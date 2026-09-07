# -*- coding: utf-8 -*-
"""게임이 업데이트돼도 대상을 찾아내는 탐색기.

pathID는 게임을 다시 빌드할 때마다 바뀐다. 그래서 이 모듈은 pathID를
일절 쓰지 않고, 오브젝트의 '이름'과 '내용'으로만 대상을 특정한다.
"""
from . import i2

# 라틴 전용 TMP 폰트 애셋은 글리프가 0~250개, CJK 폰트 애셋은 3,500개 이상.
# 그 사이가 크게 비어 있어 1,000을 경계로 두면 안전하게 갈린다.
CJK_GLYPH_MIN = 1000
# I2 언어 데이터 블롭은 1.6 MB 이상. 이보다 작은 MonoBehaviour는 후보에서 제외.
I2_MIN_BYTES  = 200_000
I2_MIN_TERMS  = 3000
# CJK TMP 폰트 애셋은 실측 332 KB 이상, 라틴 전용은 29 KB 이하로 확실히 갈린다.
# 이 필터가 없으면 sharedassets1 의 MonoBehaviour 39,483개를 전부 파싱하려 든다.
TMP_MIN_BYTES = 100_000


class NotFound(Exception):
    """대상을 찾지 못했을 때. 이 예외가 나면 아무것도 쓰지 않고 중단한다."""


# ─────────────────────────────────────────────── I2 언어 데이터
def read_raw(obj):
    """MonoBehaviour의 원시 바이트를 그대로 읽는다."""
    obj.reset()
    rd = obj.reader
    rd.stream.seek(rd.Position)
    return rd.stream.read(obj.byte_size)


def find_i2(env):
    """I2 LanguageSource를 내용으로 찾는다.

    MonoScript가 다른 파일에 있어 클래스명으로는 못 찾으므로,
    '큰 MonoBehaviour를 I2 파서로 시도 파싱해서 되는 것'을 채택한다.
    """
    best = None
    for o in env.objects:
        if o.type.name != 'MonoBehaviour' or o.byte_size < I2_MIN_BYTES:
            continue
        try:
            data = i2.parse_all(read_raw(o))
            terms = data['mSource']['mTerms']
        except Exception:
            continue
        if len(terms) >= I2_MIN_TERMS and (best is None or len(terms) > best[2]):
            best = (o, data, len(terms))
    if best is None:
        raise NotFound('I2 언어 데이터를 찾지 못했습니다.')
    return best[0], best[1]


# ─────────────────────────────────────────────── TMP 폰트 애셋
def find_tmp_font_assets(env, node):
    """CJK용 TMP 폰트 애셋만 골라낸다. 라틴 전용은 건드리지 않는다."""
    out = []
    for o in env.objects:
        if o.type.name != 'MonoBehaviour' or o.byte_size < TMP_MIN_BYTES:
            continue
        try:
            t = o.read_typetree(node)
        except Exception:
            continue
        if 'm_AtlasPopulationMode' not in t or 'm_GlyphTable' not in t:
            continue
        # 이미 초기화된 애셋(재적용)은 글리프가 0이므로 이름으로 한 번 더 본다.
        big = len(t['m_GlyphTable']) >= CJK_GLYPH_MIN
        latin = any(k in t['m_Name'] for k in
                    ('Inconsolata', 'LiberationSans', 'ARIAL', 'Sriracha'))
        if latin:
            continue
        if big or t.get('m_AtlasPopulationMode') == 1:
            out.append((o, t))
    if not out:
        raise NotFound('TMP 폰트 애셋을 찾지 못했습니다.')
    return out


def externals(env):
    """m_FileID -> 파일명 매핑. 0은 자기 자신."""
    for f in env.files.values():
        ext = getattr(f, 'externals', None)
        if ext is None:
            continue
        m = {0: None}
        for i, e in enumerate(ext):
            m[i + 1] = e.path.split('/')[-1]
        return m
    return {0: None}


def font_refs(tmp_assets, ext_map, self_name):
    """CJK TMP 애셋들이 참조하는 Font 오브젝트 (파일명, pathID) 집합.

    이 집합이 곧 TTF를 갈아끼울 대상이다. 이름 목록을 쓰지 않으므로
    같은 이름의 Font가 여러 개 있어도(NotoSansSC-Regular 등) 헷갈리지 않는다.
    """
    refs = set()
    for _, t in tmp_assets:
        src = t.get('m_SourceFontFile') or {}
        pid = src.get('m_PathID')
        if not pid:
            continue
        fid = src.get('m_FileID', 0)
        refs.add((ext_map.get(fid) or self_name, pid))
    return refs


# ─────────────────────────────────────────────── 텍스처
def find_textures(env, wanted):
    """wanted: {텍스처 이름: (너비, 높이)} -> {이름: [오브젝트, ...]}

    이름이 겹치는 텍스처(win 등)는 해상도까지 맞는 후보를 모두 돌려준다.
    전부 바꿀지 하나만 바꿀지는 manifest 의 path_id / limit 으로 정한다.
    같은 화면에 두 오브젝트가 함께 그려지는 경우가 있어 전부 바꾸면 겹쳐 보인다.
    """
    hits = {k: [] for k in wanted}
    for o in env.objects:
        if o.type.name != 'Texture2D':
            continue
        d = o.read()
        want = wanted.get(d.m_Name)
        if want and (d.m_Width, d.m_Height) == tuple(want):
            hits[d.m_Name].append(o)
    missing = [k for k, v in hits.items() if not v]
    if missing:
        raise NotFound('텍스처를 찾지 못했습니다: ' + ', '.join(missing))
    return hits
