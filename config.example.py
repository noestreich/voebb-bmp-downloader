# Vorlage für die lokale Konfiguration.
# Kopieren: cp config.example.py config.py
# Dann config.py mit deinen echten Zugangsdaten befüllen.
# config.py wird NICHT auf GitHub hochgeladen.

VOEBB_BENUTZERNUMMER = "DEINE_BENUTZERNUMMER"
VOEBB_PASSWORT       = "DEIN_PASSWORT"

DOWNLOAD_ORDNER      = "~/Downloads"

KINDLE_EMAILS        = ["name@kindle.com"]       # mehrere Adressen möglich
ABSENDER_EMAIL       = "absender@example.com"    # bei Amazon als vertrauenswürdig eingetragen
SMTP_HOST            = "smtp.example.com"        # z.B. "smtp.gmail.com"
SMTP_PORT            = 465                       # 465 = SSL, 587 = STARTTLS
SMTP_USER            = "absender@example.com"
SMTP_PASSWORT        = "DEIN_SMTP_PASSWORT"     # bei Gmail: App-Passwort
