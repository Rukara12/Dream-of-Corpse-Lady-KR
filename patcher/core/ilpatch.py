# -*- coding: utf-8 -*-
"""Assembly-CSharp.dll IL 패치.

게임은 카드 툴팁의 '###' 자리에 [수치][스탯명] 순서로 문자열을 붙인다.
한국어에서는 [스탯명][수치] 순서가 자연스러우므로 두 IL 블록의 순서를 뒤집는다.
두 블록의 길이 합이 그대로라 메서드 크기도, 예외 구간도 변하지 않는다.

오프셋을 박아두면 게임이 다시 빌드될 때 무의미해지므로,
메타데이터 토큰 자리를 와일드카드로 둔 '코드 모양'으로 찾는다.
"""
import re

# A: ldloc.s N ; ldflda <field> ; call <Single::ToString>      (12 바이트)
# B: ldsfld <f> ; ldloc.s N ; ldfld <f2> ; callvirt <m>        (17 바이트)
# ?는 버전마다 달라지는 메타데이터 토큰.
SHAPE = re.compile(
    rb'\x11(.)\x7c(....)\x28(....)'
    rb'\x7e(....)\x11(.)\x7b(....)\x6f(....)',
    re.S)
A_LEN, B_LEN = 12, 17
BLOCK = A_LEN + B_LEN          # 29


def _swapped(block):
    """A+B -> B+A"""
    return block[A_LEN:] + block[:A_LEN]


def scan(raw):
    """패치 지점을 찾는다. [(오프셋, 이미패치됨), ...]"""
    sites = []
    for m in SHAPE.finditer(raw):
        off = m.start()
        # A와 B가 같은 지역변수를 쓰는 블록만 대상 (ldloc.s 인덱스 일치)
        if m.group(1) != m.group(5):
            continue
        sites.append((off, False))
    # 이미 뒤집힌 파일도 인식해야 재실행이 안전하다.
    rev = re.compile(
        rb'\x7e(....)\x11(.)\x7b(....)\x6f(....)'
        rb'\x11(.)\x7c(....)\x28(....)', re.S)
    done = [m.start() for m in rev.finditer(raw) if m.group(2) == m.group(5)]
    return sites, done


def apply(raw, expect=4):
    """raw(bytes) -> (새 bytes, 적용 수, 메시지)"""
    raw = bytearray(raw)
    sites, done = scan(bytes(raw))

    if not sites and len(done) >= expect:
        return bytes(raw), 0, '이미 적용되어 있습니다'
    if len(sites) != expect:
        raise RuntimeError(
            '코드 패치 지점을 %d곳 찾았습니다(기대 %d곳). '
            '게임이 크게 바뀐 것 같습니다 — 코드 패치는 건너뜁니다.'
            % (len(sites), expect))

    # 뒤에서부터 바꿔야 앞쪽 오프셋이 밀리지 않는다(길이는 같지만 안전하게).
    for off, _ in sorted(sites, reverse=True):
        raw[off:off + BLOCK] = _swapped(bytes(raw[off:off + BLOCK]))
    return bytes(raw), len(sites), '%d곳 적용' % len(sites)
