# -*- coding: utf-8 -*-
"""시희지몽 한글패치 설치기 (GUI)."""
import os, sys, threading, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core import locate, steps, finder

APP  = '시희지몽 한글패치'
BG   = '#1b2220'
CARD = '#232c2a'
FG   = '#e7edeb'
DIM  = '#8f9c99'
ACC  = '#4bb89f'
WARN = '#e0897b'


def resource_dir():
    """동봉 데이터 폴더. PyInstaller로 묶였을 때도 찾는다."""
    if getattr(sys, 'frozen', False):
        return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)), 'data')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        root.title(APP)
        root.configure(bg=BG)
        root.resizable(False, False)

        st = ttk.Style()
        try: st.theme_use('clam')
        except tk.TclError: pass
        st.configure('KR.Horizontal.TProgressbar', troughcolor='#2f3a38',
                     background=ACC, bordercolor=CARD, lightcolor=ACC, darkcolor=ACC)

        wrap = tk.Frame(root, bg=BG, padx=22, pady=18)
        wrap.pack(fill='both', expand=True)

        tk.Label(wrap, text=APP, bg=BG, fg=FG,
                 font=('Malgun Gothic', 15, 'bold')).pack(anchor='w')
        tk.Label(wrap, text='번역 · 폰트 · 이미지 · 표기 순서를 한 번에 적용합니다.',
                 bg=BG, fg=DIM, font=('Malgun Gothic', 9)).pack(anchor='w', pady=(2, 14))

        # 게임 경로
        tk.Label(wrap, text='게임 폴더', bg=BG, fg=DIM,
                 font=('Malgun Gothic', 9)).pack(anchor='w')
        row = tk.Frame(wrap, bg=BG)
        row.pack(fill='x', pady=(4, 14))
        self.path = tk.StringVar(value=locate.autodetect() or '')
        self.entry = tk.Entry(row, textvariable=self.path, bg=CARD, fg=FG,
                              insertbackground=FG, relief='flat',
                              font=('Consolas', 9))
        self.entry.pack(side='left', fill='x', expand=True, ipady=6, padx=(0, 8))
        tk.Button(row, text='찾아보기', command=self.browse, bg=CARD, fg=FG,
                  activebackground='#2f3a38', activeforeground=FG, relief='flat',
                  font=('Malgun Gothic', 9), padx=14, pady=4,
                  cursor='hand2').pack(side='left')

        # 로그
        box = tk.Frame(wrap, bg=CARD)
        box.pack(fill='both', expand=True)
        self.log = tk.Text(box, height=9, bg=CARD, fg=DIM, relief='flat', wrap='word',
                           font=('Consolas', 9), padx=10, pady=8, state='disabled')
        self.log.pack(fill='both', expand=True)
        self.log.tag_configure('ok',   foreground=ACC)
        self.log.tag_configure('err',  foreground=WARN)

        self.bar = ttk.Progressbar(wrap, style='KR.Horizontal.TProgressbar',
                                   maximum=100, length=100)
        self.bar.pack(fill='x', pady=(12, 12))

        self.btn = tk.Button(wrap, text='설치', command=self.start, bg=ACC, fg='#10201c',
                             activebackground='#5fd0b6', relief='flat',
                             font=('Malgun Gothic', 11, 'bold'), pady=9, cursor='hand2')
        self.btn.pack(fill='x')

        if self.path.get():
            self.say('게임 폴더를 찾았습니다.', 'ok')
        else:
            self.say('게임 폴더를 찾지 못했습니다. 직접 지정해 주세요.', 'err')

    # ── UI helpers
    def say(self, msg, tag=None):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n', tag or ())
        self.log.see('end')
        self.log.configure(state='disabled')
        self.root.update_idletasks()

    def progress(self, pct):
        self.bar['value'] = pct
        self.root.update_idletasks()

    def browse(self):
        d = filedialog.askdirectory(title='게임 폴더 선택')
        if d:
            self.path.set(os.path.normpath(d))

    # ── 실행
    def start(self):
        if self.busy:
            return
        game = self.path.get().strip()
        if not locate.is_game_dir(game):
            messagebox.showerror(APP, 'DreamOfLadyZombie_Data 폴더가 없습니다.\n'
                                      '게임이 설치된 폴더를 지정해 주세요.')
            return
        self.busy = True
        self.btn.configure(state='disabled', text='설치 중...')
        threading.Thread(target=self._run, args=(game,), daemon=True).start()

    def _run(self, game):
        try:
            ctx = steps.Ctx(game, resource_dir(), on_log=lambda m: self.root.after(0, self.say, m))
            cache = {}
            for pct, msg, fn in (
                ( 5, '원본 백업 확인',   lambda: steps.ensure_backup(ctx)),
                (20, '번역 적용',       lambda: steps.step_translate(ctx, cache)),
                (55, '폰트 적용',       lambda: steps.step_font(ctx, cache)),
                (65, '이미지 적용',     lambda: steps.step_image(ctx, cache)),
                (70, '표기 순서 수정',  lambda: steps.step_code(ctx)),
                (98, '게임에 저장',     lambda: steps.save_all(ctx, cache)),
            ):
                self.root.after(0, self.say, '· ' + msg)
                fn()
                self.root.after(0, self.progress, pct)
            self.root.after(0, self.progress, 100)
            self.root.after(0, self.say, '설치가 끝났습니다. 게임을 실행해 주세요.', 'ok')
            self.root.after(0, lambda: messagebox.showinfo(APP, '설치가 끝났습니다.'))
        except finder.NotFound as e:
            self._fail('패치 대상을 찾지 못했습니다.\n%s\n\n'
                       '게임 파일은 변경되지 않았습니다.' % e)
        except Exception as e:
            self._fail('%s\n\n%s' % (e, traceback.format_exc(limit=3)))
        finally:
            self.root.after(0, self._done)

    def _fail(self, msg):
        self.root.after(0, self.say, msg, 'err')
        self.root.after(0, lambda: messagebox.showerror(APP, msg))

    def _done(self):
        self.busy = False
        self.btn.configure(state='normal', text='설치')


def main():
    root = tk.Tk()
    try:
        root.tk.call('tk', 'scaling', 1.25)
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
