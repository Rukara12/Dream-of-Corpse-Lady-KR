# -*- coding: utf-8 -*-
"""게임 설치 경로 찾기."""
import os, re, sys

DATA_DIR = 'DreamOfLadyZombie_Data'
FOLDER   = 'the dreamland of lady zombie'


def is_game_dir(path):
    return bool(path) and os.path.isdir(os.path.join(path, DATA_DIR))


def _steam_roots():
    """Steam 라이브러리 폴더들을 모은다."""
    roots = []
    if sys.platform == 'win32':
        try:
            import winreg
            for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                              (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Valve\Steam')):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        for name in ('SteamPath', 'InstallPath'):
                            try:
                                roots.append(winreg.QueryValueEx(k, name)[0])
                            except OSError:
                                pass
                except OSError:
                    pass
        except ImportError:
            pass
        for d in 'CDEFGH':
            for p in (r'%s:\Program Files (x86)\Steam' % d, r'%s:\Steam' % d,
                      r'%s:\SteamLibrary' % d):
                if os.path.isdir(p):
                    roots.append(p)

    # libraryfolders.vdf 에 적힌 추가 라이브러리까지 확장
    found = list(roots)
    for r in roots:
        vdf = os.path.join(r, 'steamapps', 'libraryfolders.vdf')
        if not os.path.isfile(vdf):
            continue
        try:
            txt = open(vdf, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        found += [p.replace('\\\\', '\\') for p in re.findall(r'"path"\s*"([^"]+)"', txt)]
    return found


def autodetect():
    """찾으면 게임 폴더 경로, 못 찾으면 None."""
    for root in _steam_roots():
        p = os.path.join(root, 'steamapps', 'common', FOLDER)
        if is_game_dir(p):
            return p
    # 패처를 게임 폴더에 두고 실행한 경우
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    for p in (here, os.path.dirname(here)):
        if is_game_dir(p):
            return p
    return None
