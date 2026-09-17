"""UI strings for VoiceRP, English and Polish.

Only the interface is translated. Engine log lines (whisper backend, PortAudio
errors, exception text) stay in English on purpose: they get pasted into bug
reports and searched for verbatim.
"""

UI_LANGS = [('en', 'English'), ('pl', 'Polski')]

S = {
    'en': {
        'persona':       'PERSONA',
        'speaker':       'Speaker / accent',
        'persona_set':   'persona: %s',
        'spk_none':      '(single voice)',
        'title':         'VoiceRP',
        'help_title':    'VoiceRP - settings and recommendations',
        'out_lang':      'OUTPUT LANGUAGE',
        'filter_hint':   'type to filter',
        'voice':         'VOICE',
        'test':          'Test voice',
        'reload':        'Reload',
        'help':          'Help',
        'routing':       'ROUTING',
        'mic':           'Microphone',
        'send_to':       'Send to',
        'i_speak':       'I speak',
        'talk_key':      'Talk key',
        'headset':       'Headset',
        'monitor':       'also play in my headset',
        'idle':          'idle',
        'talking':       'TALKING',
        'peak_none':     'input peak -',
        'peak':          'input peak %+.1f dB%s',
        'clipping':      '  CLIPPING - turn the mic gain down',
        'quiet':         '  very quiet',
        'log':           'LOG',
        'ui_lang':       'Language',
        'starting':      'starting...',
        'src_en':        'English',
        'src_pl':        'Polish',
        'src_auto':      'auto-detect',
        'ready':         '%d languages ready. Hold %s to talk.',
        'skipped':       'skipped %s (%s): %s',
        'mic_failed':    'mic failed: %s',
        'out_ok':        'output -> %s',
        'out_failed':    'output failed: %s',
        'mon_failed':    'headset failed: %s',
        'mon_on':        'headset monitor on -> %s',
        'mon_off':       'headset monitor off',
        'cur_lang':      'output language: %s',
        'reloaded':      'reloaded: %d languages',
        'reload_fail':   'reload failed: %s',
        'no_hotkey':     'no global hotkey (%s); hold the key in the window instead',
        'key_set':       'talk key: %s',
        'timing':        '%.0f ms total (stt %.0f / mt %.0f / tts %.0f)  %.1f s audio%s',
        'drops':         '  %d dropped blocks',
        'help_missing':  '# Help file missing\\n\\nExpected at:\\n\\n```\\n%s\\n```\\n\\n%s',
    },
    'pl': {
        'persona':       'PERSONA',
        'speaker':       'M\u00f3wca / akcent',
        'persona_set':   'persona: %s',
        'spk_none':      '(jeden g\u0142os)',
        'title':         'VoiceRP',
        'help_title':    'VoiceRP – ustawienia i zalecenia',
        'out_lang':      'JĘZYK WYJŚCIOWY',
        'filter_hint':   'wpisz, aby filtrować',
        'voice':         'GŁOS',
        'test':          'Test głosu',
        'reload':        'Odśwież',
        'help':          'Pomoc',
        'routing':       'KIEROWANIE SYGNAŁU',
        'mic':           'Mikrofon',
        'send_to':       'Wyślij do',
        'i_speak':       'Mówię po',
        'talk_key':      'Klawisz mowy',
        'headset':       'Słuchawki',
        'monitor':       'odtwarzaj też w moich słuchawkach',
        'idle':          'bezczynny',
        'talking':       'MÓWISZ',
        'peak_none':     'szczyt wejścia –',
        'peak':          'szczyt wejścia %+.1f dB%s',
        'clipping':      '  PRZESTEROWANIE – zmniejsz czułość mikrofonu',
        'quiet':         '  bardzo cicho',
        'log':           'LOG',
        'ui_lang':       'Język',
        'starting':      'uruchamianie...',
        'src_en':        'angielsku',
        'src_pl':        'polsku',
        'src_auto':      'auto-wykrywanie',
        'ready':         'gotowych języków: %d. Przytrzymaj %s, aby mówić.',
        'skipped':       'pominięto %s (%s): %s',
        'mic_failed':    'błąd mikrofonu: %s',
        'out_ok':        'wyjście → %s',
        'out_failed':    'błąd wyjścia: %s',
        'mon_failed':    'błąd słuchawek: %s',
        'mon_on':        'podsłuch w słuchawkach wł. → %s',
        'mon_off':       'podsłuch w słuchawkach wył.',
        'cur_lang':      'język wyjściowy: %s',
        'reloaded':      'odświeżono: %d języków',
        'reload_fail':   'błąd odświeżania: %s',
        'no_hotkey':     'brak globalnego skrótu (%s); przytrzymaj klawisz w oknie',
        'key_set':       'klawisz mowy: %s',
        'timing':        '%.0f ms razem (stt %.0f / mt %.0f / tts %.0f)  %.1f s audio%s',
        'drops':         '  zgubione bloki: %d',
        'help_missing':  '# Brak pliku pomocy\\n\\nOczekiwano w:\\n\\n```\\n%s\\n```\\n\\n%s',
    },
}


# Target-language names for the picker. Polish only; English comes straight
# from langs.json, so adding a language needs no code change there.
LABEL_PL = {
    'sq':  'albański',
    'ar':  'arabski',
    'eu':  'baskijski',
    'bn':  'bengalski',
    'bg':  'bułgarski',
    'zh':  'chiński',
    'hr':  'chorwacki',
    'cs':  'czeski',
    'da':  'duński',
    'et':  'estoński',
    'fa':  'perski',
    'fi':  'fiński',
    'fr':  'francuski',
    'el':  'grecki',
    'es':  'hiszpański',
    'nl':  'holenderski',
    'he':  'hebrajski',
    'hi':  'hindi',
    'id':  'indonezyjski',
    'ja':  'japoński',
    'ca':  'kataloński',
    'ko':  'koreański',
    'lt':  'litewski',
    'lv':  'łotewski',
    'mk':  'macedoński',
    'de':  'niemiecki',
    'nb':  'norweski',
    'pl':  'polski',
    'pt':  'portugalski',
    'ru':  'rosyjski',
    'ro':  'rumuński',
    'sk':  'słowacki',
    'sl':  'słoweński',
    'sv':  'szwedzki',
    'sr':  'serbski',
    'th':  'tajski',
    'tr':  'turecki',
    'uk':  'ukraiński',
    'hu':  'węgierski',
    'it':  'włoski',
    'vi':  'wietnamski',
    'ur':  'urdu',
    'en':  'angielski',
    'ms':  'malajski',
    'tl':  'tagalski',
    'az':  'azerski',
    'be':  'białoruski',
    'ga':  'irlandzki',
    'gl':  'galicyjski',
    'eo':  'esperanto',
}

_FOLD = {0x142: 'l', 0x141: 'L', 0x142: 'l'}


def sort_key(text):
    """Collation key that puts Polish diacritics with their base letter.

    Without this, plain sorting drops we\u0328gierski after wietnamski because
    'e\u0328' orders above 'i'. locale.strcoll would need a pl_PL locale
    installed, which cannot be assumed on someone else's machine.
    """
    import unicodedata
    t = text.translate(_FOLD)
    return ''.join(c for c in unicodedata.normalize('NFKD', t)
                   if not unicodedata.combining(c)).lower()


def tr(lang, key, *args):
    """Look up a string; fall back to English, then to the key itself."""
    s = S.get(lang, S['en']).get(key) or S['en'].get(key) or key
    return s % args if args else s


def label_for(lang, code, english):
    """Language name in the UI language. Unknown code keeps the English name."""
    if lang == 'pl':
        return LABEL_PL.get(code, english)
    return english
