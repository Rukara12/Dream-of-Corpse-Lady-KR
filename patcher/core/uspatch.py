# -*- coding: utf-8 -*-
"""어셈블리 안의 문자열 리터럴을 같은 길이로 바꾼다.

.NET 어셈블리의 #US 힙에는 코드가 쓰는 문자열이 UTF-16 으로 들어 있다.
길이 접두사가 붙어 있으므로 글자 수가 같은 문자로만 교체한다. 그러면
메타데이터·오프셋·토큰이 하나도 안 바뀌어 구조를 건드리지 않는다.

용도: 카드·장비·재훈련 이름을 감싸는 【】를 《》로 바꾼다.
키워드(【역병】 등)는 다른 리터럴이라 그대로 남는다.
"""
import struct

from . import finder


def _rva_map(d):
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    if d[pe:pe + 4] != b'PE\0\0':
        raise finder.NotFound('PE 헤더를 찾지 못했습니다.')
    nsec = struct.unpack_from('<H', d, pe + 6)[0]
    opt_size = struct.unpack_from('<H', d, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from('<H', d, opt)[0]
    dd = opt + (96 if magic == 0x10b else 112)
    sec0 = opt + opt_size
    secs = []
    for i in range(nsec):
        o = sec0 + i * 40
        vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
        secs.append((va, max(vs, rs), ra))
    def to_off(rva):
        for va, size, ra in secs:
            if va <= rva < va + size:
                return ra + (rva - va)
        raise finder.NotFound('RVA 0x%x 를 파일 오프셋으로 바꾸지 못했습니다.' % rva)
    return dd, to_off


def us_range(d):
    """#US 힙의 (시작 오프셋, 크기)."""
    dd, to_off = _rva_map(d)
    cli = to_off(struct.unpack_from('<I', d, dd + 14 * 8)[0])
    md = to_off(struct.unpack_from('<I', d, cli + 8)[0])
    if d[md:md + 4] != b'BSJB':
        raise finder.NotFound('메타데이터 서명을 찾지 못했습니다.')
    vlen = struct.unpack_from('<I', d, md + 12)[0]
    q = md + 16 + vlen
    nstream = struct.unpack_from('<H', d, q + 2)[0]
    q += 4
    for _ in range(nstream):
        off, size = struct.unpack_from('<II', d, q)
        q += 8
        e = d.index(b'\0', q)
        name = d[q:e].decode('ascii', 'replace')
        q = (e + 1 + 3) & ~3
        if name == '#US':
            return md + off, size
    raise finder.NotFound('#US 힙이 없습니다.')


def _compressed(b, i):
    x = b[i]
    if not x & 0x80:
        return x, i + 1
    if x & 0xC0 == 0x80:
        return ((x & 0x3F) << 8) | b[i + 1], i + 2
    return ((x & 0x1F) << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3], i + 4


def apply(raw, pairs):
    """pairs: [(원본 문자열, 바꿀 문자열), ...]. 글자 수가 같아야 한다."""
    for a, b in pairs:
        if len(a) != len(b):
            raise finder.NotFound('길이가 다른 교체는 할 수 없습니다: %r -> %r' % (a, b))
    want = {a: b for a, b in pairs}

    d = bytearray(raw)
    start, size = us_range(bytes(d))
    us = bytes(d[start:start + size])

    done = {}
    i = 0
    while i < len(us):
        ln, j = _compressed(us, i)
        if ln == 0:
            i = j
            continue
        body = us[j:j + ln - 1]
        try:
            s = body.decode('utf-16-le')
        except UnicodeDecodeError:
            i = j + ln
            continue
        if s in want:
            new = want[s].encode('utf-16-le')
            if len(new) == len(body):
                d[start + j:start + j + len(body)] = new
                done[s] = done.get(s, 0) + 1
        i = j + ln

    return bytes(d), done
