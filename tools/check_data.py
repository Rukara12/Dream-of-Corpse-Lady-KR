# -*- coding: utf-8 -*-
"""동봉 데이터 검사. 빌드 전에 CI가 돌린다.

translation.csv 를 사람이 직접 고치다 깨뜨리는 경우를 잡는다.
가장 흔한 사고는 엑셀이 CP949 로 저장해 UTF-8 이 깨지는 것이다.
"""
import csv, io, json, os, sys

import sys

# 윈도우 러너의 표준 출력이 cp1252 라서 한글을 못 찍고 죽는다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
HEAD = ['Term_Key', 'Language_0 (CN)', 'Language_1 (EN)',
        'Language_2 (JP)', 'Language_3 (RU)', 'Korean']
MIN_TRANSLATED = 5000

errs = []


def bad(msg):
    errs.append(msg)


def check_csv(man):
    p = os.path.join(DATA, man['translation']['file'])
    raw = open(p, 'rb').read()
    if raw[:3] != b'\xef\xbb\xbf':
        bad('translation.csv 에 UTF-8 BOM 이 없습니다. '
            '엑셀에서 저장했다면 "CSV UTF-8" 형식으로 다시 저장하십시오.')
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as e:
        bad('translation.csv 가 UTF-8 이 아닙니다 (%s). '
            '엑셀의 "CSV UTF-8 (쉼표로 분리)" 로 저장하십시오.' % e)
        return
    rows = list(csv.reader(io.StringIO(text), strict=True))
    if not rows:
        bad('translation.csv 가 비어 있습니다.')
        return
    if rows[0] != HEAD:
        bad('머리글이 다릅니다.\n  기대: %s\n  실제: %s' % (HEAD, rows[0]))
        return
    ki = HEAD.index('Korean')
    wrong = [i for i, r in enumerate(rows[1:], 2) if len(r) != len(HEAD)]
    if wrong:
        bad('열 개수가 %d 이 아닌 줄: %s%s'
            % (len(HEAD), wrong[:10], ' …' if len(wrong) > 10 else ''))
    nokey = [i for i, r in enumerate(rows[1:], 2) if r and not r[0].strip()]
    if nokey:
        bad('Term_Key 가 빈 줄: %s' % nokey[:10])
    done = sum(1 for r in rows[1:] if len(r) > ki and r[ki].strip())
    if done < MIN_TRANSLATED:
        bad('번역된 줄이 %d 개뿐입니다 (최소 %d). 파일이 잘렸는지 확인하십시오.'
            % (done, MIN_TRANSLATED))
    print('translation.csv  %d줄, 번역 %d줄' % (len(rows) - 1, done))


def check_assets(man):
    font = os.path.join(DATA, man['font']['file'])
    if not os.path.isfile(font) or os.path.getsize(font) < 1_000_000:
        bad('폰트 파일이 없거나 too small: %s' % man['font']['file'])
    else:
        print('%s  %s B' % (man['font']['file'], format(os.path.getsize(font), ',')))

    try:
        from PIL import Image
    except ImportError:
        Image = None
    d = man['images']['dir']
    n = 0
    for e in man['images']['entries']:
        p = os.path.join(DATA, d, e['file'])
        if not os.path.isfile(p):
            bad('이미지 없음: %s' % e['file'])
            continue
        if Image:
            w, h = Image.open(p).size
            if [w, h] != list(e['size']):
                bad('%s 크기가 manifest 와 다릅니다: %dx%d != %s'
                    % (e['file'], w, h, e['size']))
        n += 1
    print('이미지 %d/%d장' % (n, len(man['images']['entries'])))


def main():
    man = json.load(io.open(os.path.join(DATA, 'manifest.json'), encoding='utf-8'))
    check_csv(man)
    check_assets(man)
    if errs:
        print('\n검사 실패')
        for e in errs:
            print(' - %s' % e)
        return 1
    print('\n검사 통과')
    return 0


if __name__ == '__main__':
    sys.exit(main())
