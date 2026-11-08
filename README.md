# A-OK RS485 Curtain — Home Assistant / HACS

Niestandardowa integracja Home Assistant (`cover`) dla silników zasłon A-OK korzystających z protokołu RS-485 z załączonej dokumentacji v05 (2020-01-01), połączonych z Home Assistant przez transparentny most TCP ↔ RS-485, np. **USR-DR164**.

**Status:** implementacja przetestowana testami jednostkowymi; **niezweryfikowana z fizycznym AM68-2/80-EC-P ani USR-DR164**. Nie jest oficjalną integracją A-OK ani HACS. Zanim użyjesz jej na rzeczywistej zasłonie, sprawdź ustawienia ID/kanału i krańcówki.

## Funkcje

- Otwórz / Zamknij / Stop.
- Jedź do pozycji 0–100% za pomocą suwaka HA.
- Odczyt pozycji i flagi ruchu (jeżeli silnik odsyła ramki statusowe w formacie opisanym w specyfikacji).
- Kreator UI (Config Flow), opcje konfiguracji, zmiana odstępu odpytywania.
- Bez chmury i bez Modbus; komunikuje się TCP z USR-DR164.

## Konfiguracja USR-DR164

1. Połącz RS-485 A(+) ↔ A(+), B(-) ↔ B(-) z zachowaniem instrukcji producentów. Zadbaj o właściwe zasilanie, wspólny punkt odniesienia gdy wymagany oraz terminację magistrali zgodnie z jej topologią.
2. Ustaw port szeregowy **2400 bps, 8 danych, bez parzystości, 1 bit stopu (8N1)**.
3. Ustaw **TCP Server**, tryb **transparent serial-to-TCP** (bez konwersji Modbus i bez przesyłania ASCII-HEX). Wybierz własny port TCP, np. 8899 (przykład, nie domyślny port sprzętu).
4. Skonfiguruj stały adres IP / rezerwację DHCP. Jeśli urządzenie ogranicza liczbę klientów TCP do jednego, unikaj jednoczesnych połączeń z innymi aplikacjami.
5. Upewnij się, że silnik ma zaprogramowane krańcówki oraz znasz jego **ID 1–99** i **kanał 1–16**. Przykładowe ID=9 i kanał=8 w dokumentacji nie muszą odpowiadać rzeczywistej konfiguracji.

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

## Przykładowe ramki (ID=9, kanał=8)

| Akcja | HEX |
|---|---|
| Otwórz | `9A 09 80 00 0A DD 5E` |
| Stop | `9A 09 80 00 0A CC 4F` |
| Zamknij | `9A 09 80 00 0A EE 6D` |
| Odczytaj status | `9A 09 80 00 CC 00 45` |

Pozycje: protokół silnika **0 = otwarte, 100 = zamknięte**; Home Assistant **100 = otwarte, 0 = zamknięte**. Integracja odwraca pozycję.

## Ograniczenia i bezpieczeństwo

- Test połączenia w kreatorze sprawdza **tylko TCP**, nie poprawność odpowiedzi silnika. Stan zasłony pozostanie „niedostępny”, jeśli odczyt RS-485 nie powiedzie się.
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
