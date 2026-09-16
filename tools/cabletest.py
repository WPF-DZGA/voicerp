"""Send a pure tone through VB-Cable and count discontinuities at the far end.

A 440 Hz sine has a known maximum sample-to-sample slope. Anything exceeding it
is a glitch introduced by the cable or its buffering - which is what crackle is.
volumedetect and flat factor cannot see this; they only measure level.
"""
import sys, time, queue, threading
import numpy as np
import sounddevice as sd

sys.stdout.reconfigure(encoding='utf-8')

def find(name, kind):
    for i, d in enumerate(sd.query_devices()):
        if sd.query_hostapis(d['hostapi'])['name'] != 'Windows WASAPI':
            continue
        ch = d['max_input_channels'] if kind == 'in' else d['max_output_channels']
        if ch > 0 and d['name'].strip() == name:
            return i
    return None

CAB_IN = find('CABLE Input (VB-Audio Virtual Cable)', 'out')
CAB_OUT = find('CABLE Output (VB-Audio Virtual Cable)', 'in')
print('CABLE Input idx %s   CABLE Output idx %s' % (CAB_IN, CAB_OUT))

SR = 48000
AMP = 0.25
F = 440.0
DUR = 3.0

q = queue.Queue()
def cb(indata, frames, t, status):
    q.put(indata.copy())

rec = sd.InputStream(device=CAB_OUT, channels=1, samplerate=SR, dtype='float32',
                     blocksize=0, latency=0.2, callback=cb)
rec.start()
time.sleep(0.3)

t = np.arange(int(SR * DUR)) / SR
env = np.clip(np.minimum(t / 0.05, (t[-1] - t) / 0.05), 0, 1)
mono = (np.sin(2 * np.pi * F * t) * env * AMP).astype(np.float32)
data = np.ascontiguousarray(np.repeat(mono.reshape(-1, 1), 2, axis=1))

def play():
    with sd.OutputStream(device=CAB_IN, samplerate=SR, channels=2,
                         dtype='float32', latency=0.2) as st:
        st.write(data)

th = threading.Thread(target=play)
th.start()
th.join()
time.sleep(0.4)
rec.stop(); rec.close()

blocks = []
while q.qsize():
    blocks.append(q.get())
x = np.concatenate(blocks).flatten()
print('captured %.2f s' % (len(x) / SR))

# isolate the part with signal
loud = np.abs(x) > AMP * 0.3
if not loud.any():
    sys.exit('no tone arrived at CABLE Output')
a, b = np.argmax(loud), len(loud) - np.argmax(loud[::-1])
y = x[a + SR // 10: b - SR // 10]
print('analysing %.2f s of tone' % (len(y) / SR))

peak = float(np.max(np.abs(y)))
# max slope of a sine: 2*pi*f/sr * amplitude
expected = 2 * np.pi * F / SR * peak
d = np.abs(np.diff(y))
glitches = int((d > expected * 4).sum())
print('peak %.3f  expected max slope %.5f  observed max slope %.5f' % (peak, expected, float(d.max())))
print('GLITCHES (slope > 4x expected): %d in %d samples' % (glitches, len(y)))

# how pure is it? energy at 440 vs everything else
S = np.abs(np.fft.rfft(y * np.hanning(len(y))))
fr = np.fft.rfftfreq(len(y), 1 / SR)
band = (fr > F - 20) & (fr < F + 20)
sig = float((S[band] ** 2).sum())
noise = float((S[~band] ** 2).sum())
print('tone-to-junk ratio: %.1f dB   (clean cable is > 40 dB)' % (10 * np.log10(sig / max(noise, 1e-20))))
