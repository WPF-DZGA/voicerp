# -*- coding: utf-8 -*-
"""Render an audition sheet so personas can be judged by ear, not by argument.

Each sample is announced by a spoken index, so you can listen once and write
down the numbers you want. Writes one .mp3 per set plus an index .txt.

  python make_samples.py                     archetypes on English and Russian
  python make_samples.py --lang ru
  python make_samples.py --speakers en_US-l2arctic-medium
  python make_samples.py --speakers en_US-libritts_r-medium --limit 24
"""
import json, os, subprocess, sys, wave
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import voicerp_core as core

OUT = os.path.join(HERE, 'samples')
LINE = {
    'en': 'Contact north, two vehicles, moving fast. Hold your position.',
    'ru': 'Contact north, two vehicles, moving fast. Hold your position.',
    'pl': 'Contact north, two vehicles, moving fast. Hold your position.',
    'de': 'Contact north, two vehicles, moving fast. Hold your position.',
}


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def announce(eng, n):
    """A neutral English voice saying the index, so samples are identifiable."""
    sig, sr = eng.synth('Number %d.' % n, ANNOUNCE_VOICE, 'neutral')
    return (sig, sr) if sig is not None else (None, None)


def to_mp3(chunks, sr, path):
    pcm = np.concatenate([c for c in chunks if c is not None and len(c)])
    pcm = np.clip(pcm, -1, 1)
    raw = (pcm * 32767).astype('<i2').tobytes()
    wav = path.replace('.mp3', '.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(raw)
    try:
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav,
                        '-codec:a', 'libmp3lame', '-b:a', '96k', path],
                       check=True, timeout=300)
        os.remove(wav)
        return path
    except Exception as e:
        print('  ffmpeg unavailable (%s), keeping the wav' % e)
        return wav


def resample_to(sig, sr, target):
    return core.resample(sig, sr, target) if sr != target else sig


def main():
    os.makedirs(OUT, exist_ok=True)
    eng = core.Engine()
    print('loading models ...', flush=True)
    eng.load_models()

    global ANNOUNCE_VOICE
    ANNOUNCE_VOICE = None
    for cand in ('en_US-lessac-medium.onnx', 'en_US-amy-medium.onnx'):
        if os.path.exists(os.path.join(core.VOICES_DIR, cand)):
            ANNOUNCE_VOICE = cand
            break
    if ANNOUNCE_VOICE is None and 'en' in eng.langs:
        ANNOUNCE_VOICE = eng.langs['en']['voice']
    print('announcer: %s' % ANNOUNCE_VOICE, flush=True)

    gap = None
    speakers_model = arg('--speakers')
    limit = int(arg('--limit', '0') or 0)
    SR = 22050

    if speakers_model:
        # audition the speakers of one multi-speaker model, neutral prosody
        voice = speakers_model + '.onnx'
        smap = core.speakers_for(voice)
        if not smap:
            print('%s has no speaker map' % voice)
            return 1
        names = sorted(smap, key=lambda k: smap[k])
        if limit:
            names = names[:limit]
        groups = ((eng.speaker_sets.get(speakers_model) or {}).get('groups') or {})
        rev = {}
        for gname, members in groups.items():
            for m in members:
                rev[m] = gname

        chunks, index = [], []
        gap = np.zeros(int(SR * 0.35), dtype=np.float32)
        for i, name in enumerate(names, 1):
            eng.speaker_override[voice] = name
            a, asr = announce(eng, i)
            if a is not None:
                chunks += [resample_to(a, asr, SR), gap]
            sig, sr = eng.synth(LINE['en'], voice, 'neutral')
            if sig is None:
                print('  %3d %-8s FAILED %s' % (i, name, sr))
                continue
            chunks += [resample_to(sig, sr, SR), gap, gap]
            tag = rev.get(name, '')
            index.append('%3d  %-8s %s' % (i, name, tag))
            print('  %3d %-8s %s' % (i, name, tag), flush=True)
        eng.speaker_override.pop(voice, None)
        base = os.path.join(OUT, 'speakers-%s' % speakers_model)
    else:
        lang = arg('--lang', 'en')
        if lang not in eng.langs:
            print('%s not installed' % lang)
            return 1
        voice = eng.voice_for(lang)
        chunks, index = [], []
        gap = np.zeros(int(SR * 0.35), dtype=np.float32)
        order = ['neutral', 'radio_operator', 'military_nco', 'officer_calm',
                 'gruff_veteran', 'old_farmer', 'young_recruit', 'panicked',
                 'wounded', 'cqb_whisper', 'long_range', 'drunk_civilian',
                 'angry_shout']
        order = [p for p in order if p in eng.personas] + \
                [p for p in eng.personas if p not in order]
        txt = LINE.get(lang, LINE['en'])
        if lang != 'en':
            try:
                txt = eng.argos.translate(LINE['en'], 'en', lang)
            except Exception:
                pass
        print('line: %s' % txt, flush=True)
        for i, pid in enumerate(order, 1):
            a, asr = announce(eng, i)
            if a is not None:
                chunks += [resample_to(a, asr, SR), gap]
            sig, sr = eng.synth(txt, voice, pid)
            if sig is None:
                print('  %3d %-16s FAILED %s' % (i, pid, sr))
                continue
            chunks += [resample_to(sig, sr, SR), gap, gap]
            index.append('%3d  %-16s %s' % (i, pid,
                                            eng.personas[pid].get('label', '')))
            print('  %3d %-16s %s' % (i, pid, eng.personas[pid].get('label', '')),
                  flush=True)
        base = os.path.join(OUT, 'personas-%s' % lang)

    path = to_mp3(chunks, SR, base + '.mp3')
    open(base + '.txt', 'w', encoding='utf-8').write('\n'.join(index) + '\n')
    print()
    print('wrote %s (%.1f MB)' % (path, os.path.getsize(path) / 1e6))
    print('wrote %s' % (base + '.txt'))
    eng.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
