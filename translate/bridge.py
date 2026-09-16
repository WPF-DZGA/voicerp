"""
VoiceRP translate bridge - push-to-talk speech translation.

Output goes to CABLE Input, which is the Windows default microphone, so it works
in ANY app that uses the default mic: Arma Reforger, Discord, Teams, a browser.
The hotkeys are global - whatever window has focus.

  F9   hold to talk
  F1   cycle SOURCE language   (English -> Polish -> auto-detect)
  F5 Russian   F4 Ukrainian   F6 Spanish   F7 French   F8 Polish   F2 English
  F11  print current state
  F12  quit

  --selftest   run on a canned WAV, no hotkeys
"""
import os, sys, glob, site, time, queue, threading, subprocess, wave, io, tempfile, json


def _add_nvidia_dlls():
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        for d in glob.glob(os.path.join(sp, 'nvidia', '*', 'bin')):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')


_add_nvidia_dlls()
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import numpy as np
import sounddevice as sd

PIPER = r'D:\VoiceRP\xlate\piper\piper\piper.exe'
VOICES_DIR = r'D:\VoiceRP\xlate\voices'
WHISPER_DIR = r'D:\VoiceRP\xlate\whisper'
WHISPER_SIZE = 'small'
TMP_DIR = r'D:\VoiceRP\xlate\tmp'
os.makedirs(TMP_DIR, exist_ok=True)

IN_NAME = 'Microphone (Razer Seiren Elite)'
# --mic arctis / --mic seiren / --mic brio - to isolate a suspect microphone
if '--mic' in sys.argv:
    _w = sys.argv[sys.argv.index('--mic') + 1].lower()
    IN_NAME = {'arctis': 'Microphone (3- Arctis Nova 7)',
               'seiren': 'Microphone (Razer Seiren Elite)',
               'brio': 'Microphone (Logitech BRIO)'}.get(_w, _w)
OUT_NAME = 'CABLE Input (VB-Audio Virtual Cable)'
# MONITORING IS OFF ON PURPOSE. Every second audio stream we opened - the Arctis
# endpoint, Sonar Aux, Sonar Chat - crackled. To hear yourself, use Windows
# "Listen to this device" on CABLE Output instead. See README.
MON_NAME = None

QUICK = ['ru', 'uk', 'es', 'fr', 'pl', 'en']   # the six F-key slots
QUICK_KEY = {'ru': 'F5', 'uk': 'F4', 'es': 'F6', 'fr': 'F7', 'pl': 'F8', 'en': 'F2'}
SRC_OPTS = [('en', 'English'), ('pl', 'Polish'), (None, 'auto-detect')]
LANGS_JSON = r'D:\VoiceRP\xlate\langs.json'

# The language table lives in langs.json, not here. A language appears only if
# BOTH its Piper voice file is on disk AND an Argos en->X pack is installed;
# either one alone is useless, so the check is done up front instead of failing
# mid-sentence.
from argostranslate import package as _argos_pkg
_cfg = json.load(open(LANGS_JSON, encoding='utf-8'))
_have = {(p.from_code, p.to_code) for p in _argos_pkg.get_installed_packages()}
LANGS, SKIPPED = {}, []
for _code, _v in _cfg.items():
    if not os.path.exists(os.path.join(VOICES_DIR, _v['voice'])):
        SKIPPED.append((_v['label'], 'no voice file'))
        continue
    if _code != 'en' and ('en', _code) not in _have:
        SKIPPED.append((_v['label'], 'no en->%s pack' % _code))
        continue
    LANGS[_code] = (_code, _v['voice'], _v['label'], _v.get('gender', '?'))
ORDER = sorted(LANGS, key=lambda c: LANGS[c][2])
if not ORDER:
    sys.exit('no usable languages - check langs.json, voices/ and the argos packs')

target = 'ru' if 'ru' in LANGS else ORDER[0]
src_i = 0
ASR_SR = 16000
SELFTEST = '--selftest' in sys.argv


def find_device(name, kind):
    if not name:
        return None
    hits = []
    for i, d in enumerate(sd.query_devices()):
        api = sd.query_hostapis(d['hostapi'])['name']
        ch = d['max_input_channels'] if kind == 'in' else d['max_output_channels']
        if ch > 0 and d['name'].strip() == name:
            hits.append((0 if api == 'Windows WASAPI' else 1, i))
    if not hits:
        stem = name.split(' (')[0].lower()
        for i, d in enumerate(sd.query_devices()):
            ch = d['max_input_channels'] if kind == 'in' else d['max_output_channels']
            if ch > 0 and stem in d['name'].lower():
                hits.append((2, i))
    hits.sort()
    return hits[0][1] if hits else None


print('loading models...', flush=True)
from faster_whisper import WhisperModel
from piper import PiperVoice
from argostranslate import translate as argos

asr = None
for dev, ct in (('cuda', 'float16'), ('cpu', 'int8')):
    try:
        m = WhisperModel(WHISPER_SIZE, device=dev, compute_type=ct, download_root=WHISPER_DIR)
        list(m.transcribe(np.zeros(ASR_SR, dtype=np.float32), language='en', beam_size=1)[0])
        asr, ASR_DEV = m, dev
        break
    except Exception:
        print('  %s backend unavailable' % dev)
if asr is None:
    sys.exit('no working whisper backend')
for c in ('ru', 'uk', 'es', 'fr', 'pl'):
    try:
        argos.translate('warm up', 'en', c)
    except Exception:
        pass
print('models ready (whisper on %s)' % ASR_DEV, flush=True)

DEV_IN = find_device(IN_NAME, 'in')
DEV_OUT = find_device(OUT_NAME, 'out')
DEV_MON = find_device(MON_NAME, 'out')
if DEV_OUT is None:
    sys.exit('output not found: ' + OUT_NAME)
if DEV_IN is None and not SELFTEST:
    sys.exit('mic not found: ' + IN_NAME)


def state():
    return 'source=%s  ->  they hear %s [%s]' % (
        SRC_OPTS[src_i][1], LANGS[target][2], target)


def show_all():
    print('%d languages ready:' % len(ORDER), flush=True)
    cells = []
    for c in ORDER:
        cells.append('%s%-11s %s %-4s' % ('*' if c == target else ' ',
                                          LANGS[c][2], LANGS[c][3],
                                          QUICK_KEY.get(c, '')))
    for i in range(0, len(cells), 3):
        print('  ' + ''.join(cells[i:i + 3]), flush=True)
    if SKIPPED:
        print('  unavailable: ' + ', '.join('%s (%s)' % x for x in SKIPPED), flush=True)

print('mic :', ('%s  [idx %d, %s]' % (sd.query_devices(DEV_IN)['name'], DEV_IN, sd.query_hostapis(sd.query_devices(DEV_IN)['hostapi'])['name'])) if DEV_IN is not None else 'n/a')
print('out :', sd.query_devices(DEV_OUT)['name'], '(= Windows default mic, so any app picks it up)')
show_all()
print(state())

recording = threading.Event()


def resample(x, a, b):
    if a == b:
        return x
    n = int(round(len(x) * b / a))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


_VOICE_CACHE = {}


def synth(txt, voice):
    # In-process piper-tts. This replaced shelling out to piper.exe, which had
    # two problems:
    #   1. `piper.exe -f -` writes the WAV to stdout and Windows opens stdout in
    #      TEXT mode, expanding every 0x0A to 0x0D 0x0A. That misaligned every
    #      sample after it - 8621 int16 jumps > 32768 in 4.5 s, e.g.
    #      32514 -> -32513. Each one a full-scale click; that was the crackle.
    #   2. The 2023.11 binary cannot load newer voices (256-symbol phoneme maps,
    #      phoneme_type "japanese"), so Bengali, Estonian, Hebrew, Korean and
    #      Urdu silently produced 0-byte WAVs.
    # The Python API returns samples directly, so neither can happen, and the
    # model stays loaded between calls.
    #
    # Returns (signal, rate) or (None, error-string).
    try:
        v = _VOICE_CACHE.get(voice)
        if v is None:
            v = PiperVoice.load(os.path.join(VOICES_DIR, voice))
            _VOICE_CACHE[voice] = v
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            v.synthesize_wav(txt, w)
        buf.seek(0)
        with wave.open(buf, 'rb') as w:
            sr = w.getframerate()
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    except Exception as e:
        return None, '%s: %s' % (type(e).__name__, str(e)[:90])
    if len(pcm) == 0:
        return None, 'empty PCM'
    return pcm.astype(np.float32) / 32768.0, sr

def play_one(sig, sr, dev):
    info = sd.query_devices(dev)
    native = int(info['default_samplerate'])
    maxch = int(info['max_output_channels'])
    for tgt, ch in ((native, 2), (native, maxch), (native, 1), (48000, 2)):
        if ch < 1 or ch > maxch:
            continue
        try:
            x = resample(sig, sr, tgt)
            peak = float(np.max(np.abs(x))) or 1.0
            x = (x / peak * 0.7).reshape(-1, 1)   # -3 dBFS; piper runs hot and clips
            data = np.ascontiguousarray(np.repeat(x, ch, axis=1))
            # latency=0.2 is deliberate. latency='low' gives a buffer so small the
            # write underruns and the whole line comes out as crackle.
            with sd.OutputStream(device=dev, samplerate=tgt, channels=ch,
                                 dtype='float32', latency=0.2) as st:
                st.write(data)
            return
        except Exception:
            continue
    print('  play failed on %s (%s)' % (dev, info['name']), flush=True)


def play_all(sig, sr):
    ts = [threading.Thread(target=play_one, args=(sig, sr, d))
          for d in (DEV_OUT, DEV_MON) if d is not None]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def handle(audio):
    t0 = time.time()
    src_code = SRC_OPTS[src_i][0]
    pk = float(np.max(np.abs(audio))) or 1e-9
    pk = float(np.max(np.abs(audio))) or 1e-9
    pk_db = 20 * np.log10(pk)
    # Always normalise to -6 dBFS. A hot mic hands WASAPI float samples past 1.0
    # (+18 dB = 8x over full scale) and whisper then hallucinates whole sentences.
    audio = np.clip(audio / pk * 0.5, -1.0, 1.0).astype(np.float32)
    flag = '  CLIPPED AT THE MIC - gain knob down' if pk_db > 0 else ''
    print('  input peak %.1f dB%s' % (pk_db, flag), flush=True)
    try:                       # keep the last capture so a bad transcript can be replayed
        with wave.open(r'D:\VoiceRP\test\last_capture.wav','wb') as _w:
            _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(ASR_SR)
            _w.writeframes((audio * 32767).astype(np.int16).tobytes())
    except Exception:
        pass
    # Keep whisper's DEFAULT temperature fallback. temperature=0 disables it, and
    # then any segment failing log_prob_threshold is dropped instead of retried -
    # which returned an empty transcript for perfectly good -20 dB audio.
    segs, info = asr.transcribe(audio, language=src_code, beam_size=5,
                                vad_filter=False,
                                condition_on_previous_text=False)
    segs = list(segs)
    if not segs:
        print('  whisper returned no segments', flush=True)
    for s in segs:
        print('    seg [%.1fs-%.1fs] nsp=%.2f logp=%.2f :: %s'
              % (s.start, s.end, getattr(s, 'no_speech_prob', -1),
                 getattr(s, 'avg_logprob', 0), s.text.strip()), flush=True)
    JUNK = ('thank you for watching', 'thanks for watching', 'subtitles by',
            'subscribe', 'amara.org', 'puss, puss')
    keep = [s for s in segs
            if s.text.strip()
            and s.text.strip().lower().strip('.!? ') not in ('',)
            and not any(j in s.text.lower() for j in JUNK)
            and getattr(s, 'no_speech_prob', 0) < 0.9]
    said = ' '.join(s.text.strip() for s in keep).strip()
    heard = src_code or getattr(info, 'language', 'en')
    t1 = time.time()
    if not said:
        print('  (nothing heard)', flush=True)
        return
    code, voice, label, _g = LANGS[target]
    if heard == code:
        out = said
    else:
        try:
            out = argos.translate(said, heard, code)
        except Exception as e:
            print('  no translation path %s->%s (%s)' % (heard, code, e), flush=True)
            return
    t2 = time.time()
    sig, sr = synth(out, voice)
    if sig is None:
        print('  TTS failed for %s: %s' % (label, sr), flush=True)
        return
    t3 = time.time()
    print('  %s : %s' % (heard.upper(), said))
    print('  %s : %s' % (code.upper(), out))
    print('  stt %dms  mt %dms  tts %dms  TOTAL %dms  (%.1fs of audio)'
          % ((t1-t0)*1000, (t2-t1)*1000, (t3-t2)*1000, (t3-t0)*1000, len(sig)/sr), flush=True)
    play_all(sig, sr)


AUDIO_Q = queue.Queue()
DROPS = {'n': 0}
CAP_SR = int(sd.query_devices(DEV_IN)['default_samplerate']) if DEV_IN is not None else 48000


def _in_cb(indata, frames, time_info, status):
    if status:
        DROPS['n'] += 1
    if recording.is_set():
        AUDIO_Q.put(indata.copy())


def open_input_stream():
    # MUST be created and started on the MAIN thread. Starting a WASAPI stream
    # from a worker thread fails with PaErrorCode -9999 "Unanticipated host
    # error", because PortAudio's WASAPI backend initialises COM on whichever
    # thread called Pa_Initialize. The error text even names the WDM-KS
    # backend, which is misleading - the device is correct.
    st = sd.InputStream(device=DEV_IN, channels=1, samplerate=CAP_SR,
                        dtype='float32', blocksize=0, latency=0.2,
                        callback=_in_cb)
    st.start()
    print('  (capturing at %d Hz, buffered)' % CAP_SR, flush=True)
    return st


def recorder():
    # Drain loop only - the stream itself is owned by the main thread.
    #
    # The first version looped on a blocking stream.read(). At the WASAPI
    # default (minimum) buffer that loop lost input blocks whenever the GIL was
    # held by the whisper thread, so the audio handed to the ASR had gaps in it
    # and whisper answered with hallucinations instead of a transcript.
    while True:
        recording.wait()
        while AUDIO_Q.qsize():
            AUDIO_Q.get()                 # drop anything stale
        DROPS['n'] = 0
        blocks = []
        while recording.is_set():
            try:
                blocks.append(AUDIO_Q.get(timeout=0.1))
            except queue.Empty:
                pass
        time.sleep(0.15)                  # let the tail of the phrase arrive
        while AUDIO_Q.qsize():
            blocks.append(AUDIO_Q.get())
        if not blocks:
            print('  (no audio captured)', flush=True)
            continue
        raw = np.concatenate(blocks).flatten()
        if DROPS['n']:
            print('  WARNING: %d dropped input blocks' % DROPS['n'], flush=True)
        if len(raw) > CAP_SR * 0.3:
            handle(resample(raw, CAP_SR, ASR_SR))
        else:
            print('  (too short: %.2f s)' % (len(raw) / CAP_SR), flush=True)
if SELFTEST:
    with wave.open(r'D:\VoiceRP\test\src_male.wav', 'rb') as w:
        sr0 = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    a = resample(a, sr0, ASR_SR)
    # --only ru,ja,zh  to test a subset; default is every installed language
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else ORDER
    for code in only:
        if code not in LANGS:
            print('=== %s NOT INSTALLED ===' % code)
            continue
        target = code
        print('=== %s ===' % LANGS[code][2])
        handle(a)
    sys.exit(0)

from pynput import keyboard

TGT_KEYS = {keyboard.Key.f5: 'ru', keyboard.Key.f4: 'uk', keyboard.Key.f6: 'es',
            keyboard.Key.f7: 'fr', keyboard.Key.f8: 'pl', keyboard.Key.f2: 'en'}

IN_STREAM = open_input_stream()
threading.Thread(target=recorder, daemon=True).start()
print('hold F9 to talk  |  F3 next language  |  F1 source  |  F11 list  |  F12 quit',
      flush=True)


def on_press(key):
    global target, src_i
    if key == keyboard.Key.f9:
        if not recording.is_set():
            recording.set()
            print('* rec', flush=True)
    elif key in TGT_KEYS and TGT_KEYS[key] in LANGS:
        target = TGT_KEYS[key]
        print(state(), flush=True)
    elif key == keyboard.Key.f3:
        target = ORDER[(ORDER.index(target) + 1) % len(ORDER)]
        print(state(), flush=True)
    elif key == keyboard.Key.f1:
        src_i = (src_i + 1) % len(SRC_OPTS)
        print(state(), flush=True)
    elif key == keyboard.Key.f11:
        show_all()
        print(state(), flush=True)
    elif key == keyboard.Key.f12:
        print('bye')
        return False

def on_release(key):
    if key == keyboard.Key.f9 and recording.is_set():
        recording.clear()
        print('* processing', flush=True)


with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
    l.join()

