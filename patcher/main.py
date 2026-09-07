# -*- coding: utf-8 -*-
"""시희지몽 한글패치 설치기 (GUI)."""
import datetime, io, os, queue, sys, threading, time, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class _Null:
    def write(self, *a): pass
    def flush(self): pass


# 창 모드로 묶인 exe 에서는 표준 출력이 없다. 라이브러리가 print 하다 죽지 않도록.
if sys.stdout is None: sys.stdout = _Null()
if sys.stderr is None: sys.stderr = _Null()

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


class FileLog:
    """설치 과정을 파일로 남긴다. 멈춘 지점을 확인할 수 있어야 한다."""
    def __init__(self):
        root = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
        d = os.path.join(root, 'DreamOfCorpseLady-KR')
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            d = os.path.expanduser('~')
        self.path = os.path.join(d, 'install.log')
        self.t0 = time.time()
        self.write('=' * 60)
        self.write('시작 %s' % datetime.datetime.now().isoformat(timespec='seconds'))
        self.write('실행 %s' % sys.executable)

    def write(self, msg):
        try:
            with io.open(self.path, 'a', encoding='utf-8') as f:
                f.write('[%8.2fs] %s\n' % (time.time() - self.t0, msg))
        except Exception:
            pass


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.q = queue.Queue()
        self.flog = FileLog()

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
                 font=('Malgun Gothic', 15, 'bold')).pack(anchor='w', pady=(0, 14))

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
        self.flog.write('게임 폴더 후보: %r' % self.path.get())

        self.root.after(80, self._pump)

    # ── 메인 스레드 전용 UI 갱신
    def say(self, msg, tag=None):
        self.log.configure(state='normal')
        self.log.insert('end', msg + '\n', tag or ())
        self.log.see('end')
        self.log.configure(state='disabled')

    def _pump(self):
        """작업 스레드가 큐에 넣은 것만 메인 스레드에서 처리한다."""
        try:
            while True:
                kind, a, b = self.q.get_nowait()
                if kind == 'log':
                    self.say(a, b)
                elif kind == 'progress':
                    self.bar['value'] = a
                elif kind == 'done':
                    self.busy = False
                    self.btn.configure(state='normal', text='설치')
                    if a:
                        messagebox.showinfo(APP, b)
                    else:
                        messagebox.showerror(APP, b)
        except queue.Empty:
            pass
        self.root.after(80, self._pump)

    # ── 작업 스레드에서 호출
    def emit(self, msg, tag=None):
        self.flog.write(msg)
        self.q.put(('log', msg, tag))

    def progress(self, pct):
        self.q.put(('progress', pct, None))

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
        self.emit('로그: %s' % self.flog.path)
        threading.Thread(target=self._run, args=(game,), daemon=True).start()

    def _run(self, game):
        try:
            self.flog.write('대상 %r' % game)
            ctx = steps.Ctx(game, resource_dir(), on_log=self.emit)
            cache = {}
            for pct, msg, fn in (
                ( 5, '원본 백업 확인',   lambda: steps.ensure_backup(ctx)),
                (20, '번역 적용',       lambda: steps.step_translate(ctx, cache)),
                (55, '폰트 적용',       lambda: steps.step_font(ctx, cache)),
                (65, '이미지 적용',     lambda: steps.step_image(ctx, cache)),
                (70, '표기 순서 수정',  lambda: steps.step_code(ctx)),
                (98, '게임에 저장',     lambda: steps.save_all(ctx, cache)),
            ):
                self.emit('· ' + msg)
                fn()
                self.progress(pct)
            self.progress(100)
            self.emit('설치가 끝났습니다. 게임을 실행해 주세요.', 'ok')
            self.q.put(('done', True, '설치가 끝났습니다.'))
        except finder.NotFound as e:
            self._fail('패치 대상을 찾지 못했습니다.\n%s\n\n'
                       '게임 파일은 변경되지 않았습니다.' % e)
        except Exception as e:
            self.flog.write(traceback.format_exc())
            self._fail('%s\n\n%s' % (e, traceback.format_exc(limit=3)))

    def _fail(self, msg):
        self.flog.write('실패: %s' % msg)
        self.emit(msg, 'err')
        self.emit('로그 파일: %s' % self.flog.path, 'err')
        self.q.put(('done', False, msg + '\n\n로그: ' + self.flog.path))


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
