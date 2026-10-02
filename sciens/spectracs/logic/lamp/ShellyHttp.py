import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed, LampUnreachable


class ShellyHttp:
    # Shelly Gen2+ RPC over HTTP GET, stdlib only (D12). Digest auth is done here by hand: the Shelly challenges
    # with `algorithm=SHA-256`, which Python 3.10's urllib HTTPDigestAuthHandler cannot answer (it only knows
    # MD5/SHA — SPEC_lamp_switch.md §14 R1). User is always `admin` on a Shelly.

    USER = "admin"

    def __init__(self, host, password=None, timeout=2.0):
        self.host = host
        self.password = password
        self.timeout = timeout

    def rpc(self, method, **params):
        query = urllib.parse.urlencode({key: self.__encode(value) for key, value in params.items()})
        path = "/rpc/%s" % method + ("?" + query if query else "")
        return self.get(path)

    def get(self, path):
        url = "http://%s%s" % (self.host, path)
        try:
            return self.__read(urllib.request.Request(url))
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise LampUnreachable("%s: HTTP %s" % (url, error.code)) from error
            challenge = error.headers.get("WWW-Authenticate", "")
        if not self.password:
            raise LampAuthFailed("%s needs a password" % self.host)
        request = urllib.request.Request(url, headers={"Authorization": self.__digest(challenge, path)})
        try:
            return self.__read(request)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise LampAuthFailed("wrong password for %s" % self.host) from error
            raise LampUnreachable("%s: HTTP %s" % (url, error.code)) from error

    def __read(self, request):
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode()
        except urllib.error.HTTPError:
            raise
        except (OSError, ValueError) as error:          # URLError, timeout, connection refused
            raise LampUnreachable("%s: %s" % (request.full_url, error)) from error
        try:
            return json.loads(body) if body else None
        except ValueError as error:
            raise LampUnreachable("%s: not JSON" % request.full_url) from error

    def __digest(self, challenge, path):
        fields = dict(re.findall(r'(\w+)="?([^",]*)"?', challenge))
        realm = fields.get("realm", "")
        nonce = fields.get("nonce", "")
        algorithm = fields.get("algorithm", "SHA-256").upper()
        digest = ShellyHttp.__hashFor(algorithm)
        cnonce = os.urandom(8).hex()
        nc = "00000001"
        ha1 = digest("%s:%s:%s" % (self.USER, realm, self.password))
        ha2 = digest("GET:%s" % path)
        response = digest("%s:%s:%s:%s:auth:%s" % (ha1, nonce, nc, cnonce, ha2))
        return ('Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s, response="%s", '
                'qop=auth, nc=%s, cnonce="%s"' % (self.USER, realm, nonce, path, algorithm, response, nc, cnonce))

    @staticmethod
    def __hashFor(algorithm):
        name = {"SHA-256": "sha256", "MD5": "md5"}.get(algorithm, "sha256")
        return lambda text: hashlib.new(name, text.encode()).hexdigest()

    @staticmethod
    def __encode(value):
        if isinstance(value, (dict, list)):         # a config object: JSON in the query (e.g. PLUGS_UI.SetConfig)
            return json.dumps(value, separators=(",", ":"))
        return str(value).lower() if isinstance(value, bool) else value
