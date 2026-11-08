# A-OK RS485 Curtain — Home Assistant / HACS

Niestandardowa integracja Home Assistant (`cover`) dla silników zasłon A-OK korzystających z protokołu RS-485 z załączonej dokumentacji v05 (2020-01-01), połączonych z Home Assistant przez transparentny most TCP ↔ RS-485, np. **USR-DR164**.

**Status:** parser odpowiedzi statusu zweryfikowany z logiem VCOM rzeczywistego AM68-2/80-EC-P; komunikacja z Home Assistant nadal wymaga testu na urządzeniu. Nie jest oficjalną integracją A-OK ani HACS. Zanim użyjesz jej na rzeczywistej zasłonie, sprawdź ustawienia ID/kanału i krańcówki.

## Ważne dla instalacji 192.168.1.30 / ID=1 / kanał=1

- Ustawienia domyślne: `192.168.1.30:8899`, ID `1`, kanał `1`.
- W opcji **Odczytuj stan silnika** ustaw **włączone**: log VCOM potwierdził rzeczywiste ramki odpowiedzi `D8 ... XOR FF` (11 bajtów). Jeśli z Home Assistant nadal będzie timeout, wyłącz odczyt tylko diagnostycznie; sterowanie pozostanie dostępne.
- **Potwierdzone z logu VCOM:** `Zamknij = 9A 01 01 00 0A EE E4` oraz `Odczyt = 9A 01 01 00 CC 00 CC`; silnik odpowiada ramkami `D8 ... XOR FF` po 11 bajtów. `Otwórz` i `Stop` są zgodne z dokumentacją, ale w tym fragmencie logu nie ma ich jawnych wywołań. Ramka ustawienia pozycji pozostaje niezweryfikowana w logu; przed intensywnym użyciem suwaka przechwyć osobno ruch do 25% i 75%.
- Pozycja w trybie bez odczytu to *ostatnia zadana*, nie aktualna. Po STOP staje się nieznana.

## Funkcje

- Otwórz / Zamknij / Stop.
- Jedź do pozycji 0–100% za pomocą suwaka HA.
- Odczyt rzeczywistej pozycji i flagi ruchu (domyślnie włączony).
- Kreator UI (Config Flow), opcje konfiguracji, zmiana odstępu odpytywania.
- Bez chmury i bez Modbus; komunikuje się TCP z USR-DR164.

## Konfiguracja USR-DR164

1. Połącz RS-485 A(+) ↔ A(+), B(-) ↔ B(-) z zachowaniem instrukcji producentów. Zadbaj o właściwe zasilanie, wspólny punkt odniesienia gdy wymagany oraz terminację magistrali zgodnie z jej topologią.
2. Ustaw port szeregowy **2400 bps, 8 danych, bez parzystości, 1 bit stopu (8N1)**.
3. Ustaw **TCP Server**, tryb **transparent serial-to-TCP** (bez konwersji Modbus i bez przesyłania ASCII-HEX). Wybierz własny port TCP, np. 8899 (przykład, nie domyślny port sprzętu).
4. Skonfiguruj stały adres IP / rezerwację DHCP. Jeśli urządzenie ogranicza liczbę klientów TCP do jednego, unikaj jednoczesnych połączeń z innymi aplikacjami.
5. Upewnij się, że silnik ma zaprogramowane krańcówki oraz znasz jego **ID 1–99** i **kanał 1–16**. Przykładowe ID=1 i kanał=1 w dokumentacji nie muszą odpowiadać rzeczywistej konfiguracji.

## Instalacja z HACS (własne repozytorium)

**HACS nie potrafi instalować bezpośrednio z pliku ZIP.** Opublikuj zawartość tego pakietu jako repozytorium GitHub, np. `TWOJ_LOGIN/aok-rs485-homeassistant` (istotne: katalog `custom_components` ma znajdować się w głównym katalogu repozytorium).

1. W pliku `custom_components/aok_rs485/manifest.json` zastąp `REPLACE_WITH_YOUR_ACCOUNT` rzeczywistym loginem GitHub (opcjonalnie podaj prawdziwe URL dokumentacji i zgłoszeń).
2. Utwórz nowe repozytorium GitHub i wyślij do niego **zawartość** katalogu z tego pakietu.
3. W Home Assistant otwórz **HACS → menu ⋮ → Custom repositories (Własne repozytoria)**.
4. Wklej adres `https://github.com/TWOJ_LOGIN/aok-rs485-homeassistant`, wybierz typ **Integration** i dodaj.
5. Wyszukaj integrację **A-OK RS485 Curtain**, pobierz i uruchom ponownie Home Assistant.
6. Wejdź w **Ustawienia → Urządzenia i usługi → Dodaj integrację → A-OK RS485 Curtain**. Adres IP jest domyślnie ustawiony na **192.168.1.30**. Podaj port TCP, nazwę zasłony, ID silnika, kanał, timeout i okres odpytywania.
7. W ramach opcji integracji (Konfiguruj) można później zmienić parametry.

**Alternatywa do testów bez GitHub/HACS:** skopiuj `custom_components/aok_rs485` do `<config>/custom_components/aok_rs485`, uruchom ponownie HA i dodaj integrację przez UI.

## Ramki testowe (ID=1, kanał=1)

| Akcja | HEX |
|---|---|
| Otwórz | `9A 01 01 00 0A DD D7` |
| Stop | `9A 01 01 00 0A CC C6` |
| Zamknij | `9A 01 01 00 0A EE E4` |
| Odczytaj status | `9A 01 01 00 CC 00 CC` |

Pozycje: protokół silnika **0 = otwarte, 100 = zamknięte**; Home Assistant **100 = otwarte, 0 = zamknięte**. Integracja odwraca pozycję.

## Ograniczenia i bezpieczeństwo

- Test połączenia w kreatorze sprawdza **tylko TCP**, nie poprawność odpowiedzi silnika. Domyślnie odczyt statusu jest włączony; przy błędzie odczytu nie blokuje przycisków. Pozycja z poprawnej ramki statusu jest rzeczywista, w przeciwnym przypadku może być szacowana lub nieznana. Wysłanie polecenia przez TCP nie dowodzi ruchu silnika.
- Wysłanie polecenia potwierdza zapis do TCP, **nie** przyjęcie polecenia przez silnik.
- W tej wersji każde odpytywanie/komenda otwiera krótkotrwałe połączenie TCP. Adapter musi akceptować ten sposób pracy.
- Integracja adresuje pojedynczy silnik/kanał dla każdego wpisu. Przy wielu silnikach na jednym adapterze odpytywania nie są centralnie kolejkowane; w razie kolizji zwiększ interwał lub zastosuj jeden wspólny broker TCP/RS-485.
- Flagi i bajty statusu opierają się na dokumentacji v05 — kompatybilność konkretnych firmware wymaga potwierdzenia.
- Nie wykorzystywać do rolet/zasłon mogących zagrażać bezpieczeństwu bez własnych zabezpieczeń, limitów i mechanizmów stop.

## Diagnostyka

W `configuration.yaml` możesz włączyć logowanie:

```yaml
logger:
  logs:
    custom_components.aok_rs485: debug
```

Sprawdzenie składni i testów (bez wymaganego Home Assistant):

```bash
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

## Aktualizacja z poprzedniej wersji YAML

Usuń stary wpis `cover: - platform: aok_rs485` z `configuration.yaml`, zastąp stary folder `custom_components/aok_rs485` nowym, uruchom ponownie HA i skonfiguruj urządzenie przez UI. Nazwa encji może się zmienić — sprawdź automatyzacje.

## Weryfikacja VCOM — log listopad 2026

- `COM 9A 01 01 00 0A EE E4` — zamknij (potwierdzone w logu).
- `COM 9A 01 01 00 CC 00 CC` — zapytanie statusowe (potwierdzone wielokrotnie).
- `NET D8 01 01 00 05 18 00 64 02 7B FF` — odpowiedź 11 bajtów: pozycja napędu 100%, brak ruchu.
- `NET D8 01 01 00 03 18 1F 01 03 06 FF` — pozycja napędu 1%, flaga ruchu.
- Ramka odpowiedzi: nagłówek `D8`, 8 bajtów danych, XOR, końcowe `FF` (11 bajtów). Odbiór TCP może dzielić lub łączyć ramki: nie należy zakładać, że jedno `read()` zwróci całość.
- **Pozycja zadana:** w tym fragmencie brak zidentyfikowanego polecenia procentowego, dlatego `position_frame` pozostaje implementacją według dokumentacji, nie testem empirycznym.
- Logi VCOM z powtarzającymi się wpisami COM nie dowodzą konieczności dwukrotnego wysyłania komend (mogą to być duplikaty narzędzia).
- Aby uniknąć konfliktu TCP, wyłącz USR-VCOM/aplikację A-OK przy uruchamianiu Home Assistant.


## Wersja 1.3.1: odczyt rzeczywistej pozycji

- W **Ustawienia → Urządzenia i usługi → A-OK RS485 → Konfiguruj** włącz `Odczyt statusu` / `Poll status` i ustaw interwał 5–10 sekund. **Uwaga:** aktualizacja nie nadpisuje wartości zapisanej we wcześniejszej konfiguracji (wersja 1.2.0 domyślnie wyłączała odczyt).
- Realne ramki z VCOM `D8 01 01 00 XX 18 XX PP XX XOR FF` mają 11 bajtów; `PP` jest pozycją silnika 0–100%. Home Assistant pokazuje `100 - PP`.
- Po komendzie ruchu integracja nie nadpisuje prawdziwej pozycji celem; odczytuje stan ponownie i kontynuuje cykliczne odpytywanie.
- Opcjonalnie włącz `logger: {logs: {custom_components.aok_rs485: debug}}`, aby w logu zobaczyć `A-OK TX`, `A-OK RX` oraz `A-OK position: motor=... HA=...`.
- Na czas korzystania z Home Assistant zamknij A-OK i **rozłącz USR-VCOM**, ponieważ równoczesne połączenia wcześniej kolidowały.
- Komenda `Ustaw pozycję` wciąż wymaga potwierdzenia na fizycznym silniku; log VCOM nie zawiera jednoznacznego pakietu jej żądania.
