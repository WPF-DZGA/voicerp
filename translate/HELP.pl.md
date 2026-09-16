# VoiceRP – ustawienia i zalecenia

Wszystkie istotne ustawienia, w kolejności, w jakiej należy je ustawić.
Aplikacja czyta ten plik w okno Pomocy, więc kopia w repozytorium i kopia
w aplikacji nie mogą się rozjechać.

Zasada nadrzędna: **nic nie wybiera VoiceRP jako mikrofonu.** VoiceRP sam
przejmuje prawdziwy mikrofon i zapisuje do wirtualnego kabla. Aplikacje
słuchają kabla.

---

## 1. Szybki start

1. `voicerp-gui.bat`
2. Poczekaj na `models ready (whisper on cuda, 37 languages)` w logu – 30–45 s.
3. Wybierz język wyjściowy, przytrzymaj **F9**, powiedz jedno krótkie zdanie,
   puść klawisz.

Jeśli w logu jest `whisper on cpu`, CUDA się nie wczytała. Działa nadal, tylko
około 1,2 s zamiast 0,2 s.

---

## 2. Ustawienia w samym VoiceRP

| Ustawienie | Zalecane | Dlaczego |
|---|---|---|
| Mikrofon | prawdziwy mikrofon, nie kabel | wybranie kabla podaje mu jego własne wyjście |
| Wyślij do | `CABLE Input (VB-Audio Virtual Cable)` | to usłyszą inne aplikacje |
| Mówię po | `angielsku` lub `polsku`, nie auto | auto-wykrywanie myli się na jednowyrazowych meldunkach |
| Klawisz mowy | `f9` | nie może kolidować z bindem w grze |
| Słuchawki | twoje słuchawki | używane tylko przy zaznaczonym polu poniżej |
| odtwarzaj też w słuchawkach | wł. na testach, wył. w walce | to osobny strumień, inni nie słyszą dwa razy |
| Głos | dowolny | per język, zapamiętywany |
| Język | angielski lub polski | interfejs, nie ma wpływu na tłumaczenie |

Wybory zapisują się do `translate/gui_state.json` przy każdej zmianie
i wracają przy następnym uruchomieniu. Usuń ten plik, aby zacząć od zera.

**Płeć głosu**: dziewięć języków nie ma żeńskiego głosu Piper (niemiecki,
portugalski, rumuński, bułgarski, łotewski, słoweński, albański, arabski,
perski). To ograniczenie katalogu głosów, nie ustawienie.

**Całkowicie niemożliwe**: japoński i tajski. Paczki tłumaczeń istnieją, ale
synteza mowy nie – Piper nie ma fonemizera OpenJTalk ani segmentacji wyrazów
dla tajskiego. Zapisane w `translate/langs_broken.json`.

---

## 3. Poziom mikrofonu – ustawienie, które psuje wszystko

Patrz na `szczyt wejścia` po każdym puszczeniu klawisza.

| Szczyt | Znaczenie | Zrób |
|---|---|---|
| powyżej 0 dB | przesterowanie sprzętowe | zmniejsz pokrętło czułości |
| **-30 do -6 dB** | prawidłowo | nic |
| -45 do -30 dB | używalne, cicho | podejdź bliżej |
| poniżej -60 dB | nic nie dochodzi | punkt 7 |

Przesterowany mikrofon nie daje cichej transkrypcji – daje **pewny siebie
bezsens**, na przykład „THANK YOU FOR WATCHING!". To jest wyjście whispera na
szumie. Jeśli transkrypcja nie ma nic wspólnego z tym, co powiedziałeś, sprawdź
najpierw szczyt.

Na Razer Seiren Elite zmierzony zakres pokrętła to **-2,7 dB przy minimum
i +19,5 dB przy maksimum**. Około jednej trzeciej w górę jest prawidłowo.
Całkowicie w dół też działa.

---

## 4. Ustawienia dźwięku w Windows

**Wyłącz ulepszenia dźwięku na mikrofonie.** To jest obowiązkowe.

```
Ustawienia > System > Dźwięk > Wejście > (mikrofon) > Ulepszenia dźwięku = Wyłączone
```

Windows 11 „Voice Clarity" dokłada efekt do przechwytywania z mikrofonu i może
wyciszyć studyjny mikrofon do cyfrowego zera albo zostawić spadek 30 dB poniżej
300 Hz, po którym whisper rozpoznaje zupełnie inny język. Efekt siedzi
w silniku audio, więc widzi go każda aplikacja i żadna poprawka w kodzie nie
pomoże.

Sprawdzenie z PowerShella – wartość `VocaEffectPack` oznacza, że efekt nadal
jest podłączony:

```powershell
Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Control\MMDevices\Audio\Capture" -Recurse |
  Where-Object { $_.Name -like '*FxProperties*' } |
  ForEach-Object { $_.Name; Get-ItemProperty $_.PSPath }
```

**Urządzenia domyślne.** Zdecyduj, która aplikacja ma słyszeć tłumaczenie:

| Cel | Urządzenie domyślne (odtwarzanie) | Domyślne urządzenie **komunikacji** (wejście) |
|---|---|---|
| gra słyszy tłumaczenie, Discord twój prawdziwy głos | słuchawki | `CABLE Output` |
| żadne, tylko testy | słuchawki | prawdziwy mikrofon |

Arma Reforger nie ma wyboru mikrofonu – korzysta z domyślnego urządzenia
komunikacji w Windows. Discord ma własny wybór, więc można go wskazać
bezpośrednio na mikrofon Arctis i będzie nosił twój prawdziwy głos niezależnie
od reszty.

**Nie włączaj „Nasłuchuj tego urządzenia"** na CABLE Output. Użyj pola
Słuchawki w aplikacji – Nasłuchuj dodaje własne opóźnienie i może zapętlić
dźwięk.

---

## 5. Ustawienia Discorda

```
Ustawienia > Głos i wideo
  Urządzenie wejściowe .... CABLE Output (VB-Audio Virtual Cable)  <- aby wysyłać tłumaczenie
                            albo mikrofon Arctis                   <- aby wysyłać swój głos
  Głośność wejścia ........ 100%
  Czułość wejścia ......... ręcznie, około -45 dB   (albo push-to-talk)
  Redukcja szumów ......... Brak       (NIE Krisp)
  Usuwanie echa ........... wyłączone
  Ograniczanie szumów ..... wyłączone
  Automatyczna regulacja
  czułości ................ wyłączona
```

Krisp i automatyczna regulacja czułości są zrobione pod człowieka przy
mikrofonie. Syntetyczny strumień przychodzący zrywami zostaje przycięty,
wybramkowany albo w połowie zjedzony. Jeśli tłumaczenie brzmi obcięte dla
wszystkich, a w twoich słuchawkach jest w porządku – to jest ta przyczyna.

**Push-to-talk w Discordzie walczy z push-to-talk w VoiceRP.** Albo ustaw
Discordowi aktywację głosem dla kabla, albo przypisz jego PTT do tego samego F9.

---

## 6. VB-Audio Virtual Cable

Ustawienia domyślne są prawidłowe. Kabel został tu zmierzony jako przejrzysty:
**0 zakłóceń na 124 000 próbek, stosunek tonu do śmieci 95,4 dB.** Jeśli
otwierasz jego panel:

| | |
|---|---|
| Internal Sample Rate | 48000 Hz |
| Max Latency | 7168 smp (domyślnie) |

Oba końce muszą mieć ten sam format, więc zostaw CABLE Input i CABLE Output na
**48000 Hz, 16 bit, 2 kanały** w Dźwięk > Właściwości urządzenia >
Zaawansowane.

**SteelSeries Sonar**: jego wirtualne urządzenia otwierają się wyłącznie przy
swojej dokładnej częstotliwości i liczbie kanałów – 8 kanałów przy 96 kHz dla
Gaming/Media/Aux, 2 kanały przy 48 kHz dla Chat/Microphone. VoiceRP negocjuje
to automatycznie, ale jeśli kierujesz sygnał przez Sonar zamiast wprost do
słuchawek, aplikacja celowo wybierze dziwnie wyglądającą kombinację.

---

## 7. Diagnostyka, w kolejności która najszybciej znajduje przyczynę

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| `loudest sample: -120 dB` | Voice Clarity albo mikrofon wyciszony w Windows | punkt 4 |
| transkrypcja bez związku z mową | przesterowane wejście | punkt 3 |
| nic nie słyszy, a szczyt w normie | za krótko albo `no_speech_prob` powyżej 0,9 | powiedz pełne zdanie |
| trzaski | niedobieg bufora albo piper piszący na stdout | `docs/GOTCHAS.txt` #16, #22 |
| `PaErrorCode -9999` | strumień WASAPI otwarty nie w głównym wątku | zrestartuj aplikację |
| `PaErrorCode -9997` | niezgodna częstotliwość próbkowania | punkt 6 |
| inni słyszą poszarpane | Krisp / automatyczna czułość | punkt 5 |
| inni słyszą cię podwójnie | VCClient też pisze do kabla | zamknij VCClient |

**Najpierw zmień mikrofon.** Jeśli dwa różne mikrofony zawodzą identycznie, błąd
jest w oprogramowaniu, nie w sprzęcie. Ten jeden test zakończył kiedyś godzinę
szukania winy w mikrofonie, który był sprawny.

---

## 8. Jak do tego mówić

1. **Jedna myśl na jedno przytrzymanie.** Przytrzymaj, powiedz całe krótkie
   zdanie, puść. „Kontakt północ, dwa pojazdy" zadziała. Pół zdania nie.
2. **Puszczaj czysto.** Po puszczeniu dogrywane jest 150 ms ogona; przerwanie
   w środku wyrazu gubi ten wyraz.
3. **Zrób pauzę przed kolejnym przytrzymaniem.** Poprzednia linia jeszcze się
   syntetyzuje.
4. **Krótko znaczy szybciej.** Opóźnienie zależy od długości nagrania, nie od
   trudności zdania.
5. **Liczby i znaki wywoławcze znoszą tłumaczenie źle.** Powiedz je sam
   w języku docelowym albo trzymaj w jednym zdaniu ze zwykłymi słowami.

Zmierzone na RTX 4080 / i9-13900KF: **648 ms** łącznie dla
„One, two, three, four, five." – stt 101 ms, tłumaczenie 74 ms, mowa 473 ms.
Spodziewaj się 650 ms do 1,0 s. Na samym procesorze około dwa razy tyle.

---

## 9. Praca razem ze zmieniaczem głosu

Oba narzędzia piszą do tego samego kabla. Uruchomione jednocześnie oznaczają,
że wszyscy słyszą **i** twój przetworzony głos, **i** tłumaczenie.

- Tylko tłumaczenie: zamknij okno konsoli VCClient.
- Tylko zmieniacz głosu: zamknij VoiceRP.
- Sprawdzenie, co działa: `powershell -File D:\VoiceRP\voice.ps1 -Status`

---

## 10. Zanim poprosisz o naprawę

Przygotuj te trzy rzeczy – same identyfikują prawie każdą awarię:

1. wartość `szczyt wejścia`
2. całą linię `seg [...] nsp=... logp=...`
3. czy na pasku stanu pojawiły się zgubione bloki

`docs/GOTCHAS.txt` zawiera 25 numerowanych ustaleń, każde z pomiarem, który je
udowodnił. Przeczytaj je przed zmianą jakiegokolwiek ustawienia audio.
