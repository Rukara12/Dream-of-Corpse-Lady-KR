# -*- coding: utf-8 -*-
"""패치 4단계: 번역 · 폰트 · 이미지 · 코드.

원칙
  1. 항상 백업본에서 읽는다  -> 몇 번을 돌려도 결과가 같다
  2. 하나라도 못 찾으면 아무것도 쓰지 않는다  -> 반쯤 적용된 상태를 만들지 않는다
"""
import csv, hashlib, io, json, os, shutil, time

from . import fastwrite, finder, ilpatch, i2

BACKUP_DIR = '한글패치_원본백업'
DLL_REL    = os.path.join('Managed', 'Assembly-CSharp.dll')


class Ctx:
    def __init__(self, game_dir, data_dir, on_log=None, on_step=None):
        self.game = game_dir
        self.gd   = os.path.join(game_dir, 'DreamOfLadyZombie_Data')
        self.res  = data_dir                     # 동봉 리소스 폴더
        self.man  = json.load(io.open(os.path.join(data_dir, 'manifest.json'), encoding='utf-8'))
        self.backup = os.path.join(game_dir, BACKUP_DIR)
        self.out = self.gd            # 쓰기 대상 (테스트 시 변경)
        self._log, self._step = on_log, on_step

    def log(self, msg):
        if self._log: self._log(msg)

    def step(self, frac, msg):
        if self._step: self._step(frac, msg)


# ─────────────────────────────────────────────── 백업
def ensure_backup(ctx):
    os.makedirs(ctx.backup, exist_ok=True)
    files = list(ctx.man['assets']) + [DLL_REL]
    made = 0
    for rel in files:
        dst = os.path.join(ctx.backup, os.path.basename(rel))
        if os.path.exists(dst):
            continue
        shutil.copy2(os.path.join(ctx.gd, rel), dst)
        made += 1
    if made:
        ctx.log('원본 백업 %d개 생성' % made)
    for rel in files:
        dst = os.path.join(ctx.backup, os.path.basename(rel))
        live = os.path.join(ctx.gd, rel)
        try:
            a, b = os.path.getsize(dst), os.path.getsize(live)
        except OSError:
            continue
        ctx.log('  %s 백업 %s B / 현재 %s B' %
                (os.path.basename(rel), format(a, ','), format(b, ',')))
    return {n: os.path.join(ctx.backup, n) for n in
            [os.path.basename(f) for f in files]}


def src_path(ctx, name):
    """항상 백업본 경로를 돌려준다."""
    return os.path.join(ctx.backup, os.path.basename(name))


def load_asset(ctx, name):
    """애셋 파일을 UnityPy에 넘기기 전에 한 번 통째로 훑는다.

    UnityPy는 파일을 잘게 나눠 읽는데, 백신 실시간 검사가 켜져 있으면
    그 잔읽기마다 검사가 붙어 몇 분씩 멈춘 것처럼 보인다. 순차로 한 번
    읽어 두면 검사가 한 번에 끝나고 이후 읽기는 캐시에서 나온다.
    """
    import UnityPy
    p = src_path(ctx, name)
    size = os.path.getsize(p)
    ctx.log('  %s 읽는 중 (%s B)' % (name, format(size, ',')))
    t0 = time.time()
    got = 0
    with open(p, 'rb') as f:
        while True:
            chunk = f.read(8 << 20)
            if not chunk:
                break
            got += len(chunk)
    if got != size:
        raise finder.NotFound('%s 를 끝까지 읽지 못했습니다. (%s / %s B)'
                              % (name, format(got, ','), format(size, ',')))
    ctx.log('  %s 읽기 완료 (%.1f초)' % (name, time.time() - t0))
    env = UnityPy.load(p)
    ctx.log('  %s 해석 완료 (%.1f초)' % (name, time.time() - t0))
    return env


# ─────────────────────────────────────────────── 1. 번역
def load_korean(csv_path, column):
    with io.open(csv_path, encoding='utf-8-sig', newline='') as f:
        r = csv.reader(f)
        head = next(r)
        ki = head.index(column)
        out = {}
        for row in r:
            if row and len(row) > ki and row[ki].strip():
                out[row[0]] = row[ki].replace('\\r', '\r').replace('\\n', '\n')
    return out


def step_translate(ctx, env_cache):
    import UnityPy
    cfg = ctx.man['translation']
    kor = load_korean(os.path.join(ctx.res, cfg['file']), cfg['column'])
    ctx.log('번역 항목 %d개' % len(kor))

    env = load_asset(ctx, 'resources.assets')
    obj, data = finder.find_i2(env)
    src = data['mSource']
    idx = cfg['inject_into_language_index']

    applied = 0
    for t in src['mTerms']:
        if t['Term'] in kor:
            langs = t['Languages']
            while len(langs) <= idx:
                langs.append('')
            langs[idx] = kor[t['Term']]
            t['Languages'] = langs
            applied += 1

    rn = cfg['rename_language']
    for lang in src['mLanguages']:
        if lang['Code'] == rn['from_code']:
            lang['Name'], lang['Code'] = rn['name'], rn['code']
            break

    obj.set_raw_data(i2.serialize_all(data))
    env_cache['resources.assets'] = env
    ctx.log('번역 주입 %d개 항목' % applied)
    return applied


# ─────────────────────────────────────────────── 2. 폰트
def _reset_glyphs(t):
    """옛 폰트의 글리프 인덱스가 남아 있으면 새 폰트가 엉뚱한 글자로 그려진다.
    TMP는 유니코드가 아니라 글리프 인덱스로 아틀라스를 재사용하기 때문."""
    pack = 0 if (t['m_AtlasRenderMode'] & 0x10) else 1
    t['m_GlyphTable'] = []
    t['m_CharacterTable'] = []
    t['m_UsedGlyphRects'] = []
    t['m_FreeGlyphRects'] = [{'m_X': 0, 'm_Y': 0,
                              'm_Width':  t['m_AtlasWidth'] - pack,
                              'm_Height': t['m_AtlasHeight'] - pack}]
    t['m_AtlasTextureIndex'] = 0
    t['m_glyphInfoList'] = []
    if isinstance(t.get('m_KerningTable'), dict):
        t['m_KerningTable']['kerningPairs'] = []
    if isinstance(t.get('m_FontFeatureTable'), dict):
        t['m_FontFeatureTable']['m_GlyphPairAdjustmentRecords'] = []
    if isinstance(t.get('m_fontInfo'), dict):
        t['m_fontInfo']['CharacterCount'] = 0


def tmp_node(game_dir):
    from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
    g = TypeTreeGenerator('2022.3.52f1')
    g.load_local_game(game_dir)
    return g.get_nodes_up('Unity.TextMeshPro', 'TMPro.TMP_FontAsset')


def step_font(ctx, env_cache):
    """CJK TMP 폰트 애셋을 찾고, 그것들이 참조하는 Font의 TTF를 갈아끼운다.
    Font를 이름으로 찾지 않으므로 동명이인(NotoSansSC-Regular 2개) 문제가 없다."""
    import UnityPy
    fastwrite.install()
    ttf = open(os.path.join(ctx.res, ctx.man['font']['file']), 'rb').read()
    ctx.log('폰트 %s (%s B)' % (ctx.man['font']['file'], format(len(ttf), ',')))
    ctx.log('  타입트리 준비 중')
    node = tmp_node(ctx.game)
    ctx.log('  타입트리 준비 완료')

    names = ctx.man['assets']
    envs, assets, refs = {}, {}, set()
    for n in names:
        env = env_cache.get(n) or load_asset(ctx, n)
        envs[n] = env
        tmp = finder.find_tmp_font_assets(env, node)
        assets[n] = tmp
        refs |= finder.font_refs(tmp, finder.externals(env), n)
        ctx.log('  %s — CJK 폰트 애셋 %d개' % (n, len(tmp)))
    if not refs:
        raise finder.NotFound('교체할 Font 오브젝트를 찾지 못했습니다.')

    # 파일별 Font 교체
    ctx.log('  Font %d개 교체 시작' % len(refs))
    swapped = 0
    per_file = {}
    for fname, pid in refs:
        per_file.setdefault(fname, set()).add(pid)
    for n, pids in per_file.items():
        env = envs.get(n)
        if env is None:
            raise finder.NotFound('참조된 파일이 대상에 없습니다: %s' % n)
        for o in env.objects:
            if o.type.name == 'Font' and o.path_id in pids:
                t = o.read_typetree()
                t['m_FontData'] = ttf
                o.save_typetree(t)
                swapped += 1
                ctx.log('    Font %s ← 교체' % t['m_Name'])

    # TMP 애셋 초기화 + 동적 모드
    ctx.log('  TMP 애셋 초기화 중')
    fixed = 0
    for n in names:
        # 소스 폰트가 없는 애셋(JXZK2)은 같은 파일에서 교체한 Font를 물려준다.
        pids_here = per_file.get(n) or set()
        fallback = min(pids_here) if pids_here else None   # 결정적으로 고른다
        for o, t in assets[n]:
            t['m_IsMultiAtlasTexturesEnabled'] = 1
            t['m_AtlasPopulationMode'] = 1
            src = t.get('m_SourceFontFile') or {}
            if not src.get('m_PathID') and fallback:
                t['m_SourceFontFile'] = {'m_FileID': 0, 'm_PathID': fallback}
            _reset_glyphs(t)
            o.save_typetree(t, node)
            fixed += 1
    for n in names:
        env_cache[n] = envs[n]
    ctx.log('Font %d개 교체 / TMP 애셋 %d개 초기화' % (swapped, fixed))
    return swapped, fixed


# ─────────────────────────────────────────────── 3. 이미지
def step_image(ctx, env_cache):
    import UnityPy
    from PIL import Image
    cfg = ctx.man['images']
    entries = cfg['entries']
    wanted = {e['texture']: e['size'] for e in entries}
    by_tex = {e['texture']: e for e in entries}

    name = 'sharedassets1.assets'
    env = env_cache.get(name) or load_asset(ctx, name)
    hits = finder.find_textures(env, wanted)

    done = 0
    for tex, objs in hits.items():
        path = os.path.join(ctx.res, cfg['dir'], by_tex[tex]['file'])
        img = Image.open(path).convert('RGBA')
        for o in objs:
            d = o.read()
            # 원본이 DXT5면 글자 가장자리가 뭉개진다. 무손실 RGBA32로 넣는다.
            d.set_image(img, target_format=4, mipmap_count=max(1, d.m_MipCount or 1))
            d.save()
            done += 1
    env_cache[name] = env
    ctx.log('텍스처 %d장 교체' % done)
    return done


# ─────────────────────────────────────────────── 4. 코드
def step_code(ctx):
    cfg = ctx.man['code_patch']
    raw = open(src_path(ctx, 'Assembly-CSharp.dll'), 'rb').read()
    out, n, msg = ilpatch.apply(raw, cfg['expect_sites'])
    dst = os.path.join(ctx.out, DLL_REL)
    with open(dst, 'wb') as f:
        f.write(out)
    ctx.log('코드 패치: %s' % msg)
    return n


# ─────────────────────────────────────────────── 저장
def save_all(ctx, env_cache):
    """한 파일씩 쓰고 곧바로 메모리에서 놓아 준다."""
    import gc
    for n in list(env_cache):
        env = env_cache.pop(n)
        t0 = time.time()
        data = env.file.save()
        with open(os.path.join(ctx.out, n), 'wb') as f:
            f.write(data)
        ctx.log('%s 저장 (%s B, %.1f초)' % (n, format(len(data), ','), time.time() - t0))
        del data, env
        gc.collect()
