"""Live input level meter. Run it, speak, watch the numbers."""
import sys, time
import numpy as np, sounddevice as sd
sys.stdout.reconfigure(encoding='utf-8')
NAME = sys.argv[1] if len(sys.argv) > 1 else 'Microphone (Razer Seiren Elite)'
idx = None
for i, d in enumerate(sd.query_devices()):
    api = sd.query_hostapis(d['hostapi'])['name']
    if d['max_input_channels'] > 0 and d['name'].strip() == NAME and api == 'Windows WASAPI':
        idx = i
        break
if idx is None:
    sys.exit('not found: ' + NAME)
sr = int(sd.query_devices(idx)['default_samplerate'])
print('%s  @ %d Hz  - speak for 15 s' % (NAME, sr))
print('anything above -40 dB is usable; -60 and below is silence')
peak_overall = 0.0
with sd.InputStream(device=idx, channels=1, samplerate=sr, dtype='float32', blocksize=4096) as s:
    t0 = time.time()
    while time.time() - t0 < 15:
        d, _ = s.read(4096)
        pk = float(np.max(np.abs(d)))
        peak_overall = max(peak_overall, pk)
        db = 20 * np.log10(pk) if pk > 0 else -120
        bar = '#' * int(max(0, (db + 60) / 2))
        print('\r%7.1f dB  %-30s' % (db, bar), end='', flush=True)
print('\nloudest sample: %.1f dB' % (20 * np.log10(peak_overall) if peak_overall > 0 else -120))
