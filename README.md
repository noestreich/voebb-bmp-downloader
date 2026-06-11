# VÖBB ePaper Downloader

Lädt tagesaktuelle Zeitungsausgaben (Berliner Morgenpost, Frankfurter Rundschau) automatisch als PDF herunter – über den kostenlosen Bibliothekszugang des [VÖBB](https://www.voebb.de) (Verbund der Öffentlichen Bibliotheken Berlins).

Optional werden die PDFs direkt per E-Mail an ein oder mehrere Kindle-Geräte gesendet (eine E-Mail pro Zeitung).

---

## Voraussetzungen

- macOS (getestet auf macOS 14+)
- Python 3.11+
- Ein aktiver VÖBB-Bibliotheksausweis
- Playwright (headless Chromium)

```bash
pip install playwright
playwright install chromium
```

---

## Einrichtung

### 1. Konfiguration

Die Zugangsdaten werden in einer lokalen Datei `config.py` gespeichert, die **nicht** auf GitHub hochgeladen wird.

```bash
cp config.example.py config.py
```

Dann `config.py` öffnen und mit deinen echten Zugangsdaten befüllen:

```python
VOEBB_BENUTZERNUMMER = "DEINE_BENUTZERNUMMER"
VOEBB_PASSWORT       = "DEIN_PASSWORT"

DOWNLOAD_ORDNER      = "~/Downloads"

KINDLE_EMAILS        = ["name@kindle.com"]
ABSENDER_EMAIL       = "absender@example.com"
SMTP_HOST            = "smtp.example.com"
SMTP_PORT            = 465
SMTP_USER            = "absender@example.com"
SMTP_PASSWORT        = "DEIN_SMTP_PASSWORT"
```

> **Wichtig:** `config.py` steht in `.gitignore` und wird nie ins Repository hochgeladen.  
> Nur `config.example.py` (mit Platzhaltern) ist auf GitHub sichtbar.

> **Hinweis Kindle:** Die Absender-E-Mail-Adresse muss in deinem Amazon-Konto unter  
> *Verwalten → Einstellungen → Persönliches Dokument* als vertrauenswürdig eingetragen sein.  
> Bei Gmail ein [App-Passwort](https://myaccount.google.com/apppasswords) verwenden.

### 2. Zeitungen konfigurieren

In `download_bmp.py` kann die Liste der Zeitungen beliebig erweitert werden:

```python
ZEITUNGEN = [
    {
        "name": "Berliner Morgenpost",
        "url":  "https://bib-voebb.genios.de/browse/Alle/Presse/Presse%20Deutschland/Berliner%20Morgenpost",
    },
    {
        "name": "Frankfurter Rundschau",
        "url":  "https://bib-voebb.genios.de/browse/Alle/Presse/Presse%20Deutschland/Frankfurter%20Rundschau",
    },
]
```

### 3. Manuell ausführen

```bash
# Nur herunterladen
python3 download_bmp.py

# Herunterladen + an Kindle senden
python3 download_bmp.py --kindle
```

Die PDFs werden unter `~/Downloads/` gespeichert (`BMP_JJJJ_TTMMJJJJ.pdf` etc.).

---

## Automatisierung (täglich, macOS launchd)

### launchd-Plist erstellen

Datei `~/Library/LaunchAgents/de.bmp-downloader.plist` anlegen:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>de.bmp-downloader</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/DEINNAME/bmp-downloader/download_bmp.py</string>
        <string>--kindle</string>
    </array>

    <!-- Täglich 06:30, danach stündliche Wiederholungsversuche bis 12:30.
         Das Skript beendet sich sofort, wenn alle Zeitungen für den Tag
         bereits erfolgreich geladen wurden (status.json). -->
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>11</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Hour</key><integer>12</integer><key>Minute</key><integer>30</integer></dict>
    </array>

    <key>StandardOutPath</key>
    <string>/Users/DEINNAME/bmp-downloader/download.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/DEINNAME/bmp-downloader/download.log</string>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

### Agent aktivieren

```bash
launchctl load ~/Library/LaunchAgents/de.bmp-downloader.plist
```

### Agent deaktivieren

```bash
launchctl unload ~/Library/LaunchAgents/de.bmp-downloader.plist
```

---

## macOS-Benachrichtigungen

Das Skript sendet nach jedem Lauf eine Mitteilungszentrale-Benachrichtigung (Erfolg oder Fehler).

Damit die Benachrichtigung **stehen bleibt** (statt als Banner zu verschwinden):

> Systemeinstellungen → Mitteilungen → **Script Editor** → Darstellungsart → **Hinweise**

---

## Verhalten bei Wartung / Nichtverfügbarkeit

Ist der VÖBB-Login nicht erreichbar (z. B. planmäßige Wartung), schlägt der Lauf fehl und zeigt eine Fehler-Benachrichtigung. **launchd startet das Skript danach stündlich neu** (07:30–12:30, siehe Plist oben), bis alle Zeitungen geladen sind.

Dafür merkt sich das Skript in `status.json`, welche Zeitungen am aktuellen Tag bereits vollständig erledigt wurden (Download + ggf. Kindle-Versand):

- Ein Wiederholungslauf lädt **nur die noch fehlenden** Zeitungen nach – es gibt keine doppelten Downloads oder Kindle-Mails.
- Ist bereits alles erledigt, beendet sich das Skript sofort und ohne Benachrichtigung.
- Am nächsten Tag wird der Status automatisch zurückgesetzt.

Falls der Mac beim geplanten Ausführungszeitpunkt schläft, holt **launchd** den Job automatisch nach, sobald der Mac wieder aufwacht.

---

## Protokoll

Alle Läufe werden in `download.log` im Skript-Ordner protokolliert. Die Datei rotiert automatisch (max. 500 KB × 5 Dateien = 2,5 MB).

---

## Hinweis

Dieses Skript setzt einen gültigen VÖBB-Bibliotheksausweis voraus. Die Nutzung unterliegt den Nutzungsbedingungen des VÖBB und von Genios.
