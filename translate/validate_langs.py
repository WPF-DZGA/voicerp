"""Synthesise one short line in every installed language and report failures.

Some Piper voices in the catalogue cannot speak: espeak-ng has no phoneme data
for the language, so piper writes a 0-byte WAV. This finds them all at once
instead of the bridge dying on the first one mid-session.

  validate_langs.py            report only
  validate_langs.py --prune    also move the broken ones out of langs.json
"""
import json, os, sys, subprocess, wave, tempfile
sys.stdout.reconfigure(encoding='utf-8')

PIPER = r'D:\VoiceRP\xlate\piper\piper\piper.exe'
VD = r'D:\VoiceRP\xlate\voices'
CFG = r'D:\VoiceRP\xlate\langs.json'
TMP = r'D:\VoiceRP\xlate\tmp'
os.makedirs(TMP, exist_ok=True)

from argostranslate import translate as argos
from argostranslate import package as argos_pkg

cfg = json.load(open(CFG, encoding='utf-8'))
have = {(p.from_code, p.to_code) for p in argos_pkg.get_installed_packages()}
LINE = 'Command, this is Bravo two. Requesting support.'

ok, bad = [], []
for code in sorted(cfg):
    v = cfg[code]
    voice = os.path.join(VD, v['voice'])
    if not os.path.exists(voice):
        bad.append((code, v['label'], 'voice file missing'))
        continue
    if code != 'en' and ('en', code) not in have:
        bad.append((code, v['label'], 'no en->%s pack' % code))
        continue
    try:
        txt = argos.translate(LINE, 'en', code) if code != 'en' else LINE
    except Exception as e:
        bad.append((code, v['label'], 'translate failed: %s' % e))
        continue
    if not txt.strip():
        bad.append((code, v['label'], 'translation came back empty'))
        continue
    fd, tmp = tempfile.mkstemp(suffix='.wav', dir=TMP)
    os.close(fd)
    try:
        r = subprocess.run([PIPER, '-m', voice, '-f', tmp, '-q'],
                           input=txt.encode('utf-8'), stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE)
        size = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        if size < 64:
            err = (r.stderr or b'').decode('utf-8', 'replace').strip().splitlines()
            bad.append((code, v['label'], 'no audio: %s' % (err[-1][:70] if err else '0-byte wav')))
            continue
        with wave.open(tmp, 'rb') as w:
            secs = w.getnframes() / w.getframerate()
        ok.append((code, v['label'], secs, txt[:48]))
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

print('WORKING (%d):' % len(ok))
for code, label, secs, txt in ok:
    print('  %-3s %-12s %4.1fs  %s' % (code, label, secs, txt))
print()
print('BROKEN (%d):' % len(bad))
for code, label, why in bad:
    print('  %-3s %-12s %s' % (code, label, why))

if '--prune' in sys.argv and bad:
    broken = json.load(open(r'D:\VoiceRP\xlate\langs_broken.json', encoding='utf-8')) \
        if os.path.exists(r'D:\VoiceRP\xlate\langs_broken.json') else {}
    for code, _, why in bad:
        broken[code] = dict(cfg.pop(code), reason=why)
    json.dump(cfg, open(CFG, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    json.dump(broken, open(r'D:\VoiceRP\xlate\langs_broken.json', 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    print('\npruned %d into langs_broken.json; langs.json now has %d' % (len(bad), len(cfg)))
