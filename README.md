# VÖBB BMP Downloader

Lädt die aktuelle Ausgabe der **Berliner Morgenpost** automatisch als PDF herunter – über den kostenlosen Bibliothekszugang des [VÖBB](https://www.voebb.de) (Verbund der Öffentlichen Bibliotheken Berlins).

Optional wird das PDF direkt per E-Mail an ein oder mehrere Kindle-Geräte gesendet.

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

Öffne `download_bmp.py` und trage deine Zugangsdaten im Konfigurationsblock ein:

```python
VOEBB_BENUTZERNUMMER = "DEINE_BENUTZERNUMMER"
VOEBB_PASSWORT       = "DEIN_PASSWORT"

DOWNLOAD_ORDNER = Path.home() / "Downloads"

# Kindle-Versand (nur relevant mit --kindle)
KINDLE_EMAILS  = ["name@kindle.com"]
ABSENDER_EMAIL = "absender@example.com"
SMTP_HOST      = "smtp.example.com"
SMTP_PORT      = 465                    # 465 = SSL, 587 = STARTTLS
SMTP_USER      = "absender@example.com"
SMTP_PASSWORT  = "DEIN_SMTP_PASSWORT"
```

> **Hinweis Kindle:** Die Absender-E-Mail-Adresse muss in deinem Amazon-Konto unter  
> *Verwalten → Einstellungen → Persönliches Dokument* als vertrauenswürdig eingetragen sein.  
> Bei Gmail ein [App-Passwort](https://myaccount.google.com/apppasswords) verwenden, kein normales Login-Passwort.

### 2. Manuell ausführen

```bash
# Nur herunterladen
python3 download_bmp.py

# Herunterladen + an Kindle senden
python3 download_bmp.py --kindle
```

Das PDF wird unter `~/Downloads/BMP_JJJJ_TTMMJJJJ.pdf` gespeichert.

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

    <!-- Täglich um 06:30 Uhr -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

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

Ist der VÖBB-Login nicht erreichbar (z. B. planmäßige Wartung), schlägt das Skript nach dem Timeout fehl und zeigt eine Fehler-Benachrichtigung. Das PDF für diesen Tag kann dann manuell nachgeladen werden.

Falls der Mac beim geplanten Ausführungszeitpunkt schläft, holt **launchd** den Job automatisch nach, sobald der Mac wieder aufwacht.

---

## Protokoll

Alle Läufe werden in `download.log` im Skript-Ordner protokolliert. Die Datei rotiert automatisch (max. 500 KB × 5 Dateien = 2,5 MB).

---

## Hinweis

Dieses Skript setzt einen gültigen VÖBB-Bibliotheksausweis voraus. Die Berliner Morgenpost ist über den VÖBB-Zugang zu [bib-voebb.genios.de](https://bib-voebb.genios.de) verfügbar. Die Nutzung unterliegt den Nutzungsbedingungen des VÖBB und von Genios.
