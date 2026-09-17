"""VoiceRP pipeline core: STT -> translate -> TTS -> virtual cable.

Importable with no side effects beyond reading config, so both the CLI
(bridge.py) and the GUI (gui.py) can own the lifecycle themselves.
"""
import os, sys, glob, site, io, json, time, queue, threading, wave


SHIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shims')


def prefer_minisbd():
    """Let a slim install skip stanza, and with it torch.

    argostranslate 1.11 imports stanza unguarded in sbd.py, and stanza imports
    torch at module level - 502 MB, plus spacy/scipy/sympy in its train, for
    sentence splitting argos can do with MiniSBD instead. Measured saving with
    all seven removed: 839 MB, with whisper still on CUDA and multi-sentence
    splitting still correct.

    The shim is appended to the END of sys.path and only when torch is really
    absent, so a full install keeps using the real stanza and nothing changes.
    find_spec is used rather than an import because importing torch to find out
    whether it exists costs several seconds.
    """
    os.environ.setdefault('ARGOS_CHUNK_TYPE', 'MINISBD')
    os.environ.setdefault('ARGOS_STANZA_AVAILABLE', '0')
    import importlib.util
    if importlib.util.find_spec('torch') is None and os.path.isdir(SHIM_DIR):
        if SHIM_DIR not in sys.path:
            sys.path.append(SHIM_DIR)


prefer_minisbd()


def add_nvidia_dlls():
    """faster-whisper needs CUDA 12 runtime DLLs that pip puts in odd places."""
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        for d in glob.glob(os.path.join(sp, 'nvidia', '*', 'bin')):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')


add_nvidia_dlls()

import numpy as np
import sounddevice as sd

HERE = os.path.dirname(os.path.abspath(__file__))
VOICES_DIR = os.path.join(HERE, 'voices')
WHISPER_DIR = os.path.join(HERE, 'whisper')
LANGS_JSON = os.path.join(HERE, 'langs.json')
PERSONAS_JSON = os.path.join(HERE, 'personas.json')

ASR_SR = 16000
SRC_OPTS = [('en', 'English'), ('pl', 'Polish'), (None, 'auto-detect')]
QUICK = ['ru', 'uk', 'es', 'fr', 'pl', 'en']

# whisper's stock outputs on noise. Clipped input makes it emit these instead
# of a transcript, so they are dropped rather than spoken.
JUNK = ('thank you for watching', 'thanks for watching', 'subtitles by',
        'subscribe', 'amara.org', 'puss, puss')


def resample(x, a, b):
    if a == b:
        return x
    n = int(round(len(x) * b / a))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def find_device(name, kind):
    """Resolve by NAME - PortAudio indices shift when USB audio is replugged."""
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


def list_devices(kind):
    """WASAPI devices only, deduplicated by name, in display order."""
    out, seen = [], set()
    for i, d in enumerate(sd.query_devices()):
        if sd.query_hostapis(d['hostapi'])['name'] != 'Windows WASAPI':
            continue
        ch = d['max_input_channels'] if kind == 'in' else d['max_output_channels']
        n = d['name'].strip()
        if ch > 0 and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def voices_on_disk():
    """Every Piper voice present, grouped by language prefix (ru, en, zh...)."""
    by_lang = {}
    for p in glob.glob(os.path.join(VOICES_DIR, '*.onnx')):
        f = os.path.basename(p)
        by_lang.setdefault(f.split('_')[0].lower(), []).append(f)
    for k in by_lang:
        by_lang[k].sort()
    return by_lang


def load_personas():
    """Archetypes and speaker-set names. Missing file is not fatal - the app
    just runs with the one built-in neutral persona."""
    try:
        d = json.load(open(PERSONAS_JSON, encoding='utf-8'))
        return d.get('archetypes', {}), d.get('speaker_sets', {})
    except Exception:
        return {'neutral': {'label': 'Neutral', 'length_scale': 1.0,
                            'noise_scale': 0.667, 'noise_w': 0.8,
                            'pitch': 0.0, 'effect': None}}, {}


def speakers_for(voice):
    """name -> id for a multi-speaker model, empty for a single-speaker one.

    Read from the voice's own .onnx.json, so a model downloaded later needs no
    code change.
    """
    cfg = os.path.join(VOICES_DIR, voice + '.json' if voice.endswith('.onnx')
                       else voice + '.onnx.json')
    try:
        d = json.load(open(cfg, encoding='utf-8'))
    except Exception:
        return {}
    if (d.get('num_speakers') or 1) <= 1:
        return {}
    return dict(d.get('speaker_id_map') or {})


def load_langs():
    """Languages usable right now.

    A language needs BOTH an Argos en->X pack AND a Piper voice file. Either
    alone is useless, so the check happens here instead of failing mid-sentence.
    Returns (langs, skipped) where langs[code] = dict(voice,label,gender,voices).
    """
    from argostranslate import package as argos_pkg
    cfg = json.load(open(LANGS_JSON, encoding='utf-8'))
    have = {(p.from_code, p.to_code) for p in argos_pkg.get_installed_packages()}
    disk = voices_on_disk()
    langs, skipped = {}, []
    for code, v in cfg.items():
        if not os.path.exists(os.path.join(VOICES_DIR, v['voice'])):
            skipped.append((code, v['label'], 'no voice file'))
            continue
        if code != 'en' and ('en', code) not in have:
            skipped.append((code, v['label'], 'no en->%s pack' % code))
            continue
        prefix = v['voice'].split('_')[0].lower()
        langs[code] = {'voice': v['voice'], 'label': v['label'],
                       'gender': v.get('gender', '?'),
                       'voices': disk.get(prefix, [v['voice']])}
    return langs, skipped


class Engine:
    """Owns the models, the input stream and the pipeline.

    Callbacks (all optional, called from worker threads):
      on_log(text)        one line for the UI log
      on_level(db)        input peak of the last capture
      on_result(dict)     said / out / heard / code / timings
      on_state(text)      engine lifecycle messages
    """

    def __init__(self, whisper_size='small', on_log=None, on_level=None,
                 on_result=None, on_state=None):
        self.whisper_size = whisper_size
        self.on_log = on_log or (lambda s: None)
        self.on_level = on_level or (lambda db: None)
        self.on_result = on_result or (lambda r: None)
        self.on_state = on_state or (lambda s: None)
        self.asr = None
        self.asr_device = None
        self._SynthesisConfig = None
        self.argos = None
        self.langs = {}
        self.skipped = []
        self.target = 'ru'
        self.src_i = 0
        self.voice_override = {}      # code -> voice filename
        self.speaker_override = {}    # voice filename -> speaker NAME
        self.personas, self.speaker_sets = load_personas()
        self.persona = 'neutral'
        self.dev_in = None
        self.dev_out = None
        self.dev_mon = None           # optional second sink, e.g. the headset
        self.cap_sr = 48000
        self.stream = None
        self._q = queue.Queue()
        self._drops = 0
        self._voice_cache = {}
        self.recording = threading.Event()
        self._stop = threading.Event()

    # ---------- setup ----------

    def load_models(self):
        self.on_state('loading models...')
        from faster_whisper import WhisperModel
        from piper import PiperVoice
        try:
            from piper import SynthesisConfig
        except ImportError:
            SynthesisConfig = None       # older piper: prosody dials unavailable
        from argostranslate import translate as argos
        self._PiperVoice = PiperVoice
        self._SynthesisConfig = SynthesisConfig
        self.argos = argos
        for dev, ct in (('cuda', 'float16'), ('cpu', 'int8')):
            try:
                m = WhisperModel(self.whisper_size, device=dev, compute_type=ct,
                                 download_root=WHISPER_DIR)
                list(m.transcribe(np.zeros(ASR_SR, dtype=np.float32),
                                  language='en', beam_size=1)[0])
                self.asr, self.asr_device = m, dev
                break
            except Exception as e:
                self.on_log('%s backend unavailable (%s)' % (dev, type(e).__name__))
        if self.asr is None:
            raise RuntimeError('no working whisper backend')
        self.langs, self.skipped = load_langs()
        if self.target not in self.langs and self.langs:
            self.target = sorted(self.langs)[0]
        self.on_state('models ready (whisper on %s, %d languages)'
                      % (self.asr_device, len(self.langs)))

    def warm(self, codes):
        for c in codes:
            if c in self.langs and c != 'en':
                try:
                    self.argos.translate('warm up', 'en', c)
                except Exception:
                    pass

    # ---------- audio ----------

    def voice_for(self, code):
        return self.voice_override.get(code) or self.langs[code]['voice']

    def open_input(self, name):
        """MUST run on the main thread. A WASAPI stream started from a worker
        thread fails with PaErrorCode -9999 'Unanticipated host error' because
        PortAudio initialises COM on whichever thread called Pa_Initialize."""
        self.close_input()
        self.dev_in = find_device(name, 'in')
        if self.dev_in is None:
            raise RuntimeError('microphone not found: %s' % name)
        self.cap_sr = int(sd.query_devices(self.dev_in)['default_samplerate'])

        def cb(indata, frames, t, status):
            if status:
                self._drops += 1
            if self.recording.is_set():
                self._q.put(indata.copy())

        self.stream = sd.InputStream(device=self.dev_in, channels=1,
                                     samplerate=self.cap_sr, dtype='float32',
                                     blocksize=0, latency=0.2, callback=cb)
        self.stream.start()
        self.on_state('capturing %s at %d Hz'
                      % (sd.query_devices(self.dev_in)['name'], self.cap_sr))

    def close_input(self):
        if self.stream is not None:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
            self.stream = None

    def set_output(self, name):
        self.dev_out = find_device(name, 'out')
        if self.dev_out is None:
            raise RuntimeError('output not found: %s' % name)

    def set_monitor(self, name):
        """Second playback sink so the speaker hears what was sent.

        Separate from dev_out on purpose: dev_out feeds the virtual cable the
        game or Discord listens to, and mixing the monitor into it would send
        the audio twice."""
        if not name:
            self.dev_mon = None
            return
        d = find_device(name, 'out')
        if d is None:
            raise RuntimeError('monitor output not found: %s' % name)
        self.dev_mon = d

    def persona_cfg(self, persona=None):
        """The archetype dict for a persona id, falling back to neutral."""
        p = persona or self.persona
        return self.personas.get(p) or self.personas.get('neutral') or {}

    def speaker_id_for(self, voice, persona=None):
        """Resolve a speaker NAME to piper's integer id.

        Order: an explicit user choice for this voice, then the archetype's
        prefer_speaker hint (that is how German gets a real whispered or drunk
        recording), then None for a single-speaker model.
        """
        smap = speakers_for(voice)
        if not smap:
            return None
        want = self.speaker_override.get(voice)
        if want is None:
            want = (self.persona_cfg(persona).get('prefer_speaker') or {}).get(voice)
        if want is None:
            return None
        if want in smap:
            return int(smap[want])
        try:
            i = int(want)
            return i if 0 <= i < len(smap) else None
        except (TypeError, ValueError):
            return None

    def synth(self, txt, voice, persona=None):
        """In-process piper, then the persona shaping chain.

        Never shell out: piper.exe writes WAV to stdout and Windows text mode
        expands 0x0A to 0x0D 0x0A, misaligning every sample after it (8621
        int16 jumps > 32768 in 4.5 s = ~1800 clicks/second).
        """
        cfg = self.persona_cfg(persona)
        try:
            v = self._voice_cache.get(voice)
            if v is None:
                v = self._PiperVoice.load(os.path.join(VOICES_DIR, voice))
                self._voice_cache[voice] = v

            syn = None
            if self._SynthesisConfig is not None:
                syn = self._SynthesisConfig(
                    speaker_id=self.speaker_id_for(voice, persona),
                    length_scale=cfg.get('length_scale'),
                    noise_scale=cfg.get('noise_scale'),
                    noise_w_scale=cfg.get('noise_w'))

            buf = io.BytesIO()
            with wave.open(buf, 'wb') as w:
                if syn is not None:
                    v.synthesize_wav(txt, w, syn_config=syn)
                else:
                    v.synthesize_wav(txt, w)
            buf.seek(0)
            with wave.open(buf, 'rb') as w:
                sr = w.getframerate()
                pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        except Exception as e:
            return None, '%s: %s' % (type(e).__name__, str(e)[:90])
        if len(pcm) == 0:
            return None, 'empty PCM'

        sig = pcm.astype(np.float32) / 32768.0
        if cfg.get('pitch') or cfg.get('effect') or cfg.get('gain', 1.0) != 1.0:
            try:
                import dsp
                sig = dsp.apply_chain(sig, sr, pitch=cfg.get('pitch') or 0.0,
                                      effect=cfg.get('effect'),
                                      gain=cfg.get('gain', 1.0))
            except Exception as e:
                self.on_log('persona shaping skipped: %s' % e)
        return sig, sr

    def play(self, sig, sr):
        """Fan out to the cable and, optionally, the headset.

        One OutputStream per device on its own thread. sd.play() cannot do this:
        it keeps a single global stream, so the second call kills the first."""
        devs = [d for d in (self.dev_out, self.dev_mon) if d is not None]
        if not devs:
            return
        if len(devs) == 1:
            self._play_on(devs[0], sig, sr)
            return
        ts = [threading.Thread(target=self._play_on, args=(d, sig, sr))
              for d in devs]
        for t in ts:
            t.start()
        for t in ts:
            t.join()

    def _play_on(self, dev, sig, sr):
        info = sd.query_devices(dev)
        native = int(info['default_samplerate'])
        maxch = int(info['max_output_channels'])
        # Sonar virtual devices only open at their exact native rate and full
        # channel count (8ch @ 96 kHz); VB-Cable takes 2ch/48k. Negotiate.
        for tgt, ch in ((native, 2), (native, maxch), (native, 1), (48000, 2)):
            if ch < 1 or ch > maxch:
                continue
            try:
                x = resample(sig, sr, tgt)
                peak = float(np.max(np.abs(x))) or 1.0
                x = (x / peak * 0.7).reshape(-1, 1)      # -3 dBFS, piper runs hot
                data = np.ascontiguousarray(np.repeat(x, ch, axis=1))
                # latency=0.2 deliberately: 'low' underruns and turns the whole
                # line into crackle.
                with sd.OutputStream(device=dev, samplerate=tgt, channels=ch,
                                     dtype='float32', latency=0.2) as st:
                    st.write(data)
                return
            except Exception:
                continue
        self.on_log('playback failed on %s' % info['name'])

    # ---------- pipeline ----------

    def process(self, audio):
        t0 = time.time()
        src_code = SRC_OPTS[self.src_i][0]
        pk = float(np.max(np.abs(audio))) or 1e-9
        pk_db = 20 * np.log10(pk)
        self.on_level(pk_db)
        # Always normalise to -6 dBFS: a hot mic hands WASAPI float samples past
        # 1.0 and whisper then hallucinates whole sentences.
        audio = np.clip(audio / pk * 0.5, -1.0, 1.0).astype(np.float32)
        # Keep whisper's DEFAULT temperature fallback. temperature=0 disables it
        # and drops any segment failing log_prob_threshold instead of retrying.
        segs, info = self.asr.transcribe(audio, language=src_code, beam_size=5,
                                         vad_filter=False,
                                         condition_on_previous_text=False)
        segs = list(segs)
        keep = [s for s in segs
                if s.text.strip()
                and not any(j in s.text.lower() for j in JUNK)
                and getattr(s, 'no_speech_prob', 0) < 0.9]
        said = ' '.join(s.text.strip() for s in keep).strip()
        heard = src_code or getattr(info, 'language', 'en')
        t1 = time.time()
        if not said:
            self.on_result({'error': 'nothing heard', 'peak_db': pk_db,
                            'segments': [(getattr(s, 'no_speech_prob', -1),
                                          s.text.strip()) for s in segs]})
            return
        code = self.target
        if heard == code:
            out = said
        else:
            try:
                out = self.argos.translate(said, heard, code)
            except Exception as e:
                self.on_result({'error': 'no path %s->%s (%s)' % (heard, code, e)})
                return
        t2 = time.time()
        sig, sr = self.synth(out, self.voice_for(code), self.persona)
        t3 = time.time()
        if sig is None:
            self.on_result({'error': 'TTS failed: %s' % sr})
            return
        self.on_result({'heard': heard, 'said': said, 'code': code, 'out': out,
                        'peak_db': pk_db, 'drops': self._drops,
                        'stt': (t1 - t0) * 1000, 'mt': (t2 - t1) * 1000,
                        'tts': (t3 - t2) * 1000, 'total': (t3 - t0) * 1000,
                        'secs': len(sig) / sr})
        self.play(sig, sr)

    def drain_loop(self):
        """Collect while the talk key is held, then hand the clip to process()."""
        while not self._stop.is_set():
            if not self.recording.wait(timeout=0.2):
                continue
            while self._q.qsize():
                self._q.get()
            self._drops = 0
            blocks = []
            while self.recording.is_set():
                try:
                    blocks.append(self._q.get(timeout=0.1))
                except queue.Empty:
                    pass
            time.sleep(0.15)                  # let the tail of the phrase arrive
            while self._q.qsize():
                blocks.append(self._q.get())
            if not blocks:
                continue
            raw = np.concatenate(blocks).flatten()
            if len(raw) > self.cap_sr * 0.3:
                try:
                    self.process(resample(raw, self.cap_sr, ASR_SR))
                except Exception as e:
                    self.on_result({'error': '%s: %s' % (type(e).__name__, e)})
            else:
                self.on_result({'error': 'too short (%.2f s)' % (len(raw) / self.cap_sr)})

    def start(self):
        self._stop.clear()
        threading.Thread(target=self.drain_loop, daemon=True).start()

    def shutdown(self):
        self._stop.set()
        self.recording.clear()
        self.close_input()

    # ---------- GUI helpers ----------

    def speak_test(self, text=None, code=None):
        """Render one line straight to the output device, skipping STT.

        Used by the GUI Test button so a voice can be auditioned without
        talking, and so the output routing can be proven on its own.
        """
        code = code or self.target
        if code not in self.langs:
            self.on_result({'error': 'language %s not available' % code})
            return
        if text is None:
            text = 'One, two, three, four, five.'
            if code != 'en':
                try:
                    text = self.argos.translate(text, 'en', code)
                except Exception:
                    pass
        t0 = time.time()
        sig, sr = self.synth(text, self.voice_for(code), self.persona)
        if sig is None:
            self.on_result({'error': 'TTS failed: %s' % sr})
            return
        self.on_result({'heard': '-', 'said': '(test)', 'code': code, 'out': text,
                        'peak_db': 0.0, 'drops': 0, 'stt': 0.0, 'mt': 0.0,
                        'tts': (time.time() - t0) * 1000,
                        'total': (time.time() - t0) * 1000,
                        'secs': len(sig) / sr})
        self.play(sig, sr)
