# -*- coding: utf-8 -*-
"""GUI 없이 전체 파이프라인 실행 (개발·검증용)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import steps

def main(game, data, out=None):
    t0=time.time()
    ctx = steps.Ctx(game, data, on_log=lambda m: print('[%5.1fs] %s'%(time.time()-t0,m), flush=True))
    if out:
        os.makedirs(os.path.join(out,'Managed'), exist_ok=True); ctx.out = out
    steps.ensure_backup(ctx)
    cache = {}
    steps.step_translate(ctx, cache)
    steps.step_font(ctx, cache)
    steps.step_image(ctx, cache)
    steps.step_code(ctx)
    steps.save_all(ctx, cache)
    print('[%5.1fs] 완료'%(time.time()-t0))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else None)
