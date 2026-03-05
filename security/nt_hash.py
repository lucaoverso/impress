import struct

_MASK_32 = 0xFFFFFFFF


def _left_rotate(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (32 - shift))) & _MASK_32


def _f(x: int, y: int, z: int) -> int:
    return ((x & y) | (~x & z)) & _MASK_32


def _g(x: int, y: int, z: int) -> int:
    return ((x & y) | (x & z) | (y & z)) & _MASK_32


def _h(x: int, y: int, z: int) -> int:
    return (x ^ y ^ z) & _MASK_32


def _md4_digest(data: bytes) -> bytes:
    msg = bytearray(data)
    original_length_bits = (len(msg) * 8) & 0xFFFFFFFFFFFFFFFF
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0x00)
    msg += struct.pack("<Q", original_length_bits)

    a = 0x67452301
    b = 0xEFCDAB89
    c = 0x98BADCFE
    d = 0x10325476

    for offset in range(0, len(msg), 64):
        x = list(struct.unpack("<16I", msg[offset:offset + 64]))
        aa, bb, cc, dd = a, b, c, d

        # Round 1
        a = _left_rotate((a + _f(b, c, d) + x[0]) & _MASK_32, 3)
        d = _left_rotate((d + _f(a, b, c) + x[1]) & _MASK_32, 7)
        c = _left_rotate((c + _f(d, a, b) + x[2]) & _MASK_32, 11)
        b = _left_rotate((b + _f(c, d, a) + x[3]) & _MASK_32, 19)
        a = _left_rotate((a + _f(b, c, d) + x[4]) & _MASK_32, 3)
        d = _left_rotate((d + _f(a, b, c) + x[5]) & _MASK_32, 7)
        c = _left_rotate((c + _f(d, a, b) + x[6]) & _MASK_32, 11)
        b = _left_rotate((b + _f(c, d, a) + x[7]) & _MASK_32, 19)
        a = _left_rotate((a + _f(b, c, d) + x[8]) & _MASK_32, 3)
        d = _left_rotate((d + _f(a, b, c) + x[9]) & _MASK_32, 7)
        c = _left_rotate((c + _f(d, a, b) + x[10]) & _MASK_32, 11)
        b = _left_rotate((b + _f(c, d, a) + x[11]) & _MASK_32, 19)
        a = _left_rotate((a + _f(b, c, d) + x[12]) & _MASK_32, 3)
        d = _left_rotate((d + _f(a, b, c) + x[13]) & _MASK_32, 7)
        c = _left_rotate((c + _f(d, a, b) + x[14]) & _MASK_32, 11)
        b = _left_rotate((b + _f(c, d, a) + x[15]) & _MASK_32, 19)

        # Round 2
        a = _left_rotate((a + _g(b, c, d) + x[0] + 0x5A827999) & _MASK_32, 3)
        d = _left_rotate((d + _g(a, b, c) + x[4] + 0x5A827999) & _MASK_32, 5)
        c = _left_rotate((c + _g(d, a, b) + x[8] + 0x5A827999) & _MASK_32, 9)
        b = _left_rotate((b + _g(c, d, a) + x[12] + 0x5A827999) & _MASK_32, 13)
        a = _left_rotate((a + _g(b, c, d) + x[1] + 0x5A827999) & _MASK_32, 3)
        d = _left_rotate((d + _g(a, b, c) + x[5] + 0x5A827999) & _MASK_32, 5)
        c = _left_rotate((c + _g(d, a, b) + x[9] + 0x5A827999) & _MASK_32, 9)
        b = _left_rotate((b + _g(c, d, a) + x[13] + 0x5A827999) & _MASK_32, 13)
        a = _left_rotate((a + _g(b, c, d) + x[2] + 0x5A827999) & _MASK_32, 3)
        d = _left_rotate((d + _g(a, b, c) + x[6] + 0x5A827999) & _MASK_32, 5)
        c = _left_rotate((c + _g(d, a, b) + x[10] + 0x5A827999) & _MASK_32, 9)
        b = _left_rotate((b + _g(c, d, a) + x[14] + 0x5A827999) & _MASK_32, 13)
        a = _left_rotate((a + _g(b, c, d) + x[3] + 0x5A827999) & _MASK_32, 3)
        d = _left_rotate((d + _g(a, b, c) + x[7] + 0x5A827999) & _MASK_32, 5)
        c = _left_rotate((c + _g(d, a, b) + x[11] + 0x5A827999) & _MASK_32, 9)
        b = _left_rotate((b + _g(c, d, a) + x[15] + 0x5A827999) & _MASK_32, 13)

        # Round 3
        a = _left_rotate((a + _h(b, c, d) + x[0] + 0x6ED9EBA1) & _MASK_32, 3)
        d = _left_rotate((d + _h(a, b, c) + x[8] + 0x6ED9EBA1) & _MASK_32, 9)
        c = _left_rotate((c + _h(d, a, b) + x[4] + 0x6ED9EBA1) & _MASK_32, 11)
        b = _left_rotate((b + _h(c, d, a) + x[12] + 0x6ED9EBA1) & _MASK_32, 15)
        a = _left_rotate((a + _h(b, c, d) + x[2] + 0x6ED9EBA1) & _MASK_32, 3)
        d = _left_rotate((d + _h(a, b, c) + x[10] + 0x6ED9EBA1) & _MASK_32, 9)
        c = _left_rotate((c + _h(d, a, b) + x[6] + 0x6ED9EBA1) & _MASK_32, 11)
        b = _left_rotate((b + _h(c, d, a) + x[14] + 0x6ED9EBA1) & _MASK_32, 15)
        a = _left_rotate((a + _h(b, c, d) + x[1] + 0x6ED9EBA1) & _MASK_32, 3)
        d = _left_rotate((d + _h(a, b, c) + x[9] + 0x6ED9EBA1) & _MASK_32, 9)
        c = _left_rotate((c + _h(d, a, b) + x[5] + 0x6ED9EBA1) & _MASK_32, 11)
        b = _left_rotate((b + _h(c, d, a) + x[13] + 0x6ED9EBA1) & _MASK_32, 15)
        a = _left_rotate((a + _h(b, c, d) + x[3] + 0x6ED9EBA1) & _MASK_32, 3)
        d = _left_rotate((d + _h(a, b, c) + x[11] + 0x6ED9EBA1) & _MASK_32, 9)
        c = _left_rotate((c + _h(d, a, b) + x[7] + 0x6ED9EBA1) & _MASK_32, 11)
        b = _left_rotate((b + _h(c, d, a) + x[15] + 0x6ED9EBA1) & _MASK_32, 15)

        a = (a + aa) & _MASK_32
        b = (b + bb) & _MASK_32
        c = (c + cc) & _MASK_32
        d = (d + dd) & _MASK_32

    return struct.pack("<4I", a, b, c, d)


def generate_nt_hash(password: str) -> str:
    senha = str(password or "")
    digest = _md4_digest(senha.encode("utf-16le"))
    return digest.hex()
