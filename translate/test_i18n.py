# -*- coding: utf-8 -*-
"""Integration test for the language switch, with the models stubbed out.

Exercises the real _build / _after_boot / _retext path so a missing string key
or a widget that was never registered shows up as a failure, without loading
whisper (40 s) or touching an audio device.
"""
import sys, time, tkinter as tk

sys.path.insert(0, r'D:\VoiceRP\xlate')
import voicerp_core as core
import i18n
import gui

LANGS = {
    'ru': {'voice': 'ru_RU-irina-medium.onnx', 'label': 'Russian', 'gender': 'f',
           'voices': ['ru_RU-irina-medium.onnx']},
    'de': {'voice': 'de_DE-thorsten-medium.onnx', 'label': 'German', 'gender': 'm',
           'voices': ['de_DE-thorsten-medium.onnx']},
    'hu': {'voice': 'hu_HU-anna-medium.onnx', 'label': 'Hungarian', 'gender': 'f',
           'voices': ['hu_HU-anna-medium.onnx']},
    'vi': {'voice': 'vi_VN-vais1000-medium.onnx', 'label': 'Vietnamese',
           'gender': 'f', 'voices': ['vi_VN-vais1000-medium.onnx']},
}


class FakeEngine(core.Engine):
    def load_models(self):
        self.langs, self.skipped, self.target = dict(LANGS), [], 'ru'
        self.on_state('stub models ready')

    def warm(self, codes):
        pass

    def open_input(self, name):
        self.on_state('stub capture %s' % name)

    def set_output(self, name):
        pass

    def set_monitor(self, name):
        pass

    def start(self):
        pass

    def shutdown(self):
        pass


gui.core.Engine = FakeEngine
gui.core.list_devices = lambda kind: ['Fake Mic', 'CABLE Input (VB-Audio Virtual Cable)']

root = tk.Tk()
root.geometry('1020x700+2000+2000')      # off to the side, no focus theft
app = gui.App(root)
app.state['uilang'] = 'en'
app.uilang = 'en'

for _ in range(80):                       # let the boot thread land
    root.update()
    time.sleep(0.05)
    if app.ready:
        break
assert app.ready, 'never booted'

fails = []


def check(what, got, want):
    if got != want:
        fails.append('%s: got %r want %r' % (what, got, want))


def label_of(key):
    for w, k in app._tx:
        if k == key:
            return w.cget('text')
    return '<not registered>'


app._retext()
check('en out_lang', label_of('out_lang'), i18n.tr('en', 'out_lang'))
check('en test btn', label_of('test'), 'Test voice')
check('en monitor', label_of('monitor'), 'also play in my headset')
check('en title', root.title(), 'VoiceRP')
check('en src list', app.src_box['values'][0], 'English')
en_rows = list(app.lst.get(0, 'end'))

app.uil.set('Polski')
app._pick_uilang()
root.update()

check('pl code', app.uilang, 'pl')
check('pl out_lang', label_of('out_lang'), i18n.tr('pl', 'out_lang'))
check('pl test btn', label_of('test'), i18n.tr('pl', 'test'))
check('pl monitor', label_of('monitor'), i18n.tr('pl', 'monitor'))
check('pl routing', label_of('routing'), i18n.tr('pl', 'routing'))
check('pl help btn', label_of('help'), 'Pomoc')
check('pl src list', app.src_box['values'][0], i18n.tr('pl', 'src_en'))
check('pl ptt lbl', app.ptt_lbl.cget('text'), i18n.tr('pl', 'idle'))
check('pl peak lbl', app.lvl_lbl.cget('text'), i18n.tr('pl', 'peak_none'))

pl_rows = list(app.lst.get(0, 'end'))
if en_rows == pl_rows:
    fails.append('language list did not change')
names = [r.split(None, 1)[1].rsplit(None, 1)[0] for r in pl_rows]
check('pl collation', names, sorted(names, key=i18n.sort_key))
print('PL list:', names)

# every widget must have been re-texted, not just the ones checked above
missing = [k for w, k in app._tx if w.cget('text') != i18n.tr('pl', k)]
if missing:
    fails.append('not re-texted: %s' % missing)

# and switching back must restore English exactly
app.uil.set('English')
app._pick_uilang()
root.update()
check('back to en', label_of('out_lang'), 'OUTPUT LANGUAGE')
check('back list', list(app.lst.get(0, 'end')), en_rows)

# the meter keeps its language after an update
app._show_level(-14.3)
check('en peak', app.lvl_lbl.cget('text'), i18n.tr('en', 'peak', -14.3, ''))
app.uil.set('Polski')
app._pick_uilang()
root.update()
check('pl peak keeps value', app.lvl_lbl.cget('text'),
      i18n.tr('pl', 'peak', -14.3, ''))

root.destroy()
print()
if fails:
    print('FAIL (%d)' % len(fails))
    for f in fails:
        print('  ' + f)
    sys.exit(1)
print('PASS - all %d registered widgets switch, list re-sorts, meter keeps state'
      % len(app._tx))
