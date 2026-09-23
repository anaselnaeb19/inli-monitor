#!/usr/bin/env python3
"""Surveille les annonces de location sur inli.fr et notifie les nouveautes via Telegram."""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_PATH = Path(__file__).parent / "state.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

BASE_URL = "https://www.inli.fr"

# Departements surveilles : code -> (nom affiche, slug utilise dans l'URL inli.fr)
DEPARTMENTS = {
    "75": ("Paris", "paris-departement_d:75"),
    "77": ("Seine-et-Marne", "seine-et-marne-departement_d:77"),
    "78": ("Yvelines", "yvelines-departement_d:78"),
    "91": ("Essonne", "essonne-departement_d:91"),
    "92": ("Hauts-de-Seine", "hauts-de-seine-departement_d:92"),
    "93": ("Seine-Saint-Denis", "seine-saint-denis-departement_d:93"),
    "94": ("Val-de-Marne", "val-de-marne-departement_d:94"),
    "95": ("Val-d'Oise", "val-d-oise-departement_d:95"),
}

MAX_PAGES_PER_DEPARTMENT = 15
REQUEST_TIMEOUT = 20
REQUEST_DELAY_SECONDS = 1.5


def fetch_page(url: str) -> str | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        print(f"  [erreur] impossible de recuperer {url}: {exc}", file=sys.stderr)
        return None


def parse_listings(html: str) -> dict[str, dict]:
    """Retourne un dict {ref: {url, price, rooms, surface, city}} pour une page."""
    soup = BeautifulSoup(html, "html.parser")
    listings = {}

    for card in soup.select("div.featured-item"):
        link = card.find("a", href=True)
        if not link or not link["href"].startswith("/location-"):
            continue

        href = link["href"]
        ref = href.rstrip("/").rsplit("/", 1)[-1]

        price_el = card.select_one(".featured-price .demi-condensed")
        price = price_el.get_text(strip=True) if price_el else "?"

        details_el = card.select_one(".featured-details span")
        rooms, surface, city = "?", "?", "?"
        if details_el:
            raw = details_el.get_text("\n", strip=True)
            parts = [p.strip() for p in raw.split("\n") if p.strip()]
            if parts:
                city = parts[-1]
            if parts and "·" in parts[0]:
                left, _, right = parts[0].partition("·")
                rooms = left.strip()
                surface = right.strip()

        listings[ref] = {
            "url": BASE_URL + href,
            "price": price,
            "rooms": rooms,
            "surface": surface,
            "city": city,
        }

    return listings


def fetch_all_listings(slug: str) -> dict[str, dict]:
    """Parcourt les pages successives d'un departement jusqu'a epuisement."""
    all_listings: dict[str, dict] = {}
    for page in range(1, MAX_PAGES_PER_DEPARTMENT + 1):
        url = f"{BASE_URL}/locations/offres/{slug}"
        if page > 1:
            url += f"?page={page}"

        html = fetch_page(url)
        if html is None:
            break

        page_listings = parse_listings(html)
        new_refs = set(page_listings) - set(all_listings)
        all_listings.update(page_listings)

        if not new_refs:
            break

        time.sleep(REQUEST_DELAY_SECONDS)

    return all_listings


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def send_telegram_message(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("  [avertissement] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID manquant, message non envoye:")
        print(text)
        return

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=REQUEST_TIMEOUT,
    )
    if not resp.ok:
        print(f"  [erreur] envoi Telegram echoue: {resp.status_code} {resp.text}", file=sys.stderr)


def format_listing_message(dept_name: str, ref: str, info: dict) -> str:
    return (
        f"🏠 <b>Nouvelle annonce - {dept_name}</b>\n"
        f"{info['city']} · {info['rooms']} · {info['surface']}\n"
        f"💶 {info['price']}\n"
        f"{info['url']}"
    )


def main() -> None:
    state = load_state()
    is_first_run = not state
    new_state: dict = {}
    total_new = 0

    for code, (dept_name, slug) in DEPARTMENTS.items():
        print(f"Verification {dept_name} ({code})...")
        current = fetch_all_listings(slug)
        previous_refs = set(state.get(code, {}).keys())
        current_refs = set(current.keys())
        new_refs = current_refs - previous_refs

        print(f"  {len(current_refs)} annonce(s) en ligne, {len(new_refs)} nouvelle(s)")

        if not is_first_run:
            for ref in sorted(new_refs):
                send_telegram_message(format_listing_message(dept_name, ref, current[ref]))
                total_new += 1
                time.sleep(0.5)

        new_state[code] = current
        time.sleep(REQUEST_DELAY_SECONDS)

    if is_first_run:
        print("Premiere execution : etat initial enregistre, aucune notification envoyee.")
    else:
        print(f"Total nouvelles annonces notifiees : {total_new}")

    save_state(new_state)


if __name__ == "__main__":
    main()
