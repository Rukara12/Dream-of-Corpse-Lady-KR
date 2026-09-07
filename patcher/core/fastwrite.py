# -*- coding: utf-8 -*-
"""UnityPy 타입트리 쓰기 가속.

UnityPy 1.25.3 의 write_value 는 UInt8 배열을 쓸 때 바이트 하나마다
파이썬 함수를 호출한다. 12 MB 폰트를 넣으면 1,230만 번이라 느린 PC에서는
한 번에 30초씩 걸린다. 바이트 배열만 통째로 쓰도록 가로챈다.

교체 대상은 UnityPy 내부 함수이므로, 구조가 예상과 다르면 그대로 원본을 쓴다.
"""
BYTE_TYPES = ('UInt8', 'char')
_installed = False


def install():
    """한 번만 적용한다. 실패해도 패치 진행에는 지장이 없다."""
    global _installed
    if _installed:
        return True
    try:
        from UnityPy.helpers import TypeTreeHelper as T
        orig = T.write_value
        aligned = T.metaflag_is_aligned

        def write_value(value, node, writer, config):
            ch = node.m_Children
            if ch and ch[0].m_Type == 'Array':
                sub = ch[0].m_Children[1]
                if sub.m_Type in BYTE_TYPES:
                    if isinstance(value, (bytes, bytearray)):
                        raw = value
                    elif isinstance(value, list):
                        try:
                            raw = bytes(value)
                        except (TypeError, ValueError):
                            raw = None
                    else:
                        raw = None
                    if raw is not None:
                        writer.write_int(len(raw))
                        writer.write_bytes(raw)
                        if aligned(node.m_MetaFlag) or aligned(ch[0].m_MetaFlag):
                            writer.align_stream()
                        return
            return orig(value, node, writer, config)

        T.write_value = write_value
        _installed = True
        return True
    except Exception:
        return False
