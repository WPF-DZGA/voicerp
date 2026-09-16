# -*- coding: utf-8 -*-
"""Install Argos translation packs for the languages in langs.json.

Installs en->X for every target, and X->en for each source language, because
a non-English source pivots through English: Polish in, Russian out needs both
pl->en and en->ru.

  python getargos.py                    every language in langs.json
  python getargos.py --only ru,uk,pl     just those
  python getargos.py --sources en,pl     which languages you will speak
  python getargos.py --list              print the plan, install nothing
"""
import json, os, sys, time

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(HERE, 'langs.json')


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(name + '='):
            return a.split('=', 1)[1]
    return default


def main():
    only = arg('--only')
    only = {c.strip().lower() for c in only.split(',') if c.strip()} if only else None
    sources = {c.strip().lower()
               for c in (arg('--sources', 'en,pl') or '').split(',') if c.strip()}
    listing = '--list' in sys.argv

    cfg = json.load(open(CFG, encoding='utf-8'))
    targets = [c for c in sorted(cfg) if c != 'en'
               and (only is None or c in only)]

    from argostranslate import package
    package.update_package_index()
    avail = package.get_available_packages()
    have = {(p.from_code, p.to_code) for p in package.get_installed_packages()}

    want = [('en', c) for c in targets]
    for s in sorted(sources - {'en'}):
        want.append((s, 'en'))          # pivot leg
        if s in cfg:
            want.append(('en', s))
    want = [w for w in dict.fromkeys(want)]

    print('%d pairs wanted, %d already installed' % (len(want), len(have)), flush=True)
    if listing:
        for f, t in want:
            state = 'have' if (f, t) in have else 'fetch'
            print('  %-5s %s->%s' % (state, f, t))
        need = len([w for w in want if w not in have])
        print('estimate: %.1f GB (Argos packs average 120 MB each)'
              % (need * 120 / 1024.0))
        return 0

    ok = skip = miss = fail = 0
    for frm, to in want:
        if (frm, to) in have:
            skip += 1
            print('  %s->%s already' % (frm, to), flush=True)
            continue
        m = [p for p in avail if p.from_code == frm and p.to_code == to]
        if not m:
            miss += 1
            print('  %s->%s NO ARGOS PACK' % (frm, to), flush=True)
            continue
        for attempt in (1, 2, 3):
            try:
                package.install_from_path(m[0].download())
                ok += 1
                print('  %s->%s installed' % (frm, to), flush=True)
                break
            except Exception as e:
                if attempt == 3:
                    fail += 1
                    print('  %s->%s FAILED (%s)' % (frm, to, e), flush=True)
                else:
                    time.sleep(3)
    inst = sorted((p.from_code, p.to_code) for p in package.get_installed_packages())
    print('done: %d new, %d already, %d unavailable, %d failed'
          % (ok, skip, miss, fail), flush=True)
    print('installed pairs now: %d' % len(inst), flush=True)
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
