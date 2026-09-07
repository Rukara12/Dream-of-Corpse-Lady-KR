# -*- coding: utf-8 -*-
"""docs/status.json 생성.

번역 최종 갱신 시각 = data/ 를 마지막으로 건드린 커밋 시각
게임 최종 갱신 시각 = Steam public 브랜치의 timeupdated (SteamDB가 보여 주는 값과 동일)
"""
import datetime, json, os, subprocess, sys, urllib.request

import sys

# 윈도우 러너의 표준 출력이 cp1252 라서 한글을 못 찍고 죽는다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


APP  = '2842800'
INFO = 'https://api.steamcmd.net/v1/info/%s' % APP
NEWS = ('https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/'
        '?appid=%s&count=40&maxlength=1&format=json' % APP)
KEEP = 5
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, 'docs', 'status.json')


def iso(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc)\
        .isoformat().replace('+00:00', 'Z')


def game():
    req = urllib.request.Request(INFO, headers={'User-Agent': 'DreamOfCorpseLady-KR'})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    b = j['data'][APP]['depots']['branches']['public']
    return iso(b['timeupdated']), str(b.get('buildid') or '')


def updates():
    """patchnotes 태그가 붙은 Steam 공지 최근 KEEP개."""
    req = urllib.request.Request(NEWS, headers={'User-Agent': 'DreamOfCorpseLady-KR'})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    out = []
    for it in j.get('appnews', {}).get('newsitems', []):
        if 'patchnotes' not in (it.get('tags') or []):
            continue
        out.append({
            'title': (it.get('title') or '').strip(),
            'date':  iso(it.get('date')),
            'url':   it.get('url') or '',
        })
        if len(out) >= KEEP:
            break
    return out


def translation():
    out = subprocess.check_output(
        ['git', 'log', '-1', '--format=%cI', '--', 'data'], cwd=ROOT)
    return out.decode('utf-8').strip() or None


def main():
    data = {
        'app': APP,
        'translation_updated': translation(),
        'game_updated': None,
        'game_buildid': None,
        'updates': [],
        'checked': iso(datetime.datetime.now(datetime.timezone.utc).timestamp()),
    }
    try:
        data['game_updated'], data['game_buildid'] = game()
    except Exception as e:
        print('게임 빌드 조회 실패: %s' % e, file=sys.stderr)
    try:
        data['updates'] = updates()
    except Exception as e:
        print('업데이트 이력 조회 실패: %s' % e, file=sys.stderr)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(data, ensure_ascii=False))


if __name__ == '__main__':
    main()
