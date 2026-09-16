import json, os, sys, urllib.request, time
sys.stdout.reconfigure(encoding='utf-8')
CFG = r'D:\VoiceRP\xlate\langs.json'
VD = r'D:\VoiceRP\xlate\voices'
BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/'
os.makedirs(VD, exist_ok=True)
cfg = json.load(open(CFG, encoding='utf-8'))
todo = []
for code, v in sorted(cfg.items()):
    for ext in ('.onnx', '.onnx.json'):
        dst = os.path.join(VD, v['voice'].replace('.onnx', '') + ext)
        if not os.path.exists(dst) or os.path.getsize(dst) == 0:
            todo.append((code, BASE + v['path'] + ext, dst))
print('%d files to fetch' % len(todo), flush=True)
ok = fail = 0
for code, url, dst in todo:
    for attempt in (1, 2, 3):
        try:
            urllib.request.urlretrieve(url, dst)
            ok += 1
            print('  %-3s %-45s %6.1f MB' % (code, os.path.basename(dst),
                                             os.path.getsize(dst) / 1e6), flush=True)
            break
        except Exception as e:
            if attempt == 3:
                fail += 1
                print('  %-3s FAILED %s (%s)' % (code, os.path.basename(dst), e), flush=True)
            else:
                time.sleep(2)
print('done: %d ok, %d failed' % (ok, fail), flush=True)
