import json, sys, time
sys.stdout.reconfigure(encoding='utf-8')
from argostranslate import package

CFG = r'D:\VoiceRP\xlate\langs.json'
cfg = json.load(open(CFG, encoding='utf-8'))
targets = [c for c in sorted(cfg) if c != 'en']

package.update_package_index()
avail = package.get_available_packages()
have = {(p.from_code, p.to_code) for p in package.get_installed_packages()}
print('targets: %d   already installed: %d pairs' % (len(targets), len(have)), flush=True)

ok = skip = miss = fail = 0
for code in targets:
    if ('en', code) in have:
        skip += 1
        print('  %-3s already' % code, flush=True)
        continue
    m = [p for p in avail if p.from_code == 'en' and p.to_code == code]
    if not m:
        miss += 1
        print('  %-3s NO ARGOS PACK' % code, flush=True)
        continue
    for attempt in (1, 2, 3):
        try:
            package.install_from_path(m[0].download())
            ok += 1
            print('  %-3s installed en->%s' % (code, code), flush=True)
            break
        except Exception as e:
            if attempt == 3:
                fail += 1
                print('  %-3s FAILED (%s)' % (code, e), flush=True)
            else:
                time.sleep(3)
inst = sorted((p.from_code, p.to_code) for p in package.get_installed_packages())
print('done: %d new, %d already, %d unavailable, %d failed' % (ok, skip, miss, fail), flush=True)
print('installed pairs now (%d): %s' % (len(inst), inst), flush=True)
