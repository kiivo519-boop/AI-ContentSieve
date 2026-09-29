# AI ContentSieve

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-CustomTkinter-1f6aa5)
![Transcription](https://img.shields.io/badge/Transcription-Local%20Whisper-412991)
![API keys](https://img.shields.io/badge/API%20keys-Not%20required-22c55e)

**From short video to reusable content—on your desktop.**  
**От короткого видео к готовому тексту — на вашем компьютере.**

English documentation below · Русская документация во второй половине файла.

---

## English

### What it does

AI ContentSieve is a dark-themed Python desktop application for creators. Paste a
public YouTube Shorts, Instagram Reels, or TikTok video URL, select an output
folder, and click **Download & Analyze**.

- **Media extraction:** yt-dlp with network retries and single-video downloads.
- **Portable video:** FFmpeg converts the source to H.264/AAC MP4, up to 1080p
  where the platform offers suitable formats; fallback formats can be larger.
- **Local speech recognition:** multilingual OpenAI Whisper `tiny` or `base`,
  running on CPU without an API key, paid service, or CUDA setup.
- **Creator-friendly exports:** timestamped script, SRT subtitles, Markdown
  analysis, and structured JSON metadata.
- **Responsive interface:** worker-thread processing, stage progress, activity
  log, transcript/analysis tabs, and an **Open results** button.
- **Temporary-file cleanup:** source downloads and WAV files are deleted after
  success or handled errors. Only a complete result folder is published.

> **What “analysis” means:** the application extracts up to three representative
> transcript segments using word-frequency scoring, shows the opening, recurring
> keywords, approximate speaking rate, and possible English/Russian calls to
> action. This is a deterministic, local extractive summary—not a generative LLM,
> visual analysis, fact checker, or prediction of engagement. Multilingual speech
> is supported by Whisper; keyword heuristics are optimized for English/Russian.

### Prerequisites

1. **Python 3.10+**, with Tkinter. Python 3.11 is a conservative starting point
   for ML dependency compatibility; installation depends on available PyTorch
   wheels for your Python/OS. On Windows, enable Python's PATH option.
2. **FFmpeg and ffprobe**, installed system-wide and available on `PATH`.
   The FFmpeg build must include `libx264` and AAC encoding. A Python package
   named `ffmpeg` does **not** replace these executables.
3. **Deno**, recommended for YouTube's JavaScript challenges. The
   `yt-dlp[default]` dependency includes the companion EJS package; Deno itself
   must be installed separately. Use the current yt-dlp-supported Deno release.
4. Internet for media downloads, dependency installation, and the first model
   download; sufficient RAM and disk for PyTorch, model weights, and media.

Official upstream references:

- yt-dlp documentation: https://github.com/yt-dlp/yt-dlp
- YouTube JavaScript setup: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- Whisper installation: https://github.com/openai/whisper
- CustomTkinter documentation: https://customtkinter.tomschimansky.com/documentation/
- FFmpeg downloads: https://ffmpeg.org/download.html
- Deno installation: https://docs.deno.com/runtime/getting_started/installation/

### Setup · Windows PowerShell

The project is located at `D:\AI_Content_Saver`. Example system-tool installation
with Windows Package Manager (if available):

```powershell
winget install --id Gyan.FFmpeg --exact
winget install --id DenoLand.Deno --exact
```

Alternatively install from the official sites above. Restart PowerShell and VS
Code after changing `PATH`, then verify:

```powershell
ffmpeg -version
ffprobe -version
deno --version
```

Create a virtual environment and install Python dependencies. Activation is not
required, avoiding PowerShell execution-policy issues:

```powershell
Set-Location D:\AI_Content_Saver
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r D:\AI_Content_Saver\requirements.txt
.\.venv\Scripts\python.exe D:\AI_Content_Saver\main.py
```

If `py` is unavailable, use `python`. On Linux/macOS, install system FFmpeg,
Deno, and Tk support via your package manager, create the virtual environment
with `python3 -m venv .venv`, and use `.venv/bin/python` instead. Linux may need
the distribution's `python3-tk` package. A graphical desktop session is required.

### Workflow

1. Paste a link to one public video—not a profile, collection, or playlist.
2. Choose a writable destination with **Browse…** (default: the project's
   `outputs` directory).
3. Select **tiny** for faster processing or **base** for a larger model.
4. Click **Download & Analyze** and follow the Activity tab.
5. Review the Transcript and Analysis tabs; open the exported result folder.

Progress represents stages, **not** a time estimate or live Whisper percentage.
Model loading/transcription can take several minutes. Only one job runs at a
time. Closing is blocked during processing to protect cleanup; cancellation is
not implemented. Forced termination can leave `.contentsieve-*` staging folders;
remove these manually only when no job is running.

### Export layout

```text
outputs/
└── contentsieve_YYYYMMDD_HHMMSS_<unique-id>/
    ├── video.mp4        # H.264 video + AAC audio
    ├── transcript.txt   # Approximate segment timestamps and original-language speech
    ├── transcript.srt   # Subtitle track
    ├── analysis.md      # Extractive summary and creator checklist
    └── metadata.json    # Source URL, title, duration, UTC export time, full segments
```

Each job uses a unique folder; existing jobs are not overwritten. UTF-8 exports
preserve Cyrillic and other Unicode text. “Clean MP4” means normalized video with
source metadata/chapters removed—not watermark removal or quality restoration.

### Architecture

```text
D:\AI_Content_Saver\
├── main.py                  # Tk widgets, event queue, background worker
├── core/
│   ├── __init__.py
│   ├── downloader.py        # URL validation, yt-dlp, FFmpeg
│   ├── transcriber.py       # Cached Whisper model, timestamp/SRT rendering
│   ├── analyzer.py          # Local extractive analysis
│   └── pipeline.py          # Staging, cleanup, transactional export
├── tests/
│   └── test_core.py         # Offline unittest suite
├── requirements.txt
├── .gitignore
└── README.md
```

### Tests and maintenance

Run from `D:\AI_Content_Saver`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s D:\AI_Content_Saver\tests -v
.\.venv\Scripts\python.exe -m compileall -q D:\AI_Content_Saver\main.py D:\AI_Content_Saver\core D:\AI_Content_Saver\tests
.\.venv\Scripts\python.exe -m pip check
```

Offline tests mock media downloads and Whisper, validating input, exports,
timestamp rounding, model reuse, analysis, and cleanup on success/failure. They
do not prove live platform availability or transcription quality. To smoke-test
the complete stack, process a short public video you own, then check playback,
subtitles, speech accuracy, and the absence of leftover WAV/staging files.

Dependencies use version ranges rather than a lockfile so yt-dlp can track
platform changes. For a validated deployment, record your exact environment
separately. Update the extractor when sites change:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade "yt-dlp[default]"
```

### Troubleshooting

| Symptom | Action |
|---|---|
| Missing FFmpeg/ffprobe | Install both executables and restart the terminal/IDE after updating PATH. |
| YouTube extraction/challenge failure | Update yt-dlp and its default extras; install/verify Deno using upstream EJS guidance. |
| Login, private, age, region, or bot restriction | Use an accessible public video. Cookie login, DRM bypass, and restriction circumvention are not implemented. |
| First transcription is slow | Whisper is downloading model weights or running on CPU. Try `tiny`. |
| PyTorch installation fails | Check upstream Whisper/PyTorch Python and platform compatibility; use a compatible Python virtual environment. |
| No audio or unsupported media | FFmpeg requires a video stream and an audio stream; try a video containing speech. |
| Incorrect subtitles | Review manually; music, silence, names, and overlapping voices can produce errors or hallucinations. |
| Permission/disk errors | Choose a writable local folder and ensure room for source, converted video, and temporary WAV. |

### Privacy, responsible use, and repository readiness

Transcription and analysis run locally. The application does not upload speech
to an AI API. Video platforms still receive download requests, and Whisper
downloads weights on first use (normally cached under `~/.cache/whisper`). That
cache and installed dependencies live outside the repository by design.
After caching, transcription itself can run offline, but this URL-download
workflow still needs internet. Exports contain the source URL and transcript:
treat them as potentially sensitive. The app does not modify your source video.

Download only content you own or have permission to use, and respect platform
terms and applicable rights. The app does not bypass DRM or remove watermarks.
It has no telemetry code, embedded credentials, or API-key requirement.

Generated outputs, local environments, and common secrets are ignored by Git.
Before publishing, choose a repository license appropriate to your project;
no license is imposed on your behalf. Review third-party licenses separately.

---

## Русский

### Обзор

**AI ContentSieve** — настольное приложение на Python с современным тёмным
интерфейсом для авторов контента. Вставьте публичную ссылку на YouTube Shorts,
Instagram Reels или TikTok, выберите папку и нажмите **Download & Analyze**.

**Возможности:**

- Загрузка одного видео через yt-dlp с повторными попытками при сетевых сбоях.
- Конвертация в совместимый MP4: H.264 + AAC. Предпочтение форматам до 1080p;
  резервный формат платформы может иметь большее разрешение.
- Локальная многоязычная транскрипция Whisper (`tiny` / `base`) на CPU.
- Текст с приблизительными таймкодами, субтитры SRT, Markdown-анализ и JSON.
- Фоновая обработка без блокировки интерфейса, журнал и индикатор этапов.
- Удаление временных WAV и исходных файлов после завершения или обработанной
  ошибки; публикация только полностью сформированного набора результатов.
- Без API-ключей, платных AI-сервисов и обязательной CUDA.

> **Важно:** анализ — локальная экстрактивная сводка по речи, а не генеративная
> языковая модель. Приложение выбирает до трёх фрагментов по частотности слов,
> показывает начало ролика, ключевые слова, примерный темп речи и возможные
> призывы к действию. Оно не анализирует изображение, не проверяет факты и не
> предсказывает охваты. Эвристики ключевых слов ориентированы на русский и
> английский; язык транскрипции определяется Whisper автоматически.

### Требования

1. **Python 3.10+ с Tkinter.** Python 3.11 — консервативный вариант для
   совместимости ML-зависимостей. Нужны подходящие сборки PyTorch для вашей ОС
   и версии Python. При установке Windows включите добавление Python в PATH.
2. **FFmpeg и ffprobe в PATH**, со сборкой, поддерживающей `libx264` и AAC.
   Установка Python-пакета `ffmpeg` не заменяет системные программы.
3. **Deno** — рекомендуется для JavaScript-проверок YouTube. Python-зависимость
   `yt-dlp[default]` включает EJS, но сам Deno устанавливается отдельно.
4. Интернет для установки, скачивания видео и первой загрузки весов Whisper;
   достаточно памяти и диска для PyTorch, моделей и временных медиафайлов.

Официальные инструкции и ссылки приведены в разделе **Prerequisites** выше.

### Установка · Windows PowerShell

При наличии Windows Package Manager:

```powershell
winget install --id Gyan.FFmpeg --exact
winget install --id DenoLand.Deno --exact
```

Можно установить инструменты вручную с официальных сайтов. Перезапустите
терминал и VS Code после изменения PATH. Проверьте установку:

```powershell
ffmpeg -version
ffprobe -version
deno --version
```

Установка и запуск проекта без активации виртуального окружения:

```powershell
Set-Location D:\AI_Content_Saver
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r D:\AI_Content_Saver\requirements.txt
.\.venv\Scripts\python.exe D:\AI_Content_Saver\main.py
```

Если команды `py` нет, используйте `python`. В Linux/macOS установите системные
FFmpeg, Deno и Tk, создайте окружение через `python3 -m venv .venv` и используйте
`.venv/bin/python`. В Linux может понадобиться пакет `python3-tk`.
Для работы требуется графическая сессия.

### Использование

1. Вставьте публичную ссылку на конкретное видео, не на профиль или плейлист.
2. Выберите папку кнопкой **Browse…**; по умолчанию используется `outputs`
   внутри каталога проекта.
3. Выберите модель: **tiny** для скорости или более крупную **base**.
4. Нажмите **Download & Analyze**, следите за вкладкой **Activity**.
5. Просмотрите **Transcript** и **Analysis**, затем нажмите **Open results**.

Полоса показывает этапы, а не оставшееся время. При первой транскрипции
скачиваются веса модели. Распознавание на CPU может занимать несколько минут.
Одновременно выполняется одна задача; закрытие окна во время обработки
заблокировано, отмена не реализована. Принудительное завершение процесса может
оставить временные папки `.contentsieve-*`; удаляйте их только при отсутствии
активной обработки.

### Результаты

Для каждой задачи создаётся уникальная папка
`contentsieve_YYYYMMDD_HHMMSS_<unique-id>` со следующими файлами:

| Файл | Содержимое |
|---|---|
| `video.mp4` | Совместимое видео H.264/AAC |
| `transcript.txt` | Расшифровка на языке оригинала с таймкодами |
| `transcript.srt` | Субтитры |
| `analysis.md` | Экстрактивная сводка, ключевые слова и чек-лист |
| `metadata.json` | Ссылка, название, длительность, UTC-время экспорта, сегменты |

Текст сохраняется в UTF-8; кириллица поддерживается. WAV удаляется. Готовые
результаты предыдущих задач не перезаписываются. «Чистый MP4» означает
нормализацию формата и удаление исходных метаданных/глав, но **не** удаление
водяных знаков. Интерфейс и заголовки отчётов англоязычные; речь не переводится.

### Устройство проекта и тесты

Структура каталогов показана в английском разделе **Architecture**.
`main.py` управляет интерфейсом и очередью событий; `core/downloader.py` —
загрузкой и FFmpeg; `core/transcriber.py` — Whisper и субтитрами;
`core/analyzer.py` — анализом текста; `core/pipeline.py` — экспортом и очисткой.

Из `D:\AI_Content_Saver` выполните:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s D:\AI_Content_Saver\tests -v
.\.venv\Scripts\python.exe -m compileall -q D:\AI_Content_Saver\main.py D:\AI_Content_Saver\core D:\AI_Content_Saver\tests
.\.venv\Scripts\python.exe -m pip check
```

Офлайн-тесты подменяют загрузчик и модель: проверяют URL, таймкоды, экспорт,
повторное использование модели, анализ и очистку временных файлов при успехе
и ошибке. Они не проверяют доступность платформ и качество распознавания.
Для полной проверки обработайте собственный публичный ролик, проверьте MP4,
субтитры, текст и отсутствие оставшихся временных WAV.

Версии зависимостей заданы диапазонами, а не lock-файлом. Для воспроизводимого
развёртывания отдельно зафиксируйте проверенное окружение. При изменениях
платформ обновляйте загрузчик:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade "yt-dlp[default]"
```

### Решение проблем

- **Нет FFmpeg/ffprobe:** установите обе программы, добавьте каталог в PATH,
  перезапустите терминал и IDE.
- **YouTube не загружается:** обновите yt-dlp с extras, проверьте Deno и
  официальную инструкцию EJS.
- **Нужен вход / ролик заблокирован:** используйте доступное публичное видео.
  Авторизация через cookies и обход ограничений/DRM не реализованы.
- **Медленно:** дождитесь загрузки модели либо выберите `tiny`.
- **Не устанавливается PyTorch:** проверьте совместимость Python и ОС по
  официальной документации Whisper/PyTorch.
- **Нет аудио:** требуется ролик с видео- и аудиодорожкой, желательно с речью.
- **Ошибки в тексте:** вручную проверьте имена, тишину, музыку и несколько
  говорящих; Whisper может ошибаться и генерировать несуществующие фразы.
- **Ошибка записи:** выберите доступную папку и освободите место для исходника,
  итогового MP4 и временного WAV.

### Приватность и ответственное использование

Аудио не отправляется в AI API; распознавание и анализ выполняются локально.
Платформы получают запросы на скачивание видео, а Whisper при первом запуске
скачивает веса в стандартный кэш, обычно `~/.cache/whisper`. Кэш и установленные
зависимости находятся вне репозитория. После загрузки весов распознавание
может работать офлайн, однако загрузка по URL требует интернета.
Экспорт содержит исходную ссылку и текст — учитывайте конфиденциальность.
В коде приложения нет телеметрии или встроенных ключей.

Скачивайте только собственный контент или материалы, на использование которых
есть разрешение. Соблюдайте правила платформ и права авторов. Приложение не
обходит DRM и не удаляет водяные знаки.

`.gitignore` исключает результаты, окружения и распространённые секреты.
Перед публикацией выберите подходящую лицензию репозитория самостоятельно;
лицензия от вашего имени не назначена. Учитывайте лицензии зависимостей.