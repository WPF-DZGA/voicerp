# -*- coding: utf-8 -*-
"""Measure what VoiceRP actually costs: VRAM, RAM, and per-stage latency.

Run on the target machine. Reports the numbers that decide the minimum spec,
rather than guessing from model file sizes.
"""
import os, sys, time, subprocess, numpy as np

sys.path.insert(0, r'D:\VoiceRP\xlate')


def vram():
    try:
        out = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used,memory.total,name',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=15).stdout.strip().splitlines()[0]
        used, total, name = [x.strip() for x in out.split(',')]
        return int(used), int(total), name
    except Exception as e:
        return None, None, 'nvidia-smi unavailable (%s)' % e


def rss():
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t)]
        p = PMC()
        p.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(p), p.cb)
        return p.WorkingSetSize / 1048576.0
    except Exception:
        return -1


base_used, total, gpu = vram()
print('GPU              : %s (%s MB total)' % (gpu, total))
print('VRAM before      : %s MB' % base_used)
print('RAM before       : %.0f MB' % rss())

import voicerp_core as core

t0 = time.time()
e = core.Engine()
e.load_models()
load_s = time.time() - t0
after_used, _, _ = vram()
print()
print('whisper backend  : %s' % e.asr_device)
print('model load       : %.1f s' % load_s)
print('VRAM after load  : %s MB  (delta %s MB)'
      % (after_used, None if after_used is None else after_used - base_used))
print('RAM after load   : %.0f MB' % rss())

# one full pipeline pass on synthetic speech-shaped audio
sig, sr = e.synth('One, two, three, four, five.', e.langs['en']['voice']
                  if 'en' in e.langs else list(e.langs.values())[0]['voice'])
audio = core.resample(sig, sr, core.ASR_SR).astype(np.float32)

for code in ('ru', 'pl', 'de'):
    if code not in e.langs:
        continue
    e.target = code
    t = time.time()
    segs, info = e.asr.transcribe(audio, language='en', beam_size=5,
                                  vad_filter=False,
                                  condition_on_previous_text=False)
    said = ' '.join(s.text.strip() for s in segs)
    t_stt = time.time() - t
    t = time.time()
    out = e.argos.translate(said, 'en', code)
    t_mt = time.time() - t
    t = time.time()
    s2, sr2 = e.synth(out, e.voice_for(code))
    t_tts = time.time() - t
    print('%s  stt %5.0f  mt %5.0f  tts %5.0f  total %5.0f ms'
          % (code, t_stt * 1000, t_mt * 1000, t_tts * 1000,
             (t_stt + t_mt + t_tts) * 1000))

peak_used, _, _ = vram()
print()
print('VRAM peak        : %s MB  (delta %s MB)'
      % (peak_used, None if peak_used is None else peak_used - base_used))
print('RAM peak         : %.0f MB' % rss())
print('loaded voices    : %d' % len(e._voice_cache))
e.shutdown()
