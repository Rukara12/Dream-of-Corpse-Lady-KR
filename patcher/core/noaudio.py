# -*- coding: utf-8 -*-
"""오디오 변환기 임포트 우회.

UnityPy의 이미지 변환기(Texture2DConverter)를 쓰려면 export 패키지가
통째로 임포트되는데, 그 안의 AudioClipConverter 가 최상단에서
fmod_toolkit 을 부른다. fmod_toolkit 은 FMOD 네이티브 DLL을 요구한다.

이 패처는 오디오를 건드리지 않으므로, 그 자리에 빈 모듈을 끼워
임포트만 통과시킨다. exe 에 FMOD DLL을 넣을 필요가 없어진다.
"""
import sys, types

NAME = 'fmod_toolkit'


def install():
    if NAME in sys.modules:
        return False
    try:
        __import__(NAME)          # 제대로 설치돼 있으면 그대로 쓴다
        return False
    except Exception:
        pass

    mod = types.ModuleType(NAME)
    mod.__doc__ = '오디오 변환은 이 패처에 포함되지 않습니다.'

    def __getattr__(name):
        raise RuntimeError('오디오 변환은 이 패처에 포함되지 않습니다: %s' % name)

    mod.__getattr__ = __getattr__
    sys.modules[NAME] = mod
    return True
