import sys, os, subprocess, wave, io, tempfile, time
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\VoiceRP\xlate\piper\piper\piper.exe'
V = r'D:\VoiceRP\xlate\voices\ru_RU-irina-medium.onnx'
T = 'Командир, это Браво два. Запрашиваем немедленную поддержку.'
TMP = r'D:\VoiceRP\xlate\tmp'
os.makedirs(TMP, exist_ok=True)

def via_stdout():
    t0 = time.perf_counter()
    r = subprocess.run([P, '-m', V, '-f', '-', '-q'], input=T.encode('utf-8'),
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    with wave.open(io.BytesIO(r.stdout), 'rb') as w:
        w.readframes(w.getnframes())
    return (time.perf_counter() - t0) * 1000

def via_file():
    t0 = time.perf_counter()
    fd, tmp = tempfile.mkstemp(suffix='.wav', dir=TMP)
    os.close(fd)
    try:
        subprocess.run([P, '-m', V, '-f', tmp, '-q'], input=T.encode('utf-8'),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(tmp, 'rb') as w:
            w.readframes(w.getnframes())
    finally:
        os.unlink(tmp)
    return (time.perf_counter() - t0) * 1000

for f, tag in ((via_stdout, 'stdout (broken)'), (via_file, 'temp file (now)')):
    f()  # warm
    runs = [f() for _ in range(5)]
    print('%-18s min %6.1f ms   median %6.1f ms   max %6.1f ms'
          % (tag, min(runs), sorted(runs)[2], max(runs)))
