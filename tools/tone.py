"""Play a clean 3 s test tone to one device, to find which playback path crackles.

  tone.py                 -> list candidate outputs
  tone.py sonar           -> Sonar Gaming
  tone.py arctis          -> Arctis headphones directly
  tone.py "part of name"  -> anything else
"""
import sys
import numpy as np
import sounddevice as sd

ALIAS = {
    'sonar': 'SteelSeries Sonar - Gaming (SteelSeries Sonar Virtual Audio Device)',
    'chat': 'SteelSeries Sonar - Chat (SteelSeries Sonar Virtual Audio Device)',
    'arctis': 'Headphones (3- Arctis Nova 7)',
    'cable': 'CABLE Input (VB-Audio Virtual Cable)',
}

outs = [(i, d) for i, d in enumerate(sd.query_devices())
        if d['max_output_channels'] > 0
        and sd.query_hostapis(d['hostapi'])['name'] == 'Windows WASAPI']

if len(sys.argv) < 2:
    print('candidates:')
    for i, d in outs:
        print('  %-70s %d ch  %d Hz' % (d['name'], d['max_output_channels'],
                                        d['default_samplerate']))
    print('\nusage: tone.py sonar | arctis | chat | "substring"')
    sys.exit(0)

want = ALIAS.get(sys.argv[1].lower(), sys.argv[1])
hit = next(((i, d) for i, d in outs if d['name'].strip() == want), None)
if hit is None:
    hit = next(((i, d) for i, d in outs if want.lower() in d['name'].lower()), None)
if hit is None:
    sys.exit('no output matching: ' + want)

idx, d = hit
sr = int(d['default_samplerate'])
ch = int(d['max_output_channels'])
print('playing 3 s of 440 Hz at -18 dBFS')
print('  device : %s' % d['name'])
print('  format : %d ch @ %d Hz' % (ch, sr))
t = np.arange(int(sr * 3.0)) / sr
# fade in/out so the tone itself cannot click
env = np.clip(np.minimum(t / 0.05, (t[-1] - t) / 0.05), 0, 1)
mono = (np.sin(2 * np.pi * 440 * t) * env * 0.125).astype(np.float32)
data = np.ascontiguousarray(np.repeat(mono.reshape(-1, 1), ch, axis=1))
with sd.OutputStream(device=idx, samplerate=sr, channels=ch,
                     dtype='float32', latency=0.2) as st:
    st.write(data)
print('done - a pure tone should be perfectly smooth. Any fizz is that path.')
