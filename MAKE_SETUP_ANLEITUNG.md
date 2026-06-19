# Make.com Setup-Anleitung: Impressum Scraper

## Übersicht

Diese Automation nimmt E-Mail-Adressen aus einem Google Sheet, findet automatisch
den Geschäftsführer über das Impressum der Website und verschickt eine personalisierte E-Mail.

## Ablauf

```
Google Sheet (neue Zeile) → Website laden → Impressum finden → Geschäftsführer extrahieren → E-Mail senden
```

## Schritt-für-Schritt Setup

### 1. Google Sheet vorbereiten

Erstelle ein Google Sheet mit diesen Spalten:

| email | geschaeftsfuehrer | status |
|---|---|---|
| info@beispiel.de | | |

### 2. Make.com Szenario erstellen

**Option A: Blueprint importieren**
1. Geh zu make.com → Scenarios → Create a new scenario
2. Klick unten rechts auf "..." → Import Blueprint
3. Lade `make_blueprint.json` hoch
4. Ersetze `DEINE_SPREADSHEET_ID` und `DEIN_SHEET_NAME` mit deinen Werten

**Option B: Manuell aufbauen**

#### Modul 1: Google Sheets - Watch Rows
- Trigger: Neue Zeilen beobachten
- Spreadsheet & Sheet auswählen
- Limit: 1

#### Modul 2: HTTP - Make a request (Homepage)
- URL: `https://www.{{replace(split(1.email; "@"; 2); " "; "")}}`
- Method: GET
- Headers: User-Agent setzen

#### Modul 3: Text Parser - Match Pattern (Impressum-Link)
- Pattern: `(?i)href=["']([^"']*(?:impressum|imprint|legal-notice)[^"']*)[\"']`
- Text: Antwort von Modul 2

#### Modul 4: HTTP - Make a request (Impressum-Seite)
- URL: Der gefundene Impressum-Link (ggf. mit Domain ergänzen)
- Method: GET

#### Modul 5: Text Parser - Match Pattern (Geschäftsführer)
- Pattern: `(?:Geschäftsführ(?:er|ung|erin)|Vertreten\s+durch|CEO|Managing\s+Director|Inhaber(?:in)?)\s*:?\s*([A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)`
- Text: Antwort von Modul 4

#### Modul 6: Google Sheets - Update Row
- Schreibe den gefundenen Namen zurück ins Sheet

#### Modul 7: Gmail - Send Email
- An: Die E-Mail aus dem Sheet
- Betreff: `Zusammenarbeit mit {{firma}}`
- Text: Personalisierte Nachricht mit dem Geschäftsführer-Namen

### 3. Scheduling

- Setze das Szenario auf "Immediately" oder ein Intervall (z.B. alle 15 Min)
- Aktiviere das Szenario

## Tipps

- **Error Handling**: Füge nach dem HTTP-Modul einen Error Handler hinzu für Websites die nicht erreichbar sind
- **Rate Limiting**: Setze ein Delay zwischen den Durchläufen (1-2 Sek), damit Websites dich nicht blockieren
- **Testen**: Teste zuerst mit 1-2 bekannten Firmen bevor du es auf viele loslässt
