# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 정의:  pyinstaller patcher/build.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

HERE = os.path.abspath(SPECPATH)      # patcher/
ROOT = os.path.dirname(HERE)          # 저장소 루트

datas    = [(os.path.join(ROOT, 'data'), 'data')]
binaries = []
hidden   = ['PIL._tkinter_finder']

# UnityPy의 타입트리 리소스(uncompressed.tpk)
datas += collect_data_files('UnityPy', include_py_files=False)
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
    name='Dreamland-KR-Patch',
    console=False,
    upx=False,
    icon=None,
)
