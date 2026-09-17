# -*- coding: utf-8 -*-
"""Fetch the multi-speaker Piper models that give VoiceRP its personas.

These are not extra languages - they are extra PEOPLE. One model file carries
many trained speakers, selected at synthesis time with speaker_id, so 76 MB can
be worth hundreds of distinct voices.

  python getpersona.py            download them
  python getpersona.py --list     show what they contain, download nothing
"""
import json, os, sys, urllib.request, time

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
VD = os.path.join(HERE, 'voices')
BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/'

# key -> (path in the repo, why it is here)
MODELS = {
    'en_US-l2arctic-medium': (
        'en/en_US/l2arctic/medium/en_US-l2arctic-medium',
        '24 non-native English speakers - Hindi, Korean, Mandarin, Spanish, '
        'Arabic and Vietnamese accents'),
    'en_GB-vctk-medium': (
        'en/en_GB/vctk/medium/en_GB-vctk-medium',
        '109 British, Scottish, Irish and regional speakers'),
    'en_US-libritts_r-medium': (
        'en/en_US/libritts_r/medium/en_US-libritts_r-medium',
        '904 American speakers - the widest choice of ages and timbres'),
    'de_DE-thorsten_emotional-medium': (
        'de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium',
        '8 emotional deliveries of one speaker - angry, amused, sleepy, '
        'whisper and more'),
    'de_DE-mls-medium': (
        'de/de_DE/mls/medium/de_DE-mls-medium', '236 German speakers'),
    'fr_FR-mls-medium': (
        'fr/fr_FR/mls/medium/fr_FR-mls-medium', '125 French speakers'),
}


def fetch(url, dst):
    for attempt in (1, 2, 3):
        try:
            urllib.request.urlretrieve(url, dst)
            return True
        except Exception as e:
            if attempt == 3:
                print('    FAILED %s (%s)' % (os.path.basename(dst), e), flush=True)
                return False
            time.sleep(2)


def main():
    os.makedirs(VD, exist_ok=True)
    listing = '--list' in sys.argv
    total = 0
    for key, (path, why) in MODELS.items():
        onnx = os.path.join(VD, key + '.onnx')
        cfg = os.path.join(VD, key + '.onnx.json')
        have = os.path.exists(onnx) and os.path.getsize(onnx) > 0
        print('%-34s %s' % (key, why), flush=True)

        if not os.path.exists(cfg) and not listing:
            fetch(BASE + path + '.onnx.json', cfg)
        if have:
            print('    already present, %.0f MB' % (os.path.getsize(onnx) / 1e6), flush=True)
        elif listing:
            print('    not downloaded yet', flush=True)
        else:
            print('    downloading ...', flush=True)
            if fetch(BASE + path + '.onnx', onnx):
                mb = os.path.getsize(onnx) / 1e6
                total += mb
                print('    %.0f MB' % mb, flush=True)

        if os.path.exists(cfg):
            try:
                d = json.load(open(cfg, encoding='utf-8'))
                smap = d.get('speaker_id_map') or {}
                print('    %d speakers' % (d.get('num_speakers', 1)), flush=True)
                if smap:
                    names = sorted(smap, key=lambda k: smap[k])
                    print('    ids: %s%s' % (', '.join(names[:24]),
                                             ' ...' if len(names) > 24 else ''),
                          flush=True)
            except Exception as e:
                print('    could not read config: %s' % e, flush=True)
        print(flush=True)
    if total:
        print('downloaded %.0f MB' % total, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
