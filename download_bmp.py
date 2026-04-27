#!/usr/bin/env python3
"""
VÖBB ePaper Downloader
Lädt tagesaktuelle Zeitungsausgaben via VOEBB-Bibliothekslogin herunter.
Optional: Versand jeder Zeitung als separate E-Mail an Kindle-Geräte.

Setup:
    pip install playwright
    playwright install chromium

Ausführen:
    python3 download_bmp.py
    python3 download_bmp.py --kindle     # + Kindle-Versand
"""

import asyncio
import logging
import logging.handlers
import re
import smtplib
import subprocess
import sys
from datetime import date
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ─── Zeitungen ────────────────────────────────────────────────────────────────

ZEITUNGEN = [
    {
        "name": "Berliner Morgenpost",
        "url":  (
            "https://bib-voebb.genios.de/browse/Alle/Presse/"
            "Presse%20Deutschland/Berliner%20Morgenpost"
        ),
    },
    {
        "name": "Frankfurter Rundschau",
        "url":  (
            "https://bib-voebb.genios.de/browse/Alle/Presse/"
            "Presse%20Deutschland/Frankfurter%20Rundschau"
        ),
    },
]

# ─── Konfiguration ────────────────────────────────────────────────────────────

VOEBB_BENUTZERNUMMER = "DEINE_BENUTZERNUMMER"
VOEBB_PASSWORT       = "DEIN_PASSWORT"

DOWNLOAD_ORDNER = Path.home() / "Downloads"

# Kindle-Versand (nur relevant mit --kindle)
# Jede Zeitung wird als separate E-Mail verschickt.
# Mehrere Empfänger einfach als weitere Einträge in der Liste ergänzen.
KINDLE_EMAILS  = ["name@kindle.com"]
ABSENDER_EMAIL = "absender@example.com"
SMTP_HOST      = "smtp.example.com"
SMTP_PORT      = 465                    # 465 = SSL, 587 = STARTTLS
SMTP_USER      = "absender@example.com"
SMTP_PASSWORT  = "DEIN_SMTP_PASSWORT"  # Bei Gmail: App-Passwort verwenden

# ──────────────────────────────────────────────────────────────────────────────

LOG_DATEI = Path(__file__).parent / "download.log"


# ─── Logging mit automatischer Rotation ───────────────────────────────────────

def setup_logging() -> logging.Logger:
    log = logging.getLogger("epaper")
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.RotatingFileHandler(
        LOG_DATEI, maxBytes=500_000, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    log.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    log.addHandler(ch)
    return log


log = setup_logging()


# ─── macOS-Benachrichtigungen ──────────────────────────────────────────────────

def benachrichtige(titel: str, nachricht: str, fehler: bool = False) -> None:
    """
    Sendet eine macOS-Mitteilungszentrale-Benachrichtigung (nicht-blockierend).

    Damit sie als Hinweis (bleibt stehen) statt als Banner angezeigt wird:
    Systemeinstellungen → Mitteilungen → Script Editor → Darstellungsart → Hinweise
    """
    symbol = "⚠️" if fehler else "📰"
    skript = (
        f'display notification "{nachricht}" '
        f'with title "{symbol} {titel}"'
    )
    try:
        subprocess.Popen(["osascript", "-e", skript])
    except Exception as e:
        log.warning("Benachrichtigung konnte nicht angezeigt werden: %s", e)


# ─── Download einer einzelnen Zeitung ─────────────────────────────────────────

async def lade_zeitung(page, zeitung: dict, heute: date) -> Path:
    """Navigiert zur Browse-Seite der Zeitung und lädt die aktuelle Ausgabe."""
    from playwright.async_api import TimeoutError as PWTimeout

    name = zeitung["name"]
    log.info("--- %s ---", name)

    await page.goto(zeitung["url"], wait_until="networkidle", timeout=30_000)

    # Issue-ID lesen (= aktuellste Ausgabe)
    log.info("Suche aktuelle Ausgabe …")
    try:
        await page.wait_for_selector("[docid]", timeout=10_000)
    except PWTimeout:
        raise RuntimeError(
            f"{name}: Keine Ausgaben gefunden – "
            "Seite nicht erreichbar oder Login fehlgeschlagen."
        )

    docid_raw = await page.get_attribute("[docid]", "docid")
    if not docid_raw:
        raise RuntimeError(f"{name}: Kein docid-Attribut gefunden.")

    # z.B. BMP__2026-104 → BMP__:2026:104
    issue_id = re.sub(r"^([A-Z]+)__(\d{4})-(\d+)$", r"\1__:\2:\3", docid_raw)
    if ":" not in issue_id:
        raise RuntimeError(f"{name}: Unbekanntes docid-Format: {docid_raw!r}")

    issue_date = heute.strftime("%Y-%m-%d")
    log.info("Gefundene Ausgabe: %s (%s)", issue_id, issue_date)

    # ePaper bestellen → Download-URL holen
    response = await page.evaluate(
        """
        async ([issueId, issueDate]) => {
            const resp = await fetch('/api/orderEPaper', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ issueId, issueDate })
            });
            if (!resp.ok) throw new Error('orderEPaper HTTP ' + resp.status);
            return await resp.json();
        }
        """,
        [issue_id, issue_date],
    )

    if "downloadAttachmentModel" not in response:
        raise RuntimeError(f"{name}: Unerwartete API-Antwort: {response}")

    rel_url      = response["downloadAttachmentModel"]["redirectUrl"]
    download_url = f"https://bib-voebb.genios.de{rel_url}"

    # Dateinamen aus der URL extrahieren und URL-Encoding auflösen
    from urllib.parse import unquote
    datei_name = unquote(rel_url.split("filename=")[-1].split("&")[0])
    datei_name = datei_name.split("/")[-1]          # nur letztes Segment
    ziel_pfad  = DOWNLOAD_ORDNER / datei_name

    log.info("Lade PDF herunter …")
    async with page.expect_download(timeout=60_000) as dl_info:
        await page.evaluate(
            """url => {
                const a = document.createElement('a');
                a.href = url;
                a.download = '';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }""",
            download_url,
        )
    download = await dl_info.value

    failure = await download.failure()
    if failure:
        raise RuntimeError(f"{name}: Download fehlgeschlagen: {failure}")

    await download.save_as(ziel_pfad)
    groesse_mb = ziel_pfad.stat().st_size / 1_048_576
    log.info("Gespeichert: %s (%.1f MB)", ziel_pfad, groesse_mb)
    return ziel_pfad


# ─── Haupt-Download (Login + alle Zeitungen) ──────────────────────────────────

async def download_alle() -> list[tuple[dict, Path]]:
    """Loggt einmal ein und lädt alle konfigurierten Zeitungen herunter."""
    from playwright.async_api import async_playwright

    heute = date.today()
    log.info("=== ePaper-Download gestartet für %s ===", heute.strftime("%d.%m.%Y"))

    ergebnisse: list[tuple[dict, Path]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page    = await context.new_page()

        # Einmalig einloggen über erste Zeitung
        erste_url = ZEITUNGEN[0]["url"]
        await page.goto(erste_url, wait_until="networkidle", timeout=30_000)

        if "voebb.de" in page.url:
            log.info("Logge bei VOEBB ein …")
            # Warten bis das Formular wirklich im DOM ist, dann befüllen
            await page.wait_for_selector('input[name="L#AUSW"]', timeout=10_000)
            await page.fill('input[name="L#AUSW"]', VOEBB_BENUTZERNUMMER)
            await page.fill('input[name="LPASSW"]', VOEBB_PASSWORT)
            await page.click('input[name="LLOGIN"]')
            await page.wait_for_load_state("networkidle", timeout=15_000)

            # Consent-Seite (URL bleibt logincheck – Button prüfen)
            consent_btn = page.locator('input[name="CLOGIN"]')
            if await consent_btn.count() > 0:
                log.info("Akzeptiere Datenschutz-Zustimmung …")
                await consent_btn.click()
                await page.wait_for_load_state("networkidle", timeout=15_000)

            if "genios.de" not in page.url:
                raise RuntimeError(
                    f"Login fehlgeschlagen – Seite ist {page.url}"
                )

        # Alle Zeitungen in derselben Session laden
        for zeitung in ZEITUNGEN:
            try:
                pfad = await lade_zeitung(page, zeitung, heute)
                ergebnisse.append((zeitung, pfad))
            except Exception as e:
                log.error("%s: Fehler beim Download: %s", zeitung["name"], e)
                benachrichtige(
                    f"Download fehlgeschlagen",
                    f"{zeitung['name']}: {str(e)[:100]}",
                    fehler=True,
                )

        await browser.close()

    log.info("=== %d/%d Zeitungen erfolgreich geladen ===",
             len(ergebnisse), len(ZEITUNGEN))
    return ergebnisse


# ─── Kindle-Versand ───────────────────────────────────────────────────────────

def sende_an_kindle(zeitung: dict, pdf_pfad: Path) -> None:
    """Sendet eine Zeitung als separate E-Mail an alle Kindle-Adressen."""
    if not all([KINDLE_EMAILS, ABSENDER_EMAIL, SMTP_HOST, SMTP_USER, SMTP_PASSWORT]):
        log.warning("Kindle-Versand: Konfiguration unvollständig.")
        return

    name = zeitung["name"]
    log.info("Sende %s an Kindle (%s) …", name, ", ".join(KINDLE_EMAILS))

    msg            = MIMEMultipart()
    msg["From"]    = ABSENDER_EMAIL
    msg["To"]      = ", ".join(KINDLE_EMAILS)
    msg["Subject"] = name
    msg.attach(MIMEText(f"{name} ePaper", "plain"))

    with open(pdf_pfad, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{pdf_pfad.name}"',
    )
    msg.attach(part)

    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(SMTP_USER, SMTP_PASSWORT)
            smtp.sendmail(ABSENDER_EMAIL, KINDLE_EMAILS, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORT)
            smtp.sendmail(ABSENDER_EMAIL, KINDLE_EMAILS, msg.as_string())

    log.info("%s: E-Mail an Kindle gesendet.", name)


# ─── Einstiegspunkt ───────────────────────────────────────────────────────────

def main() -> None:
    kindle = "--kindle" in sys.argv

    ergebnisse = asyncio.run(download_alle())

    if not ergebnisse:
        log.error("Keine Zeitung erfolgreich geladen.")
        sys.exit(1)

    if kindle:
        fehler = False
        for zeitung, pdf in ergebnisse:
            try:
                sende_an_kindle(zeitung, pdf)
            except Exception as e:
                log.error("%s: Kindle-Versand fehlgeschlagen: %s", zeitung["name"], e)
                benachrichtige(
                    "Kindle-Versand fehlgeschlagen",
                    f"{zeitung['name']}: {str(e)[:100]}",
                    fehler=True,
                )
                fehler = True

        if not fehler:
            namen = " & ".join(z["name"] for z, _ in ergebnisse)
            benachrichtige(
                "ePaper",
                f"{namen}\nGeladen & an Kindle gesendet ✓",
            )
    else:
        namen = " & ".join(z["name"] for z, _ in ergebnisse)
        benachrichtige("ePaper", f"{namen}\nGeladen ✓")

    log.info("=== Fertig ===")


if __name__ == "__main__":
    main()
