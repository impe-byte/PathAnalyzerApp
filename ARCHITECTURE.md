# PathAnalyzer Editor v4.0 — Documentazione Architetturale

## Il Problema Fondamentale

Quando si rinominano file e cartelle in una struttura ad albero, ogni modifica a una cartella
**invalida tutti i path dei suoi discendenti**. Se hai:

```
C:\Progetto\Cartella_Molto_Lunga\sottocartella\file.txt
```

E rinomini `Cartella_Molto_Lunga` in `CML`, il path di `file.txt` cambia da:
```
C:\Progetto\Cartella_Molto_Lunga\sottocartella\file.txt  (VECCHIO - non esiste piu)
C:\Progetto\CML\sottocartella\file.txt                   (NUOVO)
```

Se il sistema aveva gia pianificato operazioni su `file.txt` usando il vecchio path,
queste falliranno. Con 100.000+ file, questo crea un effetto a cascata catastrofico.

---

## La Soluzione: Architettura a 3 Fasi

### Fase 1: SCAN (Sola Lettura)
Scansione completa della struttura. Nessuna modifica al filesystem.
Produce un modello in memoria dell'intero albero.

### Fase 2: PLAN (Calcolo in Memoria)
L'utente configura le regole tramite il wizard. Il sistema calcola TUTTE le modifiche
in memoria, senza toccare il filesystem. Preview completa prima dell'esecuzione.

### Fase 3: EXECUTE (Bottom-Up Atomico)
Le operazioni vengono ordinate ed eseguite in ordine **bottom-up** (dal piu profondo
al meno profondo). Questo garantisce che:
- I file vengono rinominati PRIMA delle cartelle che li contengono
- Quando una cartella viene rinominata, tutti i suoi figli sono gia stati processati
- Nessun path viene invalidato prima del suo utilizzo

```
ORDINE DI ESECUZIONE (depth-first post-order):

Profondita 5:  rinomina file e cartelle al livello piu profondo
Profondita 4:  rinomina file e cartelle un livello sopra
Profondita 3:  ...
Profondita 2:  ...
Profondita 1:  ...
Profondita 0:  rinomina la cartella root (se necessario)
```

---

## Perche Bottom-Up Funziona

```
ESEMPIO CON TOP-DOWN (SBAGLIATO):

1. Rinomina C:\A_Lungo\ -> C:\AL\
   -> Ora C:\A_Lungo\B_Lungo\file.txt NON ESISTE PIU
2. Rinomina C:\A_Lungo\B_Lungo\ -> ERRORE! Path non trovato!

ESEMPIO CON BOTTOM-UP (CORRETTO):

1. Rinomina C:\A_Lungo\B_Lungo\file_lungo.txt -> C:\A_Lungo\B_Lungo\fl.txt  OK
2. Rinomina C:\A_Lungo\B_Lungo\ -> C:\A_Lungo\BL\                           OK
3. Rinomina C:\A_Lungo\ -> C:\AL\                                            OK
   -> Risultato finale: C:\AL\BL\fl.txt                                      OK
```

---

## Struttura del Codice

```
path_analyzer_editor.py          # File singolo, tutto incluso
|
|-- DATA LAYER
|   |-- FileInfo, DirInfo        # Modello dati (come prima)
|   |-- RenameOperation          # Singola operazione: old_path -> new_path + depth
|   |-- RenamePlan               # Piano completo: lista ordinata di operazioni
|   |-- RenameRule               # Regola configurata dall'utente
|
|-- ENGINE
|   |-- PathAnalyzer             # Scanner (invariato dalla v3)
|   |-- RenameEngine             # Motore di rinomina
|   |   |-- plan()               # Calcola tutte le operazioni in memoria
|   |   |-- validate()           # Verifica conflitti, duplicati, limiti
|   |   |-- execute()            # Esegue bottom-up con rollback
|   |   |-- rollback()           # Annulla operazioni eseguite
|   |
|   |-- RuleProcessor            # Applica le regole ai nomi
|       |-- shorten_names()      # Abbrevia nomi lunghi
|       |-- replace_text()       # Trova e sostituisci
|       |-- remove_chars()       # Rimuovi caratteri specifici
|       |-- truncate()           # Tronca a N caratteri
|       |-- smart_abbreviate()   # Abbreviazione intelligente
|
|-- GUI
    |-- PathAnalyzerApp          # Finestra principale (scan + report)
    |-- EditorWizard             # Wizard di modifica a step
        |-- Step 1: Selezione    # Cosa modificare (file/cartelle/entrambi)
        |-- Step 2: Regole       # Configurazione regole
        |-- Step 3: Preview      # Anteprima completa con diff
        |-- Step 4: Conferma     # Warning + esecuzione
        |-- Step 5: Risultato    # Report finale con eventuali errori
```

---

## Regole Disponibili nel Wizard

| Regola | Descrizione | Esempio |
|--------|-------------|---------|
| **Trova e Sostituisci** | Sostituisce testo nei nomi | `Progetto_Vecchio` -> `PV` |
| **Tronca a N caratteri** | Taglia il nome a N chars max | `NomeMoltoLungo.txt` -> `NomeMo.txt` |
| **Rimuovi caratteri** | Rimuove spazi, underscore, ecc. | `file__name` -> `filename` |
| **Abbreviazione smart** | Abbrevia parole comuni | `Documents` -> `Docs`, `Progetto` -> `Prj` |
| **Rimuovi prefisso/suffisso** | Taglia inizio/fine del nome | `backup_file.txt` -> `file.txt` |
| **Comprimi ripetizioni** | Rimuove ripetizioni | `file___name` -> `file_name` |
| **Regex** | Pattern personalizzato | `IMG_\d{8}` -> `img` |

Le regole si applicano in sequenza e si combinano.

---

## Meccanismi di Sicurezza

### Pre-Esecuzione
- **Conflict detection**: verifica che due file non vengano rinominati con lo stesso nome
- **Path length validation**: verifica che il nuovo path sia effettivamente piu corto
- **Permission check**: testa i permessi di scrittura prima di iniziare
- **Dry-run preview**: mostra OGNI modifica prima dell'esecuzione

### Durante l'Esecuzione
- **Operazione atomica per file**: ogni singola rinomina e isolata
- **Log di ogni operazione**: tiene traccia di old -> new per rollback
- **Stop on error**: si ferma al primo errore (configurabile)
- **Continue on error**: salta gli errori e prosegue (configurabile)

### Post-Esecuzione
- **Rollback completo**: puo annullare TUTTE le modifiche (in ordine top-down inverso)
- **Report di esecuzione**: log dettagliato di cosa e stato fatto
- **Verifica finale**: ri-scansiona per confermare i risultati

---

## Gestione di 100.000+ File

### Performance
- La scansione usa `os.scandir()` (molto piu veloce di `os.listdir()`)
- Le operazioni sono calcolate in memoria con strutture dati leggere
- La GUI usa threading per non bloccarsi
- Il progress viene aggiornato ogni N operazioni (non ogni singola)

### Memoria
- Solo i metadati vengono tenuti in memoria (nome, path, size) — non il contenuto
- Per 100.000 file, circa 50-100 MB di RAM
- Le operazioni di rinomina sono stringhe (pochi byte ciascuna)

### Robustezza
- I path di rete (UNC) possono avere latenza: timeout configurabile
- I file in uso da altri processi: skip + log
- Permessi insufficienti: skip + log
- Nomi con caratteri speciali: gestione Unicode completa

---

## Tecnologie

| Componente | Tecnologia | Motivo |
|------------|------------|--------|
| GUI | CustomTkinter | Leggero, nativo Windows, dark mode |
| Filesystem | os.scandir + os.rename | API native, massima performance |
| Threading | threading.Thread | Scansione/esecuzione non bloccanti |
| Report | Markdown (.md) | Universale, leggibile, versionabile |
| Build | PyInstaller | Exe standalone senza dipendenze |
| Undo | Log JSON | Rollback preciso e verificabile |

---

## Build e Distribuzione

Identico alla v3: un singolo `.exe` standalone creato con PyInstaller.
Vedi build_exe.bat e PathAnalyzer.spec nella cartella del progetto.
