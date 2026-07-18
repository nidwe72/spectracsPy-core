"""Ed25519 — the public-domain REFERENCE implementation (djb et al., ed25519.cr.yp.to / RFC 8032 appendix),
vendored verbatim into -core so the plugin loader can VERIFY signatures with zero native dependency, on every
platform including Android (SPEC_plugin_distribution.md §8, B2). Only `checkvalid` is used by the app; signing is
done on the master with PyNaCl. Pure Python and slow (~ms), which is fine: verify runs once per plugin load.

Provenance: this is the canonical reference implementation, released to the public domain. It is intentionally
left unmodified so it can be audited against the well-known original."""
import hashlib

b = 256
q = 2 ** 255 - 19
l = 2 ** 252 + 27742317777372353535851937790883648493


def H(m):
    return hashlib.sha512(m).digest()


def expmod(base, e, m):
    if e == 0:
        return 1
    t = expmod(base, e // 2, m) ** 2 % m
    if e & 1:
        t = (t * base) % m
    return t


def inv(x):
    return expmod(x, q - 2, q)


d = -121665 * inv(121666) % q
I = expmod(2, (q - 1) // 4, q)


def xrecover(y):
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x


By = 4 * inv(5) % q
Bx = xrecover(By)
B = [Bx % q, By % q]


def edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2)
    return [x3 % q, y3 % q]


def scalarmult(P, e):
    if e == 0:
        return [0, 1]
    Q = scalarmult(P, e // 2)
    Q = edwards(Q, Q)
    if e & 1:
        Q = edwards(Q, P)
    return Q


def encodeint(y):
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])


def encodepoint(P):
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])


def bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def Hint(m):
    h = H(m)
    return sum(2 ** i * bit(h, i) for i in range(2 * b))


def isoncurve(P):
    x, y = P
    return (-x * x + y * y - 1 - d * x * x * y * y) % q == 0


def decodeint(s):
    return sum(2 ** i * bit(s, i) for i in range(0, b))


def decodepoint(s):
    y = sum(2 ** i * bit(s, i) for i in range(0, b - 1))
    x = xrecover(y)
    if x & 1 != bit(s, b - 1):
        x = q - x
    P = [x, y]
    if not isoncurve(P):
        raise Exception("decoding point that is not on curve")
    return P


def checkvalid(s, m, pk):
    """Return True iff `s` (64-byte signature) is a valid Ed25519 signature of message `m` under 32-byte
    public key `pk`. Verifies [S]B == R + [H(R,A,M)]A. Raises on malformed input (length / off-curve)."""
    if len(s) != b // 4:
        raise Exception("signature length is wrong")
    if len(pk) != b // 8:
        raise Exception("public-key length is wrong")
    R = decodepoint(s[0:b // 8])
    A = decodepoint(pk)
    S = decodeint(s[b // 8:b // 4])
    h = Hint(encodepoint(R) + pk + m)
    return scalarmult(B, S) == edwards(R, scalarmult(A, h))
