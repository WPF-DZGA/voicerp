# -*- coding: utf-8 -*-
"""Download Piper voices listed in langs.json.

Portable: every path is derived from this file's location, so it works from an
installer as well as from a dev checkout.

  python getvoices.py                 every language in langs.json
  python getvoices.py --only ru,uk,pl  just those
  python getvoices.py --list           print what would be fetched, with sizes
"""
import json, os, sys, time, urllib.request

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, 'langs.json')
VD = os.path.join(HERE, 'voices')
BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/'


def parse_only(argv):
    for i, a in enumerate(argv):
        if a == '--only' and i + 1 < len(argv):
            return {c.strip().lower() for c in argv[i + 1].split(',') if c.strip()}
        if a.startswith('--only='):
            return {c.strip().lower() for c in a.split('=', 1)[1].split(',') if c.strip()}
    return None


def main():
    only = parse_only(sys.argv)
    listing = '--list' in sys.argv
    cfg = json.load(open(CFG, encoding='utf-8'))
    os.makedirs(VD, exist_ok=True)

    todo, skipped = [], 0
    for code, v in sorted(cfg.items()):
        if only is not None and code not in only:
            continue
        for ext in ('.onnx', '.onnx.json'):
            dst = os.path.join(VD, v['voice'].replace('.onnx', '') + ext)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                skipped += 1
                continue
            todo.append((code, BASE + v['path'] + ext, dst))

    if only is not None:
        unknown = only - set(cfg)
        if unknown:
            print('not in langs.json, ignored: %s' % ', '.join(sorted(unknown)))

    print('%d files to fetch, %d already present' % (len(todo), skipped), flush=True)
    if listing:
        for code, url, dst in todo:
            print('  %-3s %s' % (code, os.path.basename(dst)))
        print('estimate: %.1f GB (voices average 64 MB per language)'
              % (len([t for t in todo if t[2].endswith('.onnx')]) * 64 / 1024.0))
        return 0

    ok = fail = 0
    for code, url, dst in todo:
        for attempt in (1, 2, 3):
            try:
                urllib.request.urlretrieve(url, dst)
                ok += 1
                print('  %-3s %-45s %6.1f MB'
                      % (code, os.path.basename(dst), os.path.getsize(dst) / 1e6),
                      flush=True)
                break
            except Exception as e:
                if attempt == 3:
                    fail += 1
                    print('  %-3s FAILED %s (%s)' % (code, os.path.basename(dst), e),
                          flush=True)
                else:
                    time.sleep(2)
    print('done: %d ok, %d failed' % (ok, fail), flush=True)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
