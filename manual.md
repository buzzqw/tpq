# TPQ — Manuale d'Uso

> **Stato del progetto:** TPQ e' in fase di sviluppo attivo ed e' da
> considerarsi **beta**. L'uso base del terminale, la history, le note e la
> chat AI con Ollama sono testati regolarmente; gli altri provider AI e alcuni
> casi limite lo sono meno. Aspettati qualche imperfezione e segnala pure i
> problemi che incontri.

## Indice

1. [Avvio Rapido](#1-avvio-rapido)
2. [Interfaccia](#2-interfaccia)
3. [Comandi TPQ](#3-comandi-tpq)
4. [AI Chat](#4-ai-chat)
5. [History](#5-history)
6. [Notes](#6-notes)
7. [Tabs e Finestre](#7-tabs-e-finestre)
8. [Preferenze](#8-preferenze)
9. [Segnali e Encoding](#9-segnali-e-encoding)
10. [Risoluzione Problemi](#10-risoluzione-problemi)

---

## 1. Avvio Rapido

```bash
cd tpq
./tpq.sh
```

Oppure:

```bash
source .venv/bin/activate
python -m tpq
```

---

## 2. Interfaccia

### Menu Bar

- **File**: Nuovo Tab, Nuova Finestra, Apri Gestore File Qui, Chiudi Tab/Finestra, Esci
- **Edit**: Copia, Incolla, Incolla Selezione, Seleziona Tutto, Preferenze
- **View**: Mostra/Nascondi Tabs, Menu Bar, Toolbar, Scrollbar, Fullscreen, Zoom
- **Terminal**: Imposta Titolo, Encoding, Invia Segnale, Reset, Read-Only, Navigazione Tab
- **Tabs**: Lista dei tab aperti (click per passare)
- **Help**: About

### Toolbar

Attivabile da `View > Always Show Toolbar`. Contiene:
- Nuovo Tab, Nuova Finestra, Copia, Incolla, Titolo dinamico

### Scrollbar

Posizione configurabile: destra, sinistra, o disabilitata (`Preferences > General`).

### Titolo Dinamico

Configurabile: sostituisce, precede, segue, o non mostra il titolo impostato
dalle applicazioni terminale.

---

## 3. Comandi TPQ

I comandi speciali iniziano con `/` e vengono processati da TPQ, non dalla shell.

### /history

```
/history                  # Mostra ultimi 30 comandi
/history ssh 167          # Cerca comandi con "ssh" E "167"
/history git push         # Cerca comandi con "git" E "push"
```

Dopo la lista, premi `Alt+1`...`Alt+9` per rieseguire il comando corrispondente.

### /ai

```
/ai                       # Entra in modalità chat AI
/ai off                   # Esce dalla chat AI
```

Vedi [Sezione 4](#4-ai-chat) per i dettagli.

### /connect

```
/connect                  # Mostra tutti i provider configurati
/connect ollama           # Mostra i modelli Ollama disponibili
/connect openai           # Connetti a OpenAI col modello predefinito
```

Vedi [Sezione 4.3](#43-connessione) per i dettagli.

### /wnotes

```
/wnotes Riunione del 24/7: decidere stack tecnologico
/wnotes -progetto.md Da fare: refactor modulo auth
```

Salva una nota con timestamp nel file note predefinito (o in quello specificato
dopo `-`).

### /onotes

```
/onotes                   # Apre il file note predefinito nell'editor
/onotes -progetto.md      # Apre progetto.md nell'editor
```

L'editor e' configurabile in `Preferences > Notes`.

### /help

Mostra la lista di tutti i comandi TPQ disponibili.

### /clear

Pulisce lo schermo del terminale. Alias: `/cls`.

### Autocompletamento con Tab

Quando scrivi un comando TPQ, premi `Tab` per autocompletare:

```
/hist [Tab] → /history
/c [Tab]    → mostra /connect, /clear
/h [Tab]    → mostra /history, /help
/a [Tab]    → /ai
/w [Tab]    → mostra /wnotes
/o [Tab]    → /onotes
```

---

## 4. AI Chat

### 4.1 Provider Supportati

| Provider | Tipo | Modello predefinito | API Key Necessaria |
|----------|------|----------------------|--------------------|
| OpenAI | Cloud | `gpt-4o` | Si |
| Claude (Anthropic) | Cloud | `claude-sonnet-4-20250514` | Si |
| Google Gemini | Cloud | `gemini-2.5-flash` | Si |
| DeepSeek | Cloud | `deepseek-chat` | Si |
| Ollama | Locale | `llama3` (auto-rileva quelli installati) | No |
| Custom API | Locale/Remoto | configurabile | Opzionale |

Tutti i provider rispondono in streaming, token per token, **eccetto Gemini**:
l'API REST `generateContent` di Google usata da TPQ non e' incrementale, quindi
la risposta di Gemini compare tutta insieme invece che carattere per carattere
come per gli altri provider.

### 4.2 Configurazione

1. Vai su `Edit > Preferences > AI`
2. Inserisci la API key per i provider cloud
3. Per Ollama: non serve API key. Assicurati che `ollama serve` sia in esecuzione
4. Per Custom: imposta l'URL del tuo endpoint (es. `http://localhost:8080/v1/chat/completions`)

### 4.3 Connessione

```bash
# Mostra tutti i provider configurati
/connect

# Output esempio:
# Available providers:
#   [1] ● DeepSeek (Pro)
#   [2] ● Ollama (Local) (llama3.2:3b) [1 models]
# Press Alt+1..9 to select a provider.
```

Premi `Alt+1` o `Alt+2` per selezionare il provider. Se il provider ha piu'
modelli (es. Ollama), ti verra' chiesto di scegliere il modello.

### 4.4 Chat

```bash
/ai
```

```
=== AI Chat Mode: Ollama (Local) (llama3.2:3b) ===
Type your message and press Enter. Type /ai off to exit.

You> spiegami come funziona Docker
AI> Thinking...
AI> Docker è una piattaforma di containerizzazione che...
You> /ai off

=== AI Chat Ended ===
user@host:~$ █
```

### 4.5 Ollama — Auto-rilevamento Modelli

Quando ti connetti a Ollama, TPQ interroga automaticamente l'API Ollama
(`http://localhost:11434/api/tags`) e mostra i modelli installati:

```
/connect ollama
```

```
Ollama (Local) — 3 models:
  [1] llama3.2:3b (current)
  [2] codellama:latest
  [3] mistral:7b
Press Alt+1..9 to select, any other key for default.
```

### 4.6 Custom API

Qualsiasi server compatibile con l'API OpenAI puo' essere usato:

- **llama.cpp**: `http://localhost:8080/v1/chat/completions`
- **vLLM**: `http://localhost:8000/v1/chat/completions`
- **text-generation-webui**: `http://localhost:5000/v1/chat/completions`
- **LM Studio**: `http://localhost:1234/v1/chat/completions`

Configura l'URL in `Preferences > AI > Custom URL`.

---

## 5. History

### 5.1 Ricerca Interattiva (Ctrl+R)

Premi `Ctrl+R` in qualsiasi momento per avviare la ricerca interattiva:

```
(reverse-i-search)`git`: 1/3
```

- **Digita** per filtrare i risultati
- **Ctrl+R** di nuovo per scorrere i match
- **Frecce su/giu'** per navigare
- **Enter** per eseguire il comando selezionato
- **Esc** per annullare

### 5.2 Ricerca con /history

```
/history ssh            # Tutti i comandi con "ssh"
/history git push       # Comandi con ENTRAMBI "git" e "push"
/history docker 167     # Comandi con "docker" E "167"
```

La ricerca usa logica AND: tutti i termini devono apparire nel comando.

### 5.3 Riesecuzione

Dopo `/history`, ogni risultato ha un numero `[1]`, `[2]`, ... `[9]`.
Premi `Alt+1`...`Alt+9` per eseguire immediatamente quel comando.

---

## 6. Notes

### 6.1 Scrivere una Nota

```bash
/wnotes Appunti sulla riunione: decisioni prese...
```

La nota viene salvata con timestamp nel file configurato (default: `~/notes.md`):

```markdown
## 2026-07-24 14:30:00

Appunti sulla riunione: decisioni prese...
```

### 6.2 Note con Nome Personalizzato

```bash
/wnotes -progetto.md Task per oggi: completare modulo X
```

Salva in `progetto.md` nella directory configurata.

### 6.3 Aprire le Note

```bash
/onotes                   # Apre ~/notes.md con l'editor
/onotes -progetto.md      # Apre progetto.md
```

Editor configurabile in `Preferences > Notes > Editor command` (default: `nano`).

---

## 7. Tabs e Finestre

### 7.1 Gestione Tab

| Azione | Menu | Shortcut |
|--------|------|----------|
| Nuovo Tab | File > New Tab | `Ctrl+Shift+T` |
| Chiudi Tab | File > Close Tab | `Ctrl+Shift+W` |
| Tab Precedente | Terminal > Previous Tab | `Ctrl+PageUp` |
| Tab Successivo | Terminal > Next Tab | `Ctrl+PageDown` |
| Sposta Tab a Sx | Terminal > Move Tab Left | `Ctrl+Shift+PageUp` |
| Sposta Tab a Dx | Terminal > Move Tab Right | `Ctrl+Shift+PageDown` |
| Stacca Tab | Terminal > Detach Tab | — |
| Rinomina Tab | Terminal > Set Title | `Ctrl+Shift+S` |
| Lista Tab | Tabs > [seleziona] | — |

### 7.2 Nuova Finestra

`File > New Window` o `Ctrl+Shift+N` apre una nuova finestra TPQ indipendente.

### 7.3 Fullscreen

`View > Full Screen` o `F11`.

### 7.4 Tutte le Scorciatoie da Tastiera

| Scorciatoia | Azione |
|-------------|--------|
| `Ctrl+Shift+T` | Nuovo Tab |
| `Ctrl+Shift+N` | Nuova Finestra |
| `Ctrl+Shift+W` | Chiudi Tab |
| `Ctrl+Shift+Q` / `Ctrl+Q` | Chiudi Finestra |
| `Ctrl+Shift+C` | Copia |
| `Ctrl+Shift+V` | Incolla |
| `Ctrl+Shift+A` | Seleziona Tutto |
| `Ctrl+Shift+S` | Imposta Titolo |
| `Ctrl+Shift+R` | Reset Terminale |
| `Ctrl+Shift+X` | Reset e Pulisci |
| `Ctrl+Plus` / `Ctrl+-` / `Ctrl+0` | Zoom In / Out / Reset |
| `Ctrl+R` | Ricerca history interattiva |
| `Ctrl+L` | Pulisci schermo |
| `Ctrl+C` | Interrompi (SIGINT) |
| `Ctrl+D` | EOF (a riga vuota) |
| `Ctrl+U` | Cancella riga |
| `Ctrl+W` | Cancella parola |
| `F11` | Fullscreen |
| `Ctrl+PageUp` / `Ctrl+PageDown` | Tab Precedente / Successivo |
| `Ctrl+Shift+PageUp` / `Ctrl+Shift+PageDown` | Sposta Tab a Sx / Dx |
| `Alt+1..9` | Seleziona provider/modello/risultato history |
| `1..9` (senza Alt) | Seleziona da una lista interattiva gia' aperta (es. dopo `/connect` o `/history`) |

---

## 8. Preferenze

`Edit > Preferences` apre la finestra con 7 tab:

### General
- Titolo iniziale e dinamico
- Login shell, comando personalizzato
- Posizione scrollbar, scrollback (0=illimitato)
- Scroll on output/keystroke
- Conferma chiusura, auto-copy selezione, unsafe paste warning
- File manager

### Appearance
- Font, dimensione, bold
- Colori: foreground, background, cursore, highlight testo e sfondo
- Colori titoli tab
- Forma e blink del cursore
- Trasparenza

### Colors
- Palette 16 colori ANSI (black, red, green, yellow, blue, magenta, cyan, white + bright)
- Griglia 4x4 con color picker
- Preset: Dark (default), Light, Solarized Dark, Solarized Light, Monokai,
  Gruvbox Dark, Nord
- Load Preset, Save As, Reset to Default

### Compatibility
- Backspace: ASCII DEL, Control-H, Escape sequence, Auto
- Delete: Escape sequence, ASCII DEL, Control-H, Auto
- Encoding predefinito: UTF-8, Latin-1, Latin-15, CP1252, etc.

### AI
- API key per OpenAI, Claude, Gemini, DeepSeek
- URL e API key per Ollama e Custom
- Modello predefinito per ogni provider

### Notes
- Directory note (default: `~/`)
- File note predefinito (default: `notes.md`)
- Comando editor (default: `nano`)

### About
- Versione, features, crediti

---

## 9. Segnali e Encoding

### 9.1 Inviare un Segnale

`Terminal > Send Signal` permette di inviare un segnale al processo in
esecuzione nel terminale corrente:

| Segnale | Uso Tipico |
|---------|------------|
| **SIGTERM** (15) | Terminazione gentile |
| **SIGKILL** (9) | Terminazione forzata |
| **SIGHUP** (1) | Hangup (chiudi terminale) |
| **SIGINT** (2) | Interrupt (come Ctrl+C) |
| **SIGQUIT** (3) | Quit con core dump |
| **SIGSTOP** (19) | Sospendi processo |
| **SIGCONT** (18) | Riattiva processo |
| **SIGUSR1** (10) | Segnale utente 1 |
| **SIGUSR2** (12) | Segnale utente 2 |

### 9.2 Cambiare Encoding

`Terminal > Set Encoding` per cambiare la codifica del tab corrente.
L'encoding viene mostrato nel titolo del tab: `Terminal [UTF-8]`.

Encoding supportati: UTF-8, ISO-8859-1 (Latin-1), ISO-8859-15 (Latin-9),
UTF-16, CP1252 (Windows-1252), CP850 (DOS Latin-1), ASCII, KOI8-R,
Shift_JIS, EUC-JP, GBK.

---

## 10. Risoluzione Problemi

### TPQ non si avvia

```bash
# Verifica che PyQt6 sia installato
python3 -c "from PyQt6.QtWidgets import QApplication; print('OK')"

# Se manca (Debian/Ubuntu):
sudo apt install python3-pyqt6

# Se mancano le dipendenze Python:
source .venv/bin/activate
uv pip install pyte requests PyQt6
```

### Ollama non rilevato

```bash
# Verifica che Ollama sia in esecuzione
curl http://localhost:11434/api/tags

# Se non risponde, avvia Ollama:
ollama serve
```

### I comandi / non funzionano

- Assicurati di scrivere `/` come **primo carattere** della riga
- Se c'e' uno spazio prima di `/`, viene interpretato come comando shell
- Premi `Esc` per annullare un comando `/` in corso

### Caratteri strani / encoding sbagliato

- Cambia encoding: `Terminal > Set Encoding > UTF-8`
- Verifica che `LANG` sia impostato: `echo $LANG` (dovrebbe essere `en_US.UTF-8` o simile)

### Reset del terminale

Se il terminale mostra caratteri corrotti:
- `Terminal > Reset` o `Ctrl+Shift+R`: resetta il terminale
- `Terminal > Reset and Clear` o `Ctrl+Shift+X`: resetta e pulisce lo schermo

### Configurazione corrotta

Elimina il file di configurazione per ripartire da zero:

```bash
rm -rf ~/.config/tpq/
```

Al prossimo avvio TPQ creera' una configurazione pulita.

### File di configurazione

```
~/.config/tpq/
├── settings.json    # Tutte le impostazioni
└── history.db       # Database SQLite della history
```

---

## Comandi Rapidi di Riferimento

```
/history [termini]     Cerca nella history
/ai                    Entra in chat AI
/ai off                Esci dalla chat AI
/connect [provider]    Connetti a un provider AI
/wnotes [-f] testo     Salva una nota
/onotes [-f]           Apri le note
/help                  Mostra questo aiuto
/clear                 Pulisci lo schermo

Ctrl+R                 Ricerca history interattiva
Ctrl+C                 Interrompi processo
Ctrl+L                 Pulisci schermo
Alt+1..9               Seleziona provider/modello/risultato
1..9                   Seleziona da lista interattiva (senza Alt)
Tab                    Autocompleta comandi TPQ (/hist → /history)
```

---

## Autore e Licenza

**TPQ Terminal** — Andres Zanzani, 2026

Licensed under the **European Union Public Licence (EUPL) 1.2**.

https://github.com/buzzqw/tpq
