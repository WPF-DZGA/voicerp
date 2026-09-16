"""VoiceRP GUI - front end over voicerp_core.Engine.

Layout follows Beatrice's idea (pick a voice on the left, monitor and route on
the right) but shares no code with it: Beatrice bundles a non-public inference
library, so only the arrangement is borrowed.

Run:  venv/Scripts/python.exe gui.py   (from D:/VoiceRP/xlate)
"""
import os, sys, queue, threading, traceback
import tkinter as tk
from tkinter import ttk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import voicerp_core as core

BG, PANEL, FG, DIM, ACC = '#1b1d21', '#24272c', '#e6e6e6', '#8b9098', '#4da3ff'
OK, BAD = '#5dd47f', '#ff6b6b'
CFG = os.path.join(HERE, 'gui_state.json')
HELP_MD = os.path.join(HERE, 'HELP.md')   # same file the repo ships as the doc
PTT_KEYS = ['f9', 'f8', 'f7', 'f6', 'caps_lock', 'scroll_lock']


class App:
    def __init__(self, root):
        self.root = root
        self.ui = queue.Queue()          # every worker-thread message lands here
        self.engine = core.Engine(on_log=self._log_cb, on_level=self._level_cb,
                                  on_result=self._result_cb, on_state=self._state_cb)
        self.ready = False
        self.listener = None
        self.state = self._load_state()
        self._build()
        self.root.after(60, self._pump)
        threading.Thread(target=self._boot, daemon=True).start()

    # ---------- persistence ----------

    def _load_state(self):
        import json
        try:
            return json.load(open(CFG, encoding='utf-8'))
        except Exception:
            return {}

    def _save_state(self):
        import json
        self.state.update({
            'mic': self.mic.get(), 'out': self.out.get(),
            'monitor': self.mon.get(), 'mon_dev': self.moni.get(),
            'src': self.src.get(),
            'target': self.engine.target, 'ptt': self.ptt.get(),
            'voices': self.engine.voice_override,
        })
        try:
            json.dump(self.state, open(CFG, 'w', encoding='utf-8'), indent=1)
        except Exception:
            pass

    # ---------- thread-safe callbacks ----------

    def _log_cb(self, s):
        self.ui.put(('log', s))

    def _state_cb(self, s):
        self.ui.put(('state', s))

    def _level_cb(self, db):
        self.ui.put(('level', db))

    def _result_cb(self, r):
        self.ui.put(('result', r))

    # ---------- layout ----------

    def _build(self):
        r = self.root
        r.title('VoiceRP')
        r.geometry('1020x700')
        r.configure(bg=BG)
        r.protocol('WM_DELETE_WINDOW', self.quit)

        s = ttk.Style()
        try:
            s.theme_use('clam')
        except Exception:
            pass
        s.configure('.', background=BG, foreground=FG, fieldbackground=PANEL,
                    bordercolor='#3a3f46', lightcolor=PANEL, darkcolor=PANEL)
        s.configure('TFrame', background=BG)
        s.configure('P.TFrame', background=PANEL)
        s.configure('TLabel', background=BG, foreground=FG)
        s.configure('P.TLabel', background=PANEL, foreground=FG)
        s.configure('Dim.TLabel', background=PANEL, foreground=DIM)
        s.configure('H.TLabel', background=PANEL, foreground=ACC,
                    font=('Segoe UI', 10, 'bold'))
        s.configure('TButton', background='#31353c', foreground=FG, borderwidth=0,
                    padding=6)
        s.map('TButton', background=[('active', '#3c424a')])
        s.configure('TCheckbutton', background=PANEL, foreground=FG)
        # readonly comboboxes otherwise draw grey-on-grey and are unreadable
        s.configure('TCombobox', arrowcolor=FG, padding=3)
        s.map('TCombobox',
              fieldbackground=[('readonly', '#15171a')],
              background=[('readonly', '#31353c')],
              foreground=[('readonly', FG)],
              selectbackground=[('readonly', '#15171a')],
              selectforeground=[('readonly', FG)],
              arrowcolor=[('active', ACC), ('!disabled', FG)])
        r.option_add('*TCombobox*Listbox.background', '#15171a')
        r.option_add('*TCombobox*Listbox.foreground', FG)
        r.option_add('*TCombobox*Listbox.selectBackground', ACC)
        r.option_add('*TCombobox*Listbox.selectForeground', '#101215')
        s.configure('Lvl.Horizontal.TProgressbar', background=OK,
                    troughcolor='#15171a', borderwidth=0)

        body = ttk.Frame(r, padding=10)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        # ---- left: language + voice picker ----
        left = ttk.Frame(body, style='P.TFrame', padding=10)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        left.rowconfigure(3, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text='OUTPUT LANGUAGE', style='H.TLabel').grid(
            row=0, column=0, sticky='w')
        self.filter = tk.StringVar()
        fe = tk.Entry(left, textvariable=self.filter, bg='#15171a', fg=FG,
                      insertbackground=FG, relief='flat', font=('Segoe UI', 10))
        fe.grid(row=1, column=0, sticky='ew', pady=(6, 2))
        fe.insert(0, '')
        self.filter.trace_add('write', lambda *_: self._refill())
        ttk.Label(left, text='type to filter', style='Dim.TLabel').grid(
            row=2, column=0, sticky='w')

        wrap = ttk.Frame(left, style='P.TFrame')
        wrap.grid(row=3, column=0, sticky='nsew', pady=6)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        self.lst = tk.Listbox(wrap, bg='#15171a', fg=FG, relief='flat',
                             selectbackground=ACC, selectforeground='#101215',
                             highlightthickness=0, activestyle='none',
                             font=('Consolas', 10), exportselection=False)
        self.lst.grid(row=0, column=0, sticky='nsew')
        sb = ttk.Scrollbar(wrap, orient='vertical', command=self.lst.yview)
        sb.grid(row=0, column=1, sticky='ns')
        self.lst.configure(yscrollcommand=sb.set)
        self.lst.bind('<<ListboxSelect>>', self._pick_lang)

        ttk.Label(left, text='VOICE', style='H.TLabel').grid(row=4, column=0,
                                                             sticky='w', pady=(6, 0))
        self.voice = tk.StringVar()
        self.voice_box = ttk.Combobox(left, textvariable=self.voice,
                                      state='readonly', values=[])
        self.voice_box.grid(row=5, column=0, sticky='ew', pady=4)
        self.voice_box.bind('<<ComboboxSelected>>', self._pick_voice)

        row = ttk.Frame(left, style='P.TFrame')
        row.grid(row=6, column=0, sticky='ew', pady=(4, 0))
        ttk.Button(row, text='Test voice', command=self.test).pack(side='left')
        ttk.Button(row, text='Reload', command=self.reload_langs).pack(side='left',
                                                                      padx=6)
        ttk.Button(row, text='Help', command=self.show_help).pack(side='left')

        # ---- right: routing, meter, log ----
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        rt = ttk.Frame(right, style='P.TFrame', padding=10)
        rt.grid(row=0, column=0, sticky='ew')
        rt.columnconfigure(1, weight=1)
        ttk.Label(rt, text='ROUTING', style='H.TLabel').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 6))

        self.mic = tk.StringVar()
        self.out = tk.StringVar()
        self.src = tk.StringVar(value=self.state.get('src', 'English'))
        self.ptt = tk.StringVar(value=self.state.get('ptt', 'f9'))
        self.mon = tk.BooleanVar(value=bool(self.state.get('monitor', False)))
        self.moni = tk.StringVar()

        self.mic_box = self._combo(rt, 1, 'Microphone', self.mic)
        self.out_box = self._combo(rt, 2, 'Send to', self.out)
        self._combo(rt, 3, 'I speak', self.src,
                    [n for _, n in core.SRC_OPTS], self._pick_src)
        self._combo(rt, 4, 'Talk key', self.ptt, PTT_KEYS, self._rebind_ptt)
        self.mon_box = self._combo(rt, 5, 'Headset', self.moni,
                                   cb=self._pick_mon)
        ttk.Checkbutton(rt, text='also play in my headset', variable=self.mon,
                        command=self._pick_mon).grid(row=6, column=1, sticky='w',
                                                     pady=(4, 0))
        self.mic_box.bind('<<ComboboxSelected>>', self._pick_mic)
        self.out_box.bind('<<ComboboxSelected>>', self._pick_out)

        mt = ttk.Frame(right, style='P.TFrame', padding=10)
        mt.grid(row=1, column=0, sticky='ew', pady=8)
        mt.columnconfigure(0, weight=1)
        self.ptt_lbl = ttk.Label(mt, text='idle', style='P.TLabel',
                                 font=('Segoe UI', 14, 'bold'))
        self.ptt_lbl.grid(row=0, column=0, sticky='w')
        self.lvl = ttk.Progressbar(mt, style='Lvl.Horizontal.TProgressbar',
                                   maximum=60, value=0)
        self.lvl.grid(row=1, column=0, sticky='ew', pady=(6, 2))
        self.lvl_lbl = ttk.Label(mt, text='input peak -', style='Dim.TLabel')
        self.lvl_lbl.grid(row=2, column=0, sticky='w')

        lg = ttk.Frame(right, style='P.TFrame', padding=10)
        lg.grid(row=2, column=0, sticky='nsew')
        lg.rowconfigure(1, weight=1)
        lg.columnconfigure(0, weight=1)
        ttk.Label(lg, text='LOG', style='H.TLabel').grid(row=0, column=0, sticky='w')
        self.log = tk.Text(lg, bg='#15171a', fg=FG, relief='flat', wrap='word',
                          height=12, font=('Consolas', 9), insertbackground=FG)
        self.log.grid(row=1, column=0, sticky='nsew', pady=(6, 0))
        lsb = ttk.Scrollbar(lg, orient='vertical', command=self.log.yview)
        lsb.grid(row=1, column=1, sticky='ns', pady=(6, 0))
        self.log.configure(yscrollcommand=lsb.set, state='disabled')
        self.log.tag_configure('said', foreground=DIM)
        self.log.tag_configure('out', foreground=OK)
        self.log.tag_configure('err', foreground=BAD)
        self.log.tag_configure('sys', foreground=ACC)

        self.status = tk.StringVar(value='starting...')
        ttk.Label(r, textvariable=self.status, anchor='w',
                  padding=(12, 4)).pack(fill='x', side='bottom')

    def _combo(self, parent, row, label, var, values=None, cb=None):
        ttk.Label(parent, text=label, style='Dim.TLabel').grid(
            row=row, column=0, sticky='w', padx=(0, 8), pady=3)
        c = ttk.Combobox(parent, textvariable=var, state='readonly',
                         values=values or [])
        c.grid(row=row, column=1, sticky='ew', pady=3)
        if cb:
            c.bind('<<ComboboxSelected>>', cb)
        return c

    # ---------- startup ----------

    def _boot(self):
        """Models load on a worker; nothing here touches sounddevice streams."""
        try:
            self.engine.load_models()
            self.engine.warm(core.QUICK)
        except Exception as e:
            self.ui.put(('log', 'FATAL %s: %s' % (type(e).__name__, e)))
            self.ui.put(('state', 'failed to start'))
            return
        self.ui.put(('booted', None))

    def _after_boot(self):
        self.ready = True
        tgt = self.state.get('target', 'ru')
        if tgt in self.engine.langs:
            self.engine.target = tgt
        self.engine.voice_override = {
            k: v for k, v in (self.state.get('voices') or {}).items()
            if k in self.engine.langs}
        self._refill()
        ins, outs = core.list_devices('in'), core.list_devices('out')
        self.mic_box['values'] = ins
        self.out_box['values'] = outs
        self.mic.set(self._prefer(self.state.get('mic'), ins,
                                 ['Seiren', 'Razer', 'Arctis', 'Microphone']))
        self.out.set(self._prefer(self.state.get('out'), outs,
                                  ['CABLE Input', 'VoiceMeeter', 'Speakers']))
        self.mon_box['values'] = outs
        self.moni.set(self._prefer(self.state.get('mon_dev'), outs,
                                   ['Arctis', 'Headset', 'Headphones', 'Speakers']))
        for code, lab, why in self.engine.skipped:
            self._write('skipped %s (%s): %s\n' % (code, lab, why), 'said')
        self._write('%d languages ready. Hold %s to talk.\n'
                    % (len(self.engine.langs), self.ptt.get().upper()), 'sys')
        self.engine.start()
        self._apply_out()
        self._apply_mon()
        self._apply_mic()
        self._rebind_ptt()

    def _prefer(self, saved, options, hints):
        if saved and saved in options:
            return saved
        for h in hints:
            for o in options:
                if h.lower() in o.lower():
                    return o
        return options[0] if options else ''

    # ---------- device wiring ----------

    def _apply_mic(self):
        """Called only from Tk callbacks - i.e. the main thread, which WASAPI
        requires for opening a stream (see Engine.open_input)."""
        name = self.mic.get()
        if not name:
            return
        try:
            self.engine.open_input(name)
        except Exception as e:
            self._write('mic failed: %s\n' % e, 'err')

    def _apply_out(self):
        name = self.out.get()
        if not name:
            return
        try:
            self.engine.set_output(name)
            self._write('output -> %s\n' % name, 'sys')
        except Exception as e:
            self._write('output failed: %s\n' % e, 'err')

    def _pick_mic(self, *_):
        self._apply_mic()
        self._save_state()

    def _pick_out(self, *_):
        self._apply_out()
        self._save_state()

    def _apply_mon(self):
        try:
            self.engine.set_monitor(self.moni.get() if self.mon.get() else None)
        except Exception as e:
            self._write('headset failed: %s\n' % e, 'err')

    def _pick_mon(self, *_):
        self._apply_mon()
        self._write('headset monitor %s\n'
                    % ('on -> %s' % self.moni.get() if self.mon.get() else 'off'),
                    'sys')
        self._save_state()

    def _pick_src(self, *_):
        names = [n for _, n in core.SRC_OPTS]
        if self.src.get() in names:
            self.engine.src_i = names.index(self.src.get())
        self._save_state()

    # ---------- language list ----------

    def _refill(self):
        if not self.ready:
            return
        q = self.filter.get().strip().lower()
        self.codes = []
        self.lst.delete(0, 'end')
        for code in sorted(self.engine.langs,
                           key=lambda c: self.engine.langs[c]['label']):
            v = self.engine.langs[code]
            if q and q not in v['label'].lower() and q not in code:
                continue
            self.codes.append(code)
            self.lst.insert('end', '%-3s %-22s %s' % (code, v['label'],
                                                      v.get('gender', '?')))
        if self.engine.target in self.codes:
            i = self.codes.index(self.engine.target)
            self.lst.selection_set(i)
            self.lst.see(i)
        self._refresh_voices()

    def _pick_lang(self, *_):
        sel = self.lst.curselection()
        if not sel:
            return
        self.engine.target = self.codes[sel[0]]
        self._refresh_voices()
        self.status.set('output language: %s'
                        % self.engine.langs[self.engine.target]['label'])
        self._save_state()

    def _refresh_voices(self):
        code = self.engine.target
        if code not in self.engine.langs:
            return
        vs = self.engine.langs[code]['voices']
        self.voice_box['values'] = vs
        self.voice.set(self.engine.voice_for(code))

    def _pick_voice(self, *_):
        self.engine.voice_override[self.engine.target] = self.voice.get()
        self._save_state()

    def reload_langs(self):
        try:
            self.engine.langs, self.engine.skipped = core.load_langs()
            self._refill()
            self._write('reloaded: %d languages\n' % len(self.engine.langs), 'sys')
        except Exception as e:
            self._write('reload failed: %s\n' % e, 'err')

    # ---------- push to talk ----------

    def _rebind_ptt(self, *_):
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
        try:
            from pynput import keyboard
        except Exception as e:
            self._write('no global hotkey (%s); use the Talk button\n' % e, 'err')
            return
        want = getattr(keyboard.Key, self.ptt.get(), None)
        if want is None:
            return

        def down(k):
            if k == want and not self.engine.recording.is_set():
                self.engine.recording.set()
                self.ui.put(('ptt', True))

        def up(k):
            if k == want and self.engine.recording.is_set():
                self.engine.recording.clear()
                self.ui.put(('ptt', False))

        self.listener = keyboard.Listener(on_press=down, on_release=up)
        self.listener.daemon = True
        self.listener.start()
        self._write('talk key: %s\n' % self.ptt.get().upper(), 'sys')
        self._save_state()

    def test(self):
        if not self.ready:
            return
        threading.Thread(target=self.engine.speak_test, daemon=True).start()

    # ---------- help ----------

    def show_help(self):
        """Render HELP.md in a window.

        The same file is the repo's settings guide, so the documentation cannot
        drift from what the app shows. Deliberately a tiny subset of markdown -
        headings, fences, tables, bullets, **bold** - because anything more
        would need a dependency to display a text file.
        """
        w = getattr(self, '_help_win', None)
        if w is not None and w.winfo_exists():
            w.lift()
            w.focus_force()
            return
        try:
            md = open(HELP_MD, encoding='utf-8').read()
        except Exception as e:
            md = ('# Help file missing\n\nExpected it at:\n\n```\n%s\n```\n\n'
                  '%s\n\nThe repo copy is translate/HELP.md.' % (HELP_MD, e))

        w = tk.Toplevel(self.root)
        self._help_win = w
        w.title('VoiceRP - settings and recommendations')
        w.geometry('900x780')
        w.configure(bg=BG)
        w.transient(self.root)

        frame = ttk.Frame(w, style='P.TFrame', padding=8)
        frame.pack(fill='both', expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        t = tk.Text(frame, bg='#15171a', fg=FG, relief='flat', wrap='word',
                    padx=16, pady=12, insertbackground=FG,
                    font=('Segoe UI', 10), spacing1=2, spacing3=3)
        t.grid(row=0, column=0, sticky='nsew')
        sb = ttk.Scrollbar(frame, orient='vertical', command=t.yview)
        sb.grid(row=0, column=1, sticky='ns')
        t.configure(yscrollcommand=sb.set)

        t.tag_configure('h1', foreground=ACC, font=('Segoe UI', 15, 'bold'),
                        spacing1=10, spacing3=8)
        t.tag_configure('h2', foreground=ACC, font=('Segoe UI', 11, 'bold'),
                        spacing1=14, spacing3=6)
        t.tag_configure('code', foreground='#9fe0b0', font=('Consolas', 9),
                        lmargin1=24, lmargin2=24)
        t.tag_configure('table', foreground=FG, font=('Consolas', 9),
                        lmargin1=16, lmargin2=16)
        t.tag_configure('bold', font=('Segoe UI', 10, 'bold'))
        t.tag_configure('bullet', lmargin1=18, lmargin2=34)
        t.tag_configure('rule', foreground='#3a3f46')
        t.tag_configure('mono', foreground='#9fe0b0', font=('Consolas', 9))

        def inline(line, base=''):
            """**bold** and `code` without pulling in a markdown library."""
            for i, chunk in enumerate(line.split('**')):
                for j, part in enumerate(chunk.split('`')):
                    if not part:
                        continue
                    tags = [base] if base else []
                    if i % 2:
                        tags.append('bold')
                    if j % 2:
                        tags.append('mono')
                    t.insert('end', part, tuple(tags))
            t.insert('end', '\n')

        def flush(rows):
            """Pipe tables as aligned columns; the |---| row is layout, not data."""
            if not rows:
                return
            grid = [[c.strip() for c in r.strip().strip('|').split('|')]
                    for r in rows]
            grid = [g for g in grid
                    if not all(set(c) <= set('-: ') and c for c in g)]
            if not grid:
                return
            n = max(len(g) for g in grid)
            grid = [g + [''] * (n - len(g)) for g in grid]
            wid = [max(len(g[i]) for g in grid) for i in range(n)]
            for k, g in enumerate(grid):
                txt = '  '.join(c.replace('`', '').ljust(wid[i])
                                for i, c in enumerate(g)).rstrip()
                t.insert('end', '  ' + txt + '\n',
                         ('table', 'bold') if k == 0 else 'table')
            t.insert('end', '\n')
            rows.clear()

        fence, rows = False, []
        for line in md.splitlines():
            if line.startswith('```'):
                flush(rows)
                fence = not fence
                t.insert('end', '\n')
                continue
            if fence:
                t.insert('end', line + '\n', 'code')
                continue
            if line.lstrip().startswith('|'):
                rows.append(line)
                continue
            flush(rows)
            if line.startswith('# '):
                t.insert('end', line[2:] + '\n', 'h1')
            elif line.startswith('## '):
                t.insert('end', line[3:] + '\n', 'h2')
            elif line.startswith('---'):
                t.insert('end', '\u2500' * 78 + '\n', 'rule')
            else:
                inline(line, 'bullet' if line.lstrip()[:2] in ('- ', '* ') else '')
        flush(rows)

        t.configure(state='disabled')
        t.bind('<Escape>', lambda e: w.destroy())
        t.focus_set()

    # ---------- UI pump ----------

    def _write(self, txt, tag='said'):
        self.log.configure(state='normal')
        self.log.insert('end', txt, tag)
        if float(self.log.index('end')) > 400:
            self.log.delete('1.0', '100.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _pump(self):
        try:
            while True:
                kind, val = self.ui.get_nowait()
                if kind == 'log':
                    self._write(val.rstrip() + '\n', 'said')
                elif kind == 'state':
                    self.status.set(val)
                    self._write(val.rstrip() + '\n', 'sys')
                elif kind == 'booted':
                    self._after_boot()
                elif kind == 'ptt':
                    self.ptt_lbl.configure(text='TALKING' if val else 'idle',
                                           foreground=OK if val else FG)
                elif kind == 'level':
                    self._show_level(val)
                elif kind == 'result':
                    self._show_result(val)
        except queue.Empty:
            pass
        except Exception:
            self._write(traceback.format_exc(), 'err')
        self.root.after(60, self._pump)

    def _show_level(self, db):
        # -60..0 dBFS mapped onto the bar; over 0 dB means whisper will
        # hallucinate, so it is called out rather than just shown full.
        self.lvl['value'] = max(0, min(60, 60 + db))
        warn = ''
        if db > 0:
            warn = '  CLIPPING - turn the mic gain down'
        elif db < -45:
            warn = '  very quiet'
        self.lvl_lbl.configure(text='input peak %+.1f dB%s' % (db, warn),
                               foreground=BAD if warn else DIM)

    def _show_result(self, r):
        if 'error' in r:
            self._write('-- %s\n' % r['error'], 'err')
            for nsp, txt in r.get('segments', []):
                self._write('   nsp=%.2f %r\n' % (nsp, txt), 'said')
            return
        self._write('%s: %s\n' % (r['heard'], r['said']), 'said')
        self._write('%s: %s\n' % (r['code'], r['out']), 'out')
        self.status.set('%.0f ms total (stt %.0f / mt %.0f / tts %.0f)  %.1f s audio%s'
                        % (r['total'], r['stt'], r['mt'], r['tts'], r['secs'],
                           '  %d dropped blocks' % r['drops'] if r['drops'] else ''))

    def quit(self):
        self._save_state()
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass
        self.engine.shutdown()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
