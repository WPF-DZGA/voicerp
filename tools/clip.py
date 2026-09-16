import sys, subprocess, wave, io
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
PIPER = r'D:\VoiceRP\xlate\piper\piper\piper.exe'
V = r'D:\VoiceRP\xlate\voices'

def synth(voice, txt):
    p = subprocess.run([PIPER, '-m', V + '\\' + voice, '-f', '-', '-q'],
                       input=txt.encode('utf-8'), stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL)
    with wave.open(io.BytesIO(p.stdout), 'rb') as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return pcm, sr

cases = [
    ('ru_RU-irina-medium.onnx', 'Командир, это Браво два. Запрашиваем поддержку.'),
    ('en_US-hfc_female-medium.onnx', 'Command, this is Bravo two. Requesting support.'),
    ('pl_PL-gosia-medium.onnx', 'Kontakt, dwoch ludzi na polnoc od mostu.'),
]
for voice, txt in cases:
    pcm, sr = synth(voice, txt)
    n = len(pcm)
    at_max = int((pcm >= 32767).sum())
    at_min = int((pcm <= -32768).sum())
    # wrap-around signature: adjacent samples jumping more than half full scale
    d = np.abs(np.diff(pcm.astype(np.int32)))
    wraps = int((d > 32768).sum())
    big = int((d > 16384).sum())
    print('%-32s %5.2f s  clipped hi %5d  lo %5d  |  jumps>32768: %4d   jumps>16384: %5d'
          % (voice.split('.')[0], n / sr, at_max, at_min, wraps, big))
    if wraps:
        i = int(np.argmax(d))
        print('        worst jump at %.3f s: %d -> %d' % (i / sr, pcm[i], pcm[i + 1]))
