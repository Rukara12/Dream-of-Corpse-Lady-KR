# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 정의:  pyinstaller patcher/build.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

HERE = os.path.abspath(SPECPATH)      # patcher/
ROOT = os.path.dirname(HERE)          # 저장소 루트

datas    = [(os.path.join(ROOT, 'data'), 'data')]
binaries = []
hidden   = ['PIL._tkinter_finder']

# UnityPy 전체. 네이티브 가속 모듈(UnityPyBoost)이 빠지면 타입트리를
# 순수 파이썬으로 읽어 100배 이상 느려진다. 리소스만 넣어서는 안 된다.
_ud, _ub, _uh = collect_all('UnityPy')
datas += _ud; binaries += _ub; hidden += _uh
hidden += ['UnityPy.UnityPyBoost']
# TypeTreeGeneratorAPI의 네이티브 라이브러리
_d, _b, _h = collect_all('TypeTreeGeneratorAPI')
datas += _d; binaries += _b; hidden += _h

a = Analysis(
    [os.path.join(HERE, 'main.py')],
    pathex=[HERE],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=['matplotlib', 'numpy.f2py', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='DreamOfCorpseLady-KR-Patch',
    console=False,
    upx=False,
    icon=None,
)
