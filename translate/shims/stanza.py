"""Stand-in for stanza, so argostranslate can import it without torch.

argostranslate 1.11.0 does an unguarded `import stanza` in sbd.py (spacy next
to it IS guarded), and stanza imports torch at module level. That is 502 MB of
wheel, plus spacy/scipy/sympy in its train, for sentence-boundary detection we
do not use: argos ships MiniSBD and prefers it when ARGOS_CHUNK_TYPE=MINISBD.

Measured on the reference rig with torch, spacy, scipy, blis, thinc, sympy and
stanza all removed: 839 MB smaller, whisper still on CUDA, 37 languages intact,
multi-sentence splitting still correct.

This module is only reachable when torch is genuinely absent - voicerp_core
appends it to the END of sys.path, so a real stanza always wins. Touching any
attribute raises, so a code path that really needs stanza fails loudly instead
of silently translating badly.
"""

__version__ = '0.0.0-voicerp-shim'


def __getattr__(name):
    raise RuntimeError(
        'stanza is stubbed out in this install: it was skipped to avoid the '
        '502 MB torch dependency, and ARGOS_CHUNK_TYPE=MINISBD should keep '
        'stanza unused. Something asked for stanza.%s - either install the '
        'full requirements.txt or unset ARGOS_CHUNK_TYPE.' % name)
