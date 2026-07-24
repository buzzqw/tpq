# TPQ — Terminale Python Qt

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt-6-green)](https://riverbankcomputing.com/software/pyqt)
[![License](https://img.shields.io/badge/License-EUPL%201.2-blue)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Beta-orange)](#project-status)

**TPQ** is an advanced terminal emulator for Linux built with Python, PyQt6, and pyte.
It combines a full-featured terminal with AI chat capabilities, command history
search, and a built-in notes system — all in a modern Qt interface.

> ⚡ Inspired by xfce4-terminal. Enhanced with AI and local smarts.

> **Project status:** TPQ is under active development and should be considered
> **beta quality**. Core terminal usage, history, notes, and Ollama-based AI chat
> are exercised regularly; other AI providers and some edge cases are less
> battle-tested. Expect occasional rough edges, back up important workflows,
> and please report issues.

For the complete, in-depth user guide (Italian), see **[manual.md](manual.md)**.

---

## Screenshots

<!-- Replace with actual screenshots -->
```
┌─ TPQ Terminal ──────────────────────────────────────────────────┐
│ File  Edit  View  Terminal  Tabs  Help                         │
│ [New Tab] [New Window] | [Copy] [Paste] | TPQ — Terminal       │
├─────────────────────────────────────────────────────────────────┤
│ Terminal 1 │ Terminal 2 × │                                    │
├─────────────────────────────────────────────────────────────────┤
│ user@host:~$ /connect                                          │
│                                                                │
│ Available providers:                                           │
│   [1] ● DeepSeek (Pro)                                        │
│   [2] ● Ollama (Local) (llama3.2:3b) [1 models]               │
│ Press Alt+1..9 to select a provider.                           │
│                                                                │
│ user@host:~$ █                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Terminal
- Full terminal emulation via **pyte** (ANSI/xterm-256color, true color)
- Tabs with **detach**, **move**, **reorder**, **rename**
- **Scrollback** with configurable limit (or unlimited, `0`)
- **Scrollbar** (left/right/off), **toolbar**, **menu bar** toggle
- **16-color ANSI palette** editor with 7 presets: Dark, Light, Solarized Dark,
  Solarized Light, Monokai, Gruvbox Dark, Nord
- Configurable **cursor** (block/underline/beam, blink, color)
- **Encoding** per tab (UTF-8, Latin-1/9, UTF-16 (BE/LE), CP1252, CP850, ASCII,
  KOI8-R, Shift_JIS, EUC-JP, GBK)
- **Backspace/Delete** key behavior customization (ASCII DEL, Control-H, escape
  sequence, auto-detect)
- **Read-Only** mode
- **Fullscreen** mode (F11)
- **Send Signal**: SIGTERM, SIGKILL, SIGHUP, SIGINT, SIGQUIT, SIGSTOP, SIGCONT,
  SIGUSR1, SIGUSR2

### AI Chat (built-in)
- `/ai` — Enter AI chat mode directly in the terminal
- `/ai off` — Return to shell
- `/connect [provider]` — Interactive provider/model selection
- Supports **6 providers**:

| Provider | Type | Default Model | API Key |
|----------|------|----------------|---------|
| **OpenAI** | Cloud | `gpt-4o` | Required |
| **Claude** (Anthropic) | Cloud | `claude-sonnet-4-20250514` | Required |
| **Gemini** (Google) | Cloud | `gemini-2.5-flash` | Required |
| **DeepSeek** | Cloud | `deepseek-chat` | Required |
| **Ollama** | Local | `llama3` | Not required |
| **Custom API** | Local/Any | configurable | Optional |

- **Auto-detection** of installed Ollama models and OpenAI-compatible endpoints
  (queries `/api/tags` or `/models`)
- Interactive model selection with `1`–`9` (or `Alt+1..9`)
- Responses stream token-by-token for OpenAI, Claude, DeepSeek, Ollama and
  Custom; **Gemini replies arrive as a single block** (Google's REST
  `generateContent` endpoint isn't incremental), not word-by-word

### Smart Commands
| Command | Description |
|---------|-------------|
| `/history [terms]` | Search command history (AND logic: `ssh 167`) |
| `/ai` | Enter AI chat mode |
| `/ai off` | Exit AI chat mode |
| `/connect [provider]` | Select AI provider/model (`openai\|claude\|gemini\|deepseek\|ollama\|custom`) |
| `/wnotes [-file.md] text` | Save a timestamped note |
| `/onotes [-file.md]` | Open notes in configured editor |
| `/clear` (or `/cls`) | Clear the terminal screen |
| `/help` | Show all commands |
| `Tab` (after `/`) | Autocomplete TPQ commands (`/hist` → `/history`) |

### History
- **SQLite-backed** command history (`~/.config/tpq/history.db`) with full-text search
- **Ctrl+R**: Interactive reverse-i-search
- `/history ssh 167`: Search commands containing both "ssh" and "167"
- **1..9** (after a `/history` or `/connect` list): pick a result
- **Alt+1..9**: Re-execute a history result by number from anywhere

### Other
- **Right-click context menu**: Copy, Paste, Open File Manager Here
- **File Manager integration**: Opens nemo/thunar/dolphin/nautilus/pcmanfm/caja/spacefm in CWD
- **Auto-copy** selection to clipboard (configurable)
- **Configurable prompts**: initial/dynamic title modes
- **Unsafe paste** warning (configurable)
- **Login shell** option and custom shell command

---

## Installation

### Quick Install
```bash
git clone https://github.com/buzzqw/tpq.git
cd tpq
chmod +x setup.sh
./setup.sh
```

The setup script installs [uv](https://docs.astral.sh/uv/), creates a virtual
environment, and installs all Python dependencies automatically.

### Manual Install
```bash
# System dependencies (Debian/Ubuntu)
sudo apt install python3-pyqt6

# Using uv
uv venv .venv
source .venv/bin/activate
uv pip install pyte requests PyQt6

# Or using pip
pip install pyte requests PyQt6
```

### Run
```bash
./tpq.sh
# or
source .venv/bin/activate && python -m tpq
```

---

## Configuration

Settings are stored in `~/.config/tpq/settings.json`.

All options can be configured via **Edit > Preferences** (7 tabs: General,
Appearance, Colors, Compatibility, AI, Notes, About), including:
- Font, colors, cursor, transparency
- 16-color palette with 7 presets
- AI API keys, URLs, and models for all 6 providers
- Shell command, login shell
- Encoding, backspace/delete key bindings
- Notes directory, default file, and editor
- Scrollback, scrollbar position

### AI Setup Example
```json
{
  "ai_keys": {
    "openai": "sk-...",
    "deepseek": "sk-..."
  },
  "ai_models": {
    "openai": "gpt-4o",
    "ollama": "llama3.2:3b"
  },
  "ai_urls": {
    "ollama": "http://localhost:11434/v1/chat/completions"
  }
}
```

Then in TPQ:
```
/connect           → choose from configured providers
/connect ollama    → show Ollama models
/ai                → start chatting
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+T` | New Tab |
| `Ctrl+Shift+N` | New Window |
| `Ctrl+Shift+W` | Close Tab |
| `Ctrl+Shift+Q` / `Ctrl+Q` | Close Window |
| `Ctrl+Shift+C` | Copy |
| `Ctrl+Shift+V` | Paste |
| `Ctrl+Shift+A` | Select All |
| `Ctrl+Shift+S` | Set Title |
| `Ctrl+Shift+R` | Reset Terminal |
| `Ctrl+Shift+X` | Reset and Clear |
| `Ctrl+Plus` | Zoom In |
| `Ctrl+-` | Zoom Out |
| `Ctrl+0` | Zoom Reset |
| `Ctrl+R` | Interactive History Search |
| `Ctrl+L` | Clear Screen |
| `Ctrl+C` | Interrupt (SIGINT) |
| `Ctrl+D` | EOF (when line empty) |
| `Ctrl+U` | Kill line |
| `Ctrl+W` | Kill word |
| `F11` | Fullscreen |
| `Ctrl+PageUp` / `Ctrl+PageDown` | Previous / Next Tab |
| `Ctrl+Shift+PageUp` / `Ctrl+Shift+PageDown` | Move Tab Left / Right |
| `Alt+1..9` | Select provider / model / history result |

---

## Requirements

- **Python** ≥ 3.10
- **PyQt6** (system package: `python3-pyqt6`)
- **pyte** ≥ 0.8
- **requests**
- **Linux** with X11 or Wayland
- **Ollama** (optional, for local AI)

---

## Project Structure

```
tpq/
├── tpq/
│   ├── __init__.py        # Package init
│   ├── __main__.py        # Entry point
│   ├── main.py             # MainWindow, tab management, toolbar
│   ├── terminal.py         # PTY + pyte terminal widget (~1500 lines)
│   ├── history.py          # SQLite command history with search
│   ├── ai_client.py        # Multi-provider AI API client
│   ├── notes.py            # Timestamped notes manager
│   ├── settings.py         # JSON config singleton
│   ├── settings_dialog.py  # Full preferences GUI (7 tabs)
│   └── menus.py            # xfce4-terminal-compatible menu bar
├── pyproject.toml         # Python project metadata
├── setup.sh               # One-command installer
├── tpq.sh                 # Launcher script
├── README.md              # This file
└── manual.md              # Full user manual (Italian)
```

---

## License

**EUPL 1.2** (European Union Public License) — see [LICENSE](LICENSE)

**Author:** Andres Zanzani

---

## Acknowledgements

- [pyte](https://github.com/selectel/pyte) — In-memory VTxxx terminal emulator
- [PyQt6](https://riverbankcomputing.com/software/pyqt) — Python bindings for Qt6
- [xfce4-terminal](https://docs.xfce.org/apps/terminal/start) — Design inspiration
- [Ollama](https://ollama.com) — Local LLM runtime
