"""The plugin-bundle contract (SPEC_shelly_instrument_memory.md §3.6, N14, S2b/S3b). Qt-free, in -core.

A bundle is ONE plugin with ALL its module files — the dev bench is six — stripped of docstrings and comments and
bz2-compressed, so it fits a plug's script slots. Signed by the MASTER key like a sealed plugin (same TRUSTED_KEYS),
but over its own tuple with its own domain string: a bundle signature can never pass for a single-row signature
and vice versa. The signature covers the STRIPPED text, because that is what is stored and run (N14)."""
import ast
import base64
import bz2
import hashlib
import json

from sciens.spectracs.logic.security import ed25519

BUNDLE_FORMAT = "spectracs-plugin-bundle/1"


def strip(source: str) -> str:
    """Drop docstrings and comments (ast round trip: semantically the same code, `__doc__` becomes None)."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) \
                    and isinstance(first.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree) + "\n"


def make(codeRef: str, version: str, targetSdkVersion, modules: dict, title: str = None) -> dict:
    """modules = {"package.module": source}; every source is stripped here."""
    return {"format": BUNDLE_FORMAT, "codeRef": codeRef, "version": version, "targetSdkVersion": targetSdkVersion,
            "title": title or codeRef, "modules": {name: strip(text) for name, text in sorted(modules.items())}}


def bundle_tuple(bundle: dict) -> bytes:
    modulesJson = json.dumps(bundle["modules"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return ("%s\n%s\n%s\n%s\n%s" % (BUNDLE_FORMAT, bundle["codeRef"], bundle["version"], bundle["targetSdkVersion"],
                                    hashlib.sha256(modulesJson.encode("utf-8")).hexdigest())).encode("utf-8")


def verify(bundle: dict, signatureBase64: str, keyId: str, trustedKeys: dict) -> bool:
    publicKeyHex = (trustedKeys or {}).get(keyId)
    if not publicKeyHex or not signatureBase64 or bundle.get("format") != BUNDLE_FORMAT:
        return False
    try:
        return ed25519.checkvalid(base64.b64decode(signatureBase64), bundle_tuple(bundle), bytes.fromhex(publicKeyHex))
    except Exception:
        return False


def pack(bundle: dict, signatureBase64: str, keyId: str) -> bytes:
    """Bytes for the plug store: bz2 of the JSON {bundle, signature, keyId}."""
    envelope = {"bundle": bundle, "signature": signatureBase64, "keyId": keyId}
    return bz2.compress(json.dumps(envelope, ensure_ascii=False).encode("utf-8"), 9)


def unpack(data: bytes) -> dict:
    return json.loads(bz2.decompress(data).decode("utf-8"))
