import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed, LampUnreachable, ShellyRpcError


class ShellyHttp:
    # Shelly Gen2+ RPC over HTTP GET (and POST for large payloads), stdlib only (D12). Digest auth is done here by hand: the Shelly challenges
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

    def post(self, method, **params):
        # JSON-RPC over POST /rpc (SPEC_shelly_instrument_memory.md §4.7): the only way to send the large script
        # pieces of the plug store, which do not fit a GET query string. The plug answers HTTP 200 with either
        # `result` or `error` ⇒ an error becomes ShellyRpcError (the plug refused, it is reachable).
        body = json.dumps({"id": 1, "method": method, "params": params}).encode()
        answer = self.__send("/rpc", "POST", body) or {}
        if "error" in answer:
            error = answer["error"] or {}
            raise ShellyRpcError(error.get("code"), error.get("message") or str(error))
        return answer.get("result")

    def get(self, path):
        return self.__send(path, "GET", None)

    def __send(self, path, method, body):
        url = "http://%s%s" % (self.host, path)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        try:
            return self.__read(urllib.request.Request(url, data=body, headers=headers, method=method))
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise LampUnreachable("%s: HTTP %s" % (url, error.code)) from error
            challenge = error.headers.get("WWW-Authenticate", "")
        if not self.password:
            raise LampAuthFailed("%s needs a password" % self.host)
        headers["Authorization"] = self.__digest(challenge, method, path)
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
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

    def __digest(self, challenge, method, path):
        fields = dict(re.findall(r'(\w+)="?([^",]*)"?', challenge))
        realm = fields.get("realm", "")
        nonce = fields.get("nonce", "")
        algorithm = fields.get("algorithm", "SHA-256").upper()
        digest = ShellyHttp.__hashFor(algorithm)
        cnonce = os.urandom(8).hex()
        nc = "00000001"
        ha1 = digest("%s:%s:%s" % (self.USER, realm, self.password))
        ha2 = digest("%s:%s" % (method, path))
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
