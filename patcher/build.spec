# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 정의:  pyinstaller patcher/build.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

HERE = os.path.abspath(SPECPATH)      # patcher/
ROOT = os.path.dirname(HERE)          # 저장소 루트

datas    = [(os.path.join(ROOT, 'data'), 'data')]
binaries = []
hidden   = ['PIL._tkinter_finder']

# UnityPy 와 그것이 실행 중에 부르는 패키지들을 통째로 넣는다.
# 하나라도 빠지면 exe 안에서만 죽거나(데이터 파일 누락) 100배 느려진다
# (UnityPyBoost 누락). 리소스만 넣어서는 안 된다.
for _pkg in ('UnityPy', 'TypeTreeGeneratorAPI', 'astc_encoder',
             'texture2ddecoder', 'archspec', 'brotli', 'lz4', 'fsspec'):
    try:
        _d, _b, _h = collect_all(_pkg)
    except Exception:
        continue
    datas += _d; binaries += _b; hidden += _h
hidden += ['UnityPy.UnityPyBoost']

a = Analysis(
    [os.path.join(HERE, 'main.py')],
    pathex=[HERE],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    # 오디오 변환은 쓰지 않는다. FMOD 네이티브 DLL을 넣지 않기 위해 제외한다.
    excludes=['matplotlib', 'numpy.f2py', 'pytest', 'fmod_toolkit', 'pyfmodex'],
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
