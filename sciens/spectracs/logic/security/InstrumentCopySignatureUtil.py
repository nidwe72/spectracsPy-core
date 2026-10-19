"""The instrument-copy signature contract (SPEC_shelly_instrument_memory.md §9.4). Qt-free, in -core, so every
client verifies with the vendored pure-Python Ed25519 — exactly like plugin signatures (PluginSignatureUtil), but
with its OWN domain string and its OWN trusted keys: the server's copy key can never pass for a plugin key.

The signature covers (serial, server schema revision, sha256 of the SQLite bytes) ⇒ a copy moved onto another plug,
or relabelled with another revision, fails."""
import base64
import hashlib

from sciens.spectracs.logic.security import ed25519

COPY_DOMAIN = "spectracs-instrument-copy/1"


def copy_tuple(serial: str, revision: str, sqliteSha256: str) -> bytes:
    return ("%s\n%s\n%s\n%s" % (COPY_DOMAIN, serial, revision or "", sqliteSha256)).encode("utf-8")


def sha256hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(publicKey: bytes) -> str:
    return hashlib.sha256(publicKey).hexdigest()[:16]


def verify(trustedKeys: dict, keyId: str, signatureBase64: str, serial: str, revision: str,
           sqliteSha256: str) -> bool:
    publicKeyHex = (trustedKeys or {}).get(keyId)
    if not publicKeyHex or not signatureBase64:
        return False
    try:
        return ed25519.checkvalid(base64.b64decode(signatureBase64), copy_tuple(serial, revision, sqliteSha256),
                                  bytes.fromhex(publicKeyHex))
    except Exception:
        return False
