import ipaddress
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor

from sciens.spectracs.logic.lamp.LampDiscoveryResult import LampDiscoveryResult
from sciens.spectracs.logic.lamp.LampDriverRegistry import LampDriverRegistry

LOG = logging.getLogger(__name__)


class LampDiscovery:
    # Finds the lamp plug on the LAN, driver-agnostic (SPEC_lamp_switch.md §5, D8):
    #   1. the stored plug — probe its last host, same MAC => done (no multicast needed)
    #   2. mDNS / DNS-SD browse over every driver's service types, each answer confirmed by the driver's probe
    #   3. fallback: probe every address of the local /24 in parallel (networks that drop multicast)
    # Blocking (a few seconds at worst) — LampService runs it on its worker thread. The mDNS browser and the
    # subnet host list are injectable, so tests run against a FakeShellyServer on localhost.

    MDNS_SECONDS = 3.0
    SUBNET_PROBE_TIMEOUT = 0.4
    SUBNET_WORKERS = 64

    def __init__(self, drivers=None, mdnsBrowse=None, subnetHosts=None, probeTimeout=1.0):
        self.drivers = tuple(drivers) if drivers is not None else LampDriverRegistry.drivers()
        self.mdnsBrowse = mdnsBrowse if mdnsBrowse is not None else LampDiscovery.browseMdns
        self.subnetHosts = subnetHosts if subnetHosts is not None else LampDiscovery.localSubnetHosts
        self.probeTimeout = probeTimeout

    def discover(self, stored=None, useMdns=True, useSubnet=True, wantedId=None):
        """Find plugs. `chosen` is the plug with device id `wantedId` (the active instrument's serial, §11.3), else the
        stored plug (same MAC) — and NEVER simply the first one found: with several Shellys in a room that switched a
        stranger's plug (SPEC_shelly_instrument_memory.md §11, R25). The full list is in `devices`."""
        storedMac = stored.mac if stored is not None else None
        if stored is not None:
            device = self.__probe(stored.host, self.drivers)
            if device is not None and device.mac == storedMac and (wantedId is None or device.deviceId == wantedId):
                return LampDiscoveryResult([device], device, "stored")

        found, via = self.__scan(useMdns, useSubnet)
        if not found:
            return LampDiscoveryResult()
        if wantedId is not None:
            chosen = next((device for device in found if device.deviceId == wantedId), None)
        else:
            chosen = next((device for device in found if device.mac == storedMac), None)
        return LampDiscoveryResult(found, chosen, via)

    def discoverAll(self, useMdns=True, useSubnet=True):
        """Every plug on the LAN, nothing chosen — for the setup and plug pages' picker (§11.3)."""
        found, via = self.__scan(useMdns, useSubnet)
        return LampDiscoveryResult(found, None, via if found else None)

    def __scan(self, useMdns, useSubnet):
        found, via = [], None
        if useMdns:
            serviceTypes = sorted({serviceType for driver in self.drivers for serviceType in driver.mdnsServiceTypes})
            hosts = self.__safe(lambda: self.mdnsBrowse(serviceTypes, self.MDNS_SECONDS), "mDNS browse")
            found = self.__probeAll(hosts, self.probeTimeout)
            via = "mdns"
        if not found and useSubnet:
            hosts = self.__safe(self.subnetHosts, "subnet listing")
            found = self.__probeAll(hosts, self.SUBNET_PROBE_TIMEOUT)
            via = "subnet"
        return found, via

    def __probeAll(self, hosts, timeout):
        hosts = list(dict.fromkeys(hosts or ()))
        if not hosts:
            return []
        with ThreadPoolExecutor(max_workers=min(self.SUBNET_WORKERS, len(hosts))) as pool:
            results = pool.map(lambda host: self.__probe(host, self.drivers, timeout), hosts)
        unique = []
        for device in results:
            if device is not None and device not in unique:
                unique.append(device)
        return unique

    def __probe(self, host, drivers, timeout=None):
        for driver in drivers:
            device = driver.probe(host, timeout or self.probeTimeout)
            if device is not None:
                return device
        return None

    @staticmethod
    def __safe(call, what):
        try:
            return call() or []
        except Exception as error:                      # discovery must never take the app down
            LOG.warning("lamp discovery: %s failed: %s", what, error)
            return []

    @staticmethod
    def browseMdns(serviceTypes, seconds):
        """IPv4 hosts announcing any of `serviceTypes`. Needs `zeroconf`; without it, an empty list (the subnet
        scan still runs)."""
        try:
            from zeroconf import IPVersion, ServiceBrowser, Zeroconf
        except ImportError:
            LOG.info("lamp discovery: zeroconf not installed, skipping mDNS")
            return []
        names = []

        class Listener:
            def add_service(self, zc, serviceType, name):
                names.append((serviceType, name))

            def update_service(self, zc, serviceType, name):
                pass

            def remove_service(self, zc, serviceType, name):
                pass

        zc = Zeroconf(ip_version=IPVersion.V4Only)
        try:
            ServiceBrowser(zc, list(serviceTypes), Listener())
            time.sleep(seconds)
            hosts = []
            for serviceType, name in list(names):
                info = zc.get_service_info(serviceType, name, timeout=1000)
                if info is not None:
                    hosts.extend(info.parsed_addresses(IPVersion.V4Only))
            return hosts
        finally:
            zc.close()

    # Interfaces that are never the lab LAN: loopback, containers, VMs, VPN tunnels (§14.2).
    VIRTUAL_PREFIXES = ("lo", "docker", "br-", "veth", "virbr", "vmnet", "vboxnet", "tun", "tap", "wg", "zt")

    @staticmethod
    def localSubnetHosts():
        """Every address of the /24 around each real LAN interface's IPv4 (eno1 and wlp6s0 on the same
        192.168.1.x collapse to one network). Not the default route: on a PC with a VPN that is the tunnel."""
        networks = {}
        for name, address in LampDiscovery.lanAddresses():
            network = ipaddress.ip_network(address + "/24", strict=False)
            networks.setdefault(network, set()).add(address)
        hosts = []
        for network, own in networks.items():
            hosts.extend(str(host) for host in network.hosts() if str(host) not in own)
        return hosts

    @staticmethod
    def lanAddresses():
        """[(interface, ipv4)] of the private, non-virtual interfaces. Uses `ifaddr` (ships with zeroconf);
        without it, the interface of the default route."""
        try:
            import ifaddr
        except ImportError:
            return [("default", LampDiscovery.localIpv4())]
        pairs = []
        for adapter in ifaddr.get_adapters():
            if adapter.nice_name.startswith(LampDiscovery.VIRTUAL_PREFIXES):
                continue
            for ip in adapter.ips:
                if isinstance(ip.ip, str) and ipaddress.ip_address(ip.ip).is_private:
                    pairs.append((adapter.nice_name, ip.ip))
        return pairs

    @staticmethod
    def localIpv4():
        """The address of the interface carrying the default route (a UDP connect sends nothing)."""
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 9))                # TEST-NET-1, never routed anywhere
            return probe.getsockname()[0]
        finally:
            probe.close()
