# 📂 Path Analyzer v3.0 — GUI Edition

> Applicazione desktop Windows per analizzare la struttura di directory locali e di rete, con analisi completa della lunghezza dei percorsi e generazione di report Markdown.

---

## 📋 Indice

- [Download](https://github.com/887eb56b-b0f8-4dc1-9188-66f2685b4a0c)
- [Screenshot](#-screenshot)
- [Funzionalità](#-funzionalità)
- [Requisiti](#-requisiti)
- [Installazione Rapida](#-installazione-rapida)
- [Creare l'Eseguibile (.exe)](#-creare-leseguibile-exe)
- [Struttura del Progetto](#-struttura-del-progetto)
- [Guida all'Uso](#-guida-alluso)
- [Parametri e Opzioni](#-parametri-e-opzioni)
- [Report Generato](#-report-generato)
- [Troubleshooting](#-troubleshooting)
- [Note Tecniche](#-note-tecniche)

---

## 🖼️ Screenshot

L'applicazione si presenta con un'interfaccia moderna in dark mode:

```
╔══════════════════════════════════════════════════════════════════╗
║  📂 Path Analyzer v3.0                                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Percorso: [ C:\Users\Luigi\Documents          ] [📁 Sfoglia]  ║
║                                                                  ║
║  Soglia Path: [260]  Profondità: [-1]  Top file: [15]           ║
║  ☑ Mostra file nascosti  Escludi: [.git, node_modules, ...]    ║
║                                                                  ║
║  [🔍 Avvia Scansione] [⏹ Annulla] [💾 Esporta] [📂 Apri]      ║
║  ████████████████████████████████████████████████ 100%           ║
║  ✅ Completata in 2.34s — 156 cartelle, 1,247 file, 45.2 MB   ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │ 🌳 Struttura │ 📊 Statistiche │ 📐 Analisi Path │ 📋 Log  │ ║
║  ├─────────────────────────────────────────────────────────────┤ ║
║  │ Documents                                                   │ ║
║  │ ├── Progetti                                                │ ║
║  │ │   ├── WebApp                                              │ ║
║  │ │   │   ├── src                                             │ ║
║  │ │   │   │   ├── index.js                                   │ ║
║  │ │   │   │   └── styles.css                                 │ ║
║  │ │   │   └── package.json                                   │ ║
║  │ │   └── MobileApp                                          │ ║
║  │ └── Documenti                                               │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## ✨ Funzionalità

### Scansione
- Analisi di percorsi **locali** (`C:\`, `D:\`) e **di rete UNC** (`\\server\share`)
- Scansione ricorsiva con profondità configurabile
- Esclusione di cartelle specifiche (`.git`, `node_modules`, ecc.)
- Opzione per nascondere/mostrare file nascosti
- **Annullamento** della scansione in corso

### Analisi Path
- Calcolo lunghezza in caratteri di ogni percorso (file e cartelle)
- **Soglia personalizzabile** (default 260 = `MAX_PATH` di Windows)
- Segnalazione visiva dei percorsi che superano la soglia
- Distribuzione statistica delle lunghezze
- Top 10 percorsi più lunghi
- Media e mediana delle lunghezze

### Struttura ad Albero
- **Vista pulita** in stile `tree` classico (come nel tuo esempio)
- **Vista dettagliata** con icone, dimensioni e lunghezza path
- Connettori Unicode (`├──`, `└──`, `│`)

### Report Markdown
- Export completo in formato `.md`
- Tabelle formattate per GitHub/VS Code/qualsiasi viewer Markdown
- Sezioni: Info, Riepilogo, Analisi Path, Estensioni, File grandi, Albero, Indice

### Interfaccia
- GUI moderna con **CustomTkinter** (dark mode)
- 4 tab: Struttura, Statistiche, Analisi Path, Log
- Barra di progresso e stato in tempo reale
- Sfoglia cartelle con dialog nativo di Windows

---

## 📋 Requisiti

### Per eseguire dal sorgente Python
- **Python 3.8+** (consigliato 3.11+)
- **customtkinter** >= 5.2.0

### Per creare l'eseguibile
- Tutto quanto sopra, più:
- **PyInstaller** >= 6.0

### Per usare l'eseguibile compilato
- **Windows 10/11** (64-bit)
- Nessun altro requisito! L'exe è completamente standalone.

---

## 🚀 Installazione Rapida

### 1. Scarica i file del progetto

Metti tutti i file nella stessa cartella:

```
PathAnalyzerApp/
├── path_analyzer_gui.py      ← Applicazione principale
├── requirements.txt          ← Dipendenze Python
├── PathAnalyzer.spec         ← Configurazione PyInstaller
├── build_exe.bat             ← Script automatico di build
└── README.md                 ← Questa documentazione
```

### 2. Installa le dipendenze

Apri un terminale nella cartella del progetto:

```bash
pip install -r requirements.txt
```

### 3. Avvia l'applicazione

```bash
python path_analyzer_gui.py
```

---

## 📦 Creare l'Eseguibile (.exe)

### Metodo 1: Script Automatico (Consigliato)

**Fai doppio click su `build_exe.bat`**

Lo script automaticamente:
1. ✅ Verifica Python
2. ✅ Installa le dipendenze
3. ✅ Compila l'eseguibile con i temi CustomTkinter inclusi
4. ✅ Pulisce i file temporanei
5. ✅ Apre la cartella con l'exe

### Metodo 2: Manuale via Terminale

```bash
# Installa dipendenze
pip install -r requirements.txt

# Build con spec file (CONSIGLIATO - gestisce customtkinter)
pyinstaller PathAnalyzer.spec --clean --noconfirm

# L'exe sarà in: dist/PathAnalyzer.exe
```

### Metodo 3: Manuale senza spec file

```bash
# Trova il percorso di customtkinter
python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"
# Output esempio: C:\Python311\Lib\site-packages\customtkinter

# Build (sostituisci il percorso)
pyinstaller --onefile --noconsole --name PathAnalyzer ^
  --add-data "C:\Python311\Lib\site-packages\customtkinter;customtkinter" ^
  path_analyzer_gui.py
```

### Risultato del Build

```
PathAnalyzerApp/
├── dist/
│   └── PathAnalyzer.exe    ← IL TUO ESEGUIBILE (~20-25 MB)
├── build/                   ← puoi cancellare
└── ...
```

### Distribuzione

Il file `PathAnalyzer.exe` è **completamente standalone**:
- ✅ NON richiede Python installato
- ✅ NON richiede librerie aggiuntive
- ✅ Funziona su qualsiasi Windows 10/11 (64-bit)
- ✅ Copia singolo file, zero configurazione

---

## 📁 Struttura del Progetto

```
PathAnalyzerApp/
├── path_analyzer_gui.py      # Sorgente principale (tutto in un file)
│                              #   ├── Data Classes (FileInfo, DirInfo, Stats)
│                              #   ├── Utility (format_size, is_hidden, ecc.)
│                              #   ├── PathAnalyzer Engine (scanner + report)
│                              #   └── PathAnalyzerApp GUI (CustomTkinter)
├── requirements.txt           # Dipendenze: customtkinter, pyinstaller
├── PathAnalyzer.spec          # Config PyInstaller (include assets CTk)
├── build_exe.bat              # Script automatico di compilazione
└── README.md                  # Documentazione (questo file)
```

### Architettura del Codice

```
path_analyzer_gui.py
│
├── DATA CLASSES
│   ├── FileInfo          → Info singolo file (nome, path, size, ext, path_length)
│   ├── DirInfo           → Info directory (files, subdirs, totali)
│   ├── PathLengthStats   → Statistiche lunghezza path
│   └── ScanStats         → Statistiche globali scansione
│
├── UTILITY FUNCTIONS
│   ├── format_size()     → Formattazione dimensioni (B/KB/MB/GB)
│   ├── format_date()     → Formattazione date
│   ├── is_hidden()       → Rilevamento file nascosti (Windows API)
│   ├── get_file_icon()   → Icone per estensione
│   └── safe_stat()       → os.stat() con error handling
│
├── PathAnalyzer (ENGINE)
│   ├── scan()            → Scansione ricorsiva (thread-safe)
│   ├── cancel()          → Annullamento scansione
│   ├── build_clean_tree()  → Albero stile `tree`
│   ├── build_detail_tree() → Albero con dettagli
│   └── generate_report()   → Export Markdown completo
│
└── PathAnalyzerApp (GUI)
    ├── __init__()        → Setup finestra + tema
    ├── _build_ui()       → Costruzione interfaccia
    ├── _start_scan()     → Lancio scansione in thread separato
    ├── _on_scan_complete() → Popolamento tab risultati
    └── _export_report()  → Salvataggio report .md
```

---

## 📖 Guida all'Uso

### 1. Seleziona il Percorso

- Digita il percorso manualmente nel campo di testo
- Oppure clicca **📁 Sfoglia** per selezionare la cartella
- Supporta percorsi locali (`C:\Users\...`) e di rete (`\\server\share`)

### 2. Configura le Opzioni

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| **Soglia Path** | Lunghezza massima in caratteri prima di segnalare un warning | `260` |
| **Profondità max** | Livelli massimi di ricorsione (`-1` = illimitata) | `-1` |
| **Top file** | Numero di file più grandi da mostrare | `15` |
| **File nascosti** | Include/escludi file e cartelle nascosti | ✅ Inclusi |
| **Escludi cartelle** | Lista separata da virgola delle cartelle da ignorare | `.git, node_modules, ...` |

### 3. Avvia la Scansione

- Clicca **🔍 Avvia Scansione**
- La barra di progresso si attiva
- Puoi **⏹ Annullare** in qualsiasi momento

### 4. Esplora i Risultati

I risultati sono divisi in 4 tab:

| Tab | Contenuto |
|-----|-----------|
| **🌳 Struttura** | Albero delle directory in stile `tree` |
| **📊 Statistiche** | Riepilogo, distribuzione estensioni, file più grandi |
| **📐 Analisi Path** | Distribuzione lunghezze, path oltre soglia, percorsi più lunghi |
| **📋 Log** | Log delle operazioni con timestamp |

### 5. Esporta il Report

- Clicca **💾 Esporta Report .md**
- Scegli dove salvare il file Markdown
- Clicca **📂 Apri Report** per visualizzarlo

---

## ⚙️ Parametri e Opzioni

### Soglia Lunghezza Path

Il valore di default è **260 caratteri**, che corrisponde al limite classico `MAX_PATH` di Windows.

| Soglia | Caso d'uso |
|--------|------------|
| `260` | Standard Windows — identifica file che non possono essere aperti da programmi legacy |
| `200` | Conservativo — identifica path che potrebbero causare problemi con vecchi software |
| `150` | Restrittivo — per ambienti con limiti più severi |
| `32767` | Nessun limite pratico — per analisi solo statistica |

### Cartelle Escluse di Default

```
.git, node_modules, __pycache__, .vs, .vscode
```

Puoi aggiungere altre cartelle separate da virgola, ad esempio:
```
.git, node_modules, __pycache__, .vs, .vscode, bin, obj, dist, build
```

---

## 📄 Report Generato

Il report `.md` contiene le seguenti sezioni:

### Struttura del Report

```
# 📂 Path Analyzer Report
│
├── ℹ️ Informazioni Percorso         → Dettagli scansione
├── 📊 Riepilogo Generale            → Conteggi e dimensioni
├── 📐 Analisi Lunghezza Percorsi
│   ├── Statistiche Generali         → Media, mediana, estremi
│   ├── Distribuzione                → Istogramma per range
│   ├── Top 10 più Lunghi            → Con stato OK/OLTRE
│   ├── Percorsi Oltre Soglia        → Tabella dettagliata
│   └── Percorsi più Lunghi per Tipo → File e cartella record
├── 🏷️ Distribuzione per Estensione  → Tabella con barre
├── 📏 File più Grandi               → Top N con path length
├── ⚠️ Errori                        → Se presenti
├── 🌳 Struttura Directory
│   ├── Vista Pulita                 → Stile `tree` classico
│   └── Vista Dettagliata            → Con dimensioni e path length
└── 📋 Indice Completo               → Tutti i file per cartella
```

### Esempio Vista Pulita

```
Documents
├── Progetti
│   ├── WebApp
│   │   ├── src
│   │   │   ├── index.js
│   │   │   └── styles.css
│   │   └── package.json
│   └── MobileApp
│       └── App.tsx
└── Archivio
    └── backup_2024.zip
```

---

## 🔧 Troubleshooting

### L'antivirus blocca l'exe

PyInstaller crea exe che alcuni antivirus segnalano come falsi positivi.

**Soluzione:** Aggiungi un'eccezione per `PathAnalyzer.exe` nel tuo antivirus.

### Errore "ModuleNotFoundError: customtkinter"

```bash
pip install customtkinter --upgrade
```

### L'exe si apre e si chiude subito

Probabilmente c'è un errore. Per vedere i messaggi, esegui l'exe dal terminale:

```bash
cd dist
PathAnalyzer.exe
```

### Build fallisce con errore su customtkinter

Assicurati di usare il file `.spec` che include gli assets di CustomTkinter:

```bash
pyinstaller PathAnalyzer.spec --clean --noconfirm
```

### La finestra è troppo piccola / grande

La finestra si ridimensiona liberamente. La dimensione minima è 800x600. Puoi massimizzare con il pulsante standard di Windows.

### Il percorso di rete non funziona

- Assicurati che il percorso UNC sia raggiungibile: `\\server\share\cartella`
- Verifica le autorizzazioni di accesso
- Testa con `dir \\server\share\cartella` nel prompt dei comandi

### Scansione lenta su cartelle molto grandi

Per cartelle con decine di migliaia di file:
- Imposta un **limite di profondità** (es. `-d 5`)
- **Escludi** cartelle pesanti (`node_modules`, `.git`, `bin`, `obj`)
- La scansione è in un thread separato e non blocca l'interfaccia

---

## 📝 Note Tecniche

### Perché CustomTkinter?

- **Aspetto moderno** — dark mode nativa, widget arrotondati
- **Nessuna dipendenza esterna** — basato su Tkinter (incluso in Python)
- **Leggero** — nessun browser embedded (come Electron)
- **Facile da distribuire** — un singolo exe con PyInstaller

### Thread Safety

La scansione avviene in un **thread separato** per non bloccare la GUI.
Il callback `progress_callback` usa `self.after()` per aggiornare la UI dal thread principale (thread-safe con Tkinter).

### Limiti

- L'exe è per **Windows 64-bit** (la stessa architettura del Python usato per il build)
- Il rilevamento dei file nascosti usa l'API Windows (`ctypes.windll`) — su Linux/Mac usa solo il prefisso `.`
- Per cartelle con milioni di file, il report Markdown potrebbe essere molto grande

### Compatibilità

| Windows | Stato |
|---------|-------|
| Windows 11 | ✅ Testato |
| Windows 10 | ✅ Compatibile |
| Windows 8.1 | ⚠️ Non testato |
| Windows 7 | ❌ Non supportato (Python 3.9+ non supporta Win7) |

---

## 📜 Licenza

Progetto sviluppato per uso interno. Puoi modificarlo e redistribuirlo liberamente.

---

*Path Analyzer v3.0 GUI — Sviluppato con Python + CustomTkinter*
