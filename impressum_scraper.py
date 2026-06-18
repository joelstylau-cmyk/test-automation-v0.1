#!/usr/bin/env python3
"""
Impressum-Scraper: Extrahiert den Geschäftsführer von der Unternehmenswebsite
und erstellt eine personalisierte E-Mail.

Usage:
    python impressum_scraper.py info@beispiel.de
    python impressum_scraper.py info@beispiel.de --template vorlage.txt
"""

import argparse
import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.5",
}

IMPRESSUM_PATHS = [
    "/impressum",
    "/impressum.html",
    "/imprint",
    "/legal",
    "/legal-notice",
    "/about/impressum",
    "/de/impressum",
    "/ueber-uns/impressum",
]

GF_PATTERNS = [
    r"Geschäftsführ(?:er|ung|erin)[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    r"Geschäftsleitung[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    r"Managing\s+Director[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    r"CEO[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    r"Vertreten\s+durch[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    r"Vertretungsberechtigt(?:er?)?[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
    r"Inhaber(?:in)?[\s:]*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,3})",
]

DEFAULT_TEMPLATE = """Betreff: Zusammenarbeit mit {firma}

Sehr geehrte/r {anrede} {nachname},

ich hoffe, diese Nachricht erreicht Sie wohlauf.

Mein Name ist [IHR NAME] und ich schreibe Ihnen, weil ich glaube, dass wir
für {firma} einen echten Mehrwert schaffen können.

[HIER IHREN PITCH EINFÜGEN]

Ich würde mich freuen, wenn wir in einem kurzen Gespräch die Möglichkeiten
einer Zusammenarbeit besprechen könnten.

Mit freundlichen Grüßen
[IHR NAME]
"""


def domain_from_email(email: str) -> str:
    parts = email.strip().split("@")
    if len(parts) != 2 or "." not in parts[1]:
        raise ValueError(f"Ungültige E-Mail-Adresse: {email}")
    return parts[1]


def fetch_page(url: str, timeout: int = 15) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
            resp.encoding = resp.apparent_encoding
            return resp.text
    except requests.RequestException:
        pass
    return None


def find_impressum_url(base_url: str) -> str | None:
    html = fetch_page(base_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        text = link.get_text(strip=True).lower()
        if any(kw in text for kw in ["impressum", "imprint", "legal notice"]):
            return urljoin(base_url, href)
        if any(kw in href.lower() for kw in ["impressum", "imprint", "legal-notice"]):
            return urljoin(base_url, href)

    for path in IMPRESSUM_PATHS:
        url = urljoin(base_url, path)
        if fetch_page(url):
            return url

    return None


def extract_geschaeftsfuehrer(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator="\n")

    noise = ["GmbH", "UG", "AG", "KG", "OHG", "Ltd", "Inc", "mbH", "Deutschland",
             "Registergericht", "Amtsgericht", "Handelsregister", "Sitz", "USt"]

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for pattern in GF_PATTERNS:
            match = re.search(pattern, line)
            if match:
                name = match.group(1).strip()
                if not any(n in name for n in noise):
                    return name

    return None


def guess_anrede(vorname: str) -> str:
    female_endings = ["a", "e", "ine", "ina", "ika", "ina"]
    common_male = ["Andre", "Arne", "Malte", "Helge", "Ole", "Uwe", "Jörge", "Nisse"]
    if vorname in common_male:
        return "Herr"
    if any(vorname.endswith(e) for e in female_endings):
        return "Frau"
    return "Herr/Frau"


def personalize_email(name: str, domain: str, template: str) -> str:
    parts = name.split()
    vorname = parts[0]
    nachname = parts[-1]
    anrede = guess_anrede(vorname)
    firma = domain.split(".")[0].capitalize()

    return template.format(
        vorname=vorname,
        nachname=nachname,
        name=name,
        anrede=anrede,
        firma=firma,
        domain=domain,
    )


def run(email: str, template: str | None = None) -> dict:
    domain = domain_from_email(email)
    base_url = f"https://www.{domain}"

    print(f"[1/4] Domain extrahiert: {domain}")
    print(f"[2/4] Suche Impressum auf {base_url} ...")

    impressum_url = find_impressum_url(base_url)
    if not impressum_url:
        base_url = f"https://{domain}"
        impressum_url = find_impressum_url(base_url)

    if not impressum_url:
        print("  ✗ Kein Impressum gefunden.")
        return {"success": False, "error": "Impressum nicht gefunden"}

    print(f"  ✓ Impressum gefunden: {impressum_url}")
    print("[3/4] Extrahiere Geschäftsführer ...")

    html = fetch_page(impressum_url)
    if not html:
        return {"success": False, "error": "Impressum-Seite nicht ladbar"}

    name = extract_geschaeftsfuehrer(html)
    if not name:
        print("  ✗ Kein Geschäftsführer gefunden.")
        return {"success": False, "error": "Geschäftsführer nicht im Impressum gefunden"}

    print(f"  ✓ Geschäftsführer: {name}")
    print("[4/4] Erstelle personalisierte E-Mail ...\n")

    tmpl = template or DEFAULT_TEMPLATE
    email_text = personalize_email(name, domain, tmpl)

    print("=" * 60)
    print(email_text)
    print("=" * 60)

    return {
        "success": True,
        "domain": domain,
        "impressum_url": impressum_url,
        "geschaeftsfuehrer": name,
        "email": email_text,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Geschäftsführer aus Impressum und erstelle personalisierte E-Mail"
    )
    parser.add_argument("email", help="E-Mail-Adresse des Unternehmens (z.B. info@firma.de)")
    parser.add_argument("--template", "-t", help="Pfad zu einer eigenen E-Mail-Vorlage (.txt)")
    args = parser.parse_args()

    template = None
    if args.template:
        with open(args.template) as f:
            template = f.read()

    result = run(args.email, template)
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
