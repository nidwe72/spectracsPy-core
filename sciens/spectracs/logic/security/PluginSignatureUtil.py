"""The plugin-signature contract (SPEC_plugin_distribution.md §3 / §8, B2). Qt-free, in -core, so it runs on
every client including Android. The master SIGNS this same tuple with PyNaCl (app-tier PluginSigner); everyone
VERIFIES here with the vendored pure-Python Ed25519.

The signature covers the TUPLE, not just the source — so a tampered source, a swapped version, a re-pointed
codeRef, or a lied-about targetSdkVersion all break it:

    codeRef \n version \n targetSdkVersion \n sha256hex(source)
"""
import base64
import hashlib

from sciens.spectracs.logic.security import ed25519


class PluginSignatureError(Exception):
    """A DB plugin's sealed row failed signature verification (bad signature, untrusted keyId, or a tampered
    tuple). The loader refuses to exec it."""


def signing_tuple(codeRef: str, version: str, targetSdkVersion, source: str) -> bytes:
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return ("%s\n%s\n%s\n%s" % (codeRef, version, targetSdkVersion, digest)).encode("utf-8")


def fingerprint(publicKey: bytes) -> str:
    """keyId = the first 16 hex chars of sha256(pubkey). Derived, so it can never be mislabelled."""
    return hashlib.sha256(publicKey).hexdigest()[:16]


def verify(publicKey: bytes, signature: bytes, codeRef: str, version: str, targetSdkVersion, source: str) -> bool:
    try:
        return ed25519.checkvalid(signature, signing_tuple(codeRef, version, targetSdkVersion, source), publicKey)
    except Exception:
        return False


def verifySealed(codeRef: str, version: str, targetSdkVersion, source: str,
                 signatureBase64: str, keyId: str, trustedKeys: dict) -> bool:
    """Verify a sealed DbPlugin row. `trustedKeys` = {keyId: pubkey-hex} shipped IN the app (the trust anchor).
    An unknown keyId is refused BEFORE any crypto — the shipped list is what gates. Returns True only if the
    keyId is trusted AND the signature verifies over the tuple."""
    publicKeyHex = trustedKeys.get(keyId)
    if not publicKeyHex:
        return False
    try:
        publicKey = bytes.fromhex(publicKeyHex)
        signature = base64.b64decode(signatureBase64)
    except Exception:
        return False
    return verify(publicKey, signature, codeRef, version, targetSdkVersion, source)
