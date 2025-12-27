# MKV Subtitle Translator

Inteligentny translator napisów do filmów, który:
- 🎬 Wyciąga napisy z plików wideo (MKV, MP4, itp.)
- 📝 Tłumaczy samodzielne pliki napisów (SRT, VTT)
- 🤖 Używa OpenRouter API (dowolny model AI)
- 📦 Dzieli napisy na batche w miejscach naturalnych przerw w dialogach
- ⏱️ Zachowuje oryginalne timestampy

## Wymagania

### Wymagane narzędzia systemowe

Zainstaluj **jedno** z poniższych:

**Opcja 1: mkvtoolnix (zalecane dla plików MKV)**
```bash
# Ubuntu/Debian
sudo apt-get install mkvtoolnix

# macOS
brew install mkvtoolnix

# Windows
# Pobierz z: https://mkvtoolnix.download/
```

**Opcja 2: ffmpeg (obsługuje więcej formatów)**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Pobierz z: https://ffmpeg.org/download.html
```

### Python

- Python 3.7 lub nowszy
- pip (menedżer paczek Python)

## Instalacja

1. **Sklonuj repozytorium:**
```bash
git clone <repository-url>
cd MKV_translator
```

2. **Zainstaluj zależności Python:**
```bash
pip install -r requirements.txt
```

3. **Skonfiguruj zmienne środowiskowe:**
```bash
# Skopiuj przykładowy plik konfiguracyjny
cp .env.example .env

# Edytuj .env i wpisz swój klucz API
nano .env  # lub użyj innego edytora
```

4. **Ustaw klucz OpenRouter API w `.env`:**
```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
TARGET_LANGUAGE=polish
SOURCE_LANGUAGE=english
```

> 💡 **Jak zdobyć klucz OpenRouter API:**
> 1. Odwiedź https://openrouter.ai/
> 2. Załóż konto
> 3. Przejdź do Settings → API Keys
> 4. Wygeneruj nowy klucz
> 5. Dodaj środki do konta (pay-as-you-go)

## Użycie

### Scenariusz 1: Tłumaczenie napisów z pliku wideo

Wyciągnij napisy z pliku MKV/MP4 i przetłumacz je:

```bash
python main.py --video movie.mkv --output movie_pl.srt
```

**Z wyborem ścieżki napisów:**
```bash
# Najpierw sprawdź dostępne ścieżki (w logach)
python main.py --video movie.mkv --output movie_pl.srt --track 1
```

### Scenariusz 2: Tłumaczenie samodzielnego pliku napisów

Przetłumacz istniejący plik SRT/VTT:

```bash
python main.py --subtitle movie.srt --output movie_pl.srt
```

### Zaawansowane opcje

**Zmiana języka docelowego:**
```bash
python main.py --subtitle movie.srt --output movie_de.srt --target german
```

**Zmiana modelu AI:**
```bash
python main.py --subtitle movie.srt --output movie_pl.srt --model openai/gpt-4
```

**Dostosowanie batchowania:**
```bash
# Większe batche (szybciej, ale mniej precyzyjnie)
python main.py --subtitle movie.srt --output movie_pl.srt --max-batch-size 100 --min-gap 5.0

# Mniejsze batche (wolniej, ale bardziej precyzyjnie)
python main.py --subtitle movie.srt --output movie_pl.srt --max-batch-size 30 --min-gap 2.0
```

## Parametry

### Wymagane (jeden z dwóch)

- `--video`, `-v` - Ścieżka do pliku wideo (MKV, MP4, itp.)
- `--subtitle`, `-s` - Ścieżka do pliku napisów (SRT, VTT)

### Wymagane (zawsze)

- `--output`, `-o` - Ścieżka do pliku wyjściowego

### Opcjonalne

- `--track`, `-t` - Numer ścieżki napisów do wyciągnięcia (domyślnie: 0)
- `--target` - Język docelowy (nadpisuje .env)
- `--source` - Język źródłowy (nadpisuje .env)
- `--model` - Model OpenRouter (nadpisuje .env)
- `--min-gap` - Minimalna przerwa w sekundach dla podziału batchy (domyślnie: 3.0)
- `--max-batch-size` - Maksymalna liczba napisów w batchu (domyślnie: 50)

## Obsługiwane formaty

### Wideo (wejście)
- MKV (Matroska)
- MP4
- AVI
- Inne formaty obsługiwane przez ffmpeg/mkvtoolnix

### Napisy (wejście)
- SRT (SubRip)
- VTT (WebVTT)

### Napisy (wyjście)
- SRT (SubRip) - z zachowanymi timestampami

## Jak działa inteligentne batchowanie?

Program analizuje przerwy między napisami i dzieli je na batche w miejscach naturalnych przerw w dialogach:

1. **Wykrywa przerwy** - szuka miejsc gdzie jest cisza (domyślnie ≥3 sekundy)
2. **Tworzy batche** - grupuje napisy w logiczne segmenty
3. **Respektuje limity** - nie przekracza maksymalnej wielkości batcha
4. **Optymalizuje koszty** - mniejsze batche = mniej tokenów = niższe koszty

### Przykład:

```
Napisy 1-10: Dialog w scenie 1  ← Batch 1
[5 sekund ciszy]
Napisy 11-25: Dialog w scenie 2 ← Batch 2
[3 sekundy ciszy]
Napisy 26-40: Dialog w scenie 3 ← Batch 3
```

## Przykłady

### Podstawowe tłumaczenie
```bash
# Z pliku MKV
python main.py --video film.mkv --output film_pl.srt

# Z pliku SRT
python main.py --subtitle film.srt --output film_pl.srt
```

### Tłumaczenie na niemiecki z GPT-4
```bash
python main.py --subtitle movie.srt --output movie_de.srt \
  --target german \
  --model openai/gpt-4-turbo
```

### Wyciągnięcie drugiej ścieżki napisów i tłumaczenie
```bash
python main.py --video movie.mkv --output movie_pl.srt --track 1
```

### Szybkie tłumaczenie z dużymi batchami
```bash
python main.py --subtitle movie.srt --output movie_pl.srt \
  --max-batch-size 100 \
  --min-gap 5.0
```

## Struktura projektu

```
MKV_translator/
├── main.py                 # Główny interfejs CLI
├── subtitle_extractor.py   # Wyciąganie napisów z wideo
├── subtitle_parser.py      # Parsowanie/zapisywanie SRT/VTT
├── batch_optimizer.py      # Inteligentne dzielenie na batche
├── translator.py           # Tłumaczenie przez OpenRouter
├── requirements.txt        # Zależności Python
├── .env.example           # Przykładowa konfiguracja
├── .env                   # Twoja konfiguracja (nie commituj!)
└── README.md              # Ta dokumentacja
```

## Testy

Projekt zawiera kompleksowy zestaw testów jednostkowych i integracyjnych.

### Uruchomienie testów

**Podstawowe uruchomienie:**
```bash
pytest tests/ -v
```

**Z raportem pokrycia kodu:**
```bash
pytest tests/ -v --cov=. --cov-report=html
```

**Tylko szybkie testy (bez integracyjnych):**
```bash
pytest tests/ -v -m "not slow"
```

**Konkretny moduł:**
```bash
pytest tests/test_subtitle_parser.py -v
```

### Statystyki testów

- **64 testy** pokrywające wszystkie główne funkcjonalności
- **84% pokrycia kodu**
- Testy jednostkowe dla każdego modułu
- Testy integracyjne dla pełnego workflow

### Struktura testów

```
tests/
├── conftest.py                  # Wspólne fixtures
├── test_subtitle_parser.py      # 18 testów parsowania napisów
├── test_batch_optimizer.py      # 14 testów inteligentnego batchowania
├── test_translator.py           # 12 testów tłumaczenia API
├── test_subtitle_extractor.py   # 12 testów ekstrakcji z wideo
└── test_integration.py          # 8 testów integracyjnych
```

### Coverage HTML Report

Po uruchomieniu testów z flagą `--cov-report=html`, raport HTML zostanie wygenerowany w `htmlcov/index.html`. Otwórz go w przeglądarce aby zobaczyć szczegółowe pokrycie każdej linii kodu.

## Rozwiązywanie problemów

### Brak mkvextract lub ffmpeg

**Problem:** `RuntimeError: Neither mkvextract nor ffmpeg found`

**Rozwiązanie:** Zainstaluj jedno z narzędzi (zobacz sekcję Wymagania)

### Błąd klucza API

**Problem:** `Error: OPENROUTER_API_KEY not found in environment`

**Rozwiązanie:**
1. Sprawdź czy plik `.env` istnieje
2. Sprawdź czy zawiera poprawny klucz API
3. Upewnij się że nie ma spacji wokół `=`

### Nie znaleziono napisów w wideo

**Problem:** `Error: No subtitle tracks found in video file`

**Rozwiązanie:**
1. Sprawdź czy plik wideo zawiera napisy (np. w VLC)
2. Spróbuj wyciągnąć napisy ręcznie za pomocą mkvextract lub ffmpeg
3. Jeśli napisy są w osobnym pliku, użyj opcji `--subtitle`

### Błędy w tłumaczeniu

**Problem:** Niektóre napisy nie są przetłumaczone lub źle sformatowane

**Rozwiązanie:**
1. Spróbuj mniejszych batchy: `--max-batch-size 30`
2. Zmień model: `--model anthropic/claude-3-opus`
3. Sprawdź czy format napisów jest prawidłowy

## Koszty

Koszty zależą od:
- Wybranego modelu AI
- Długości napisów
- Liczby batchy

**Szacunkowe koszty** (dla filmu 90 min, ~1000 napisów):
- GPT-3.5 Turbo: ~$0.10-0.30
- GPT-4 Turbo: ~$1.00-3.00
- Claude 3.5 Sonnet: ~$0.50-1.50

> 💡 Tip: Używaj modeli Haiku/Mini dla niższych kosztów, lub Sonnet/GPT-4 dla lepszej jakości

## Licencja

MIT License - Zobacz plik LICENSE

## Contributing

Pull requesty mile widziane! W przypadku większych zmian, otwórz najpierw issue.

## Autor

Twój GitHub Username

## Podziękowania

- OpenRouter za API
- mkvtoolnix i ffmpeg za narzędzia
- Społeczność open source
