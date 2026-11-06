"""Read-only checker for Austrian Working Holiday appointments in Buenos Aires.

Does not book appointments or bypass access controls. Fails closed on ambiguity.
"""
import os
import re
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

URL = "https://appointment.bmeia.gv.at/?Office=buenos-aires"
OUT = Path("diagnostics")
OUT.mkdir(exist_ok=True)


def save(page, name):
    try:
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=True, timeout=5000)
    except Exception as exc:
        print(f"Screenshot unavailable: {exc}")
    try:
        (OUT / f"{name}.html").write_text(page.content(), encoding="utf-8")
    except Exception as exc:
        print(f"HTML unavailable: {exc}")
    try:
        (OUT / f"{name}.txt").write_text(page.locator("body").inner_text(timeout=5000), encoding="utf-8")
    except Exception as exc:
        print(f"Page text unavailable: {exc}")


def choose_option(page, pattern):
    matches = []
    for select in page.locator("select").all():
        if not select.is_visible():
            continue
        for option in select.locator("option").all():
            label = option.inner_text().strip()
            value = option.get_attribute("value")
            if value is not None and re.search(pattern, label, re.I):
                matches.append((select, value, label))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one option matching {pattern!r}; found {len(matches)}")
    select, value, label = matches[0]
    select.select_option(value=value)
    print(f"Selected: {label}")


def next_button(page):
    pattern = re.compile(r"^(Continuar|Next|Weiter)$", re.I)
    buttons = page.get_by_role("button", name=pattern)
    if buttons.count() == 1:
        buttons.click(timeout=10000)
        return
    text = page.get_by_text(pattern, exact=True)
    if text.count() == 1:
        text.click(timeout=10000)
        return
    raise RuntimeError("Cannot identify a unique Continue button")


def alert(message):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        raise RuntimeError("NTFY_TOPIC secret missing")
    response = requests.post(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers={"Title": "Austria Working Holiday: revisar turnos", "Priority": "high", "Click": URL},
        timeout=20,
    )
    response.raise_for_status()


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(locale="es-AR", timezone_id="America/Argentina/Buenos_Aires")
        try:
            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                print(f"Navigation failed. Current URL: {page.url}")
                save(page, "navigation_error")
                raise

            save(page, "start")
            choose_option(page, r"Working\s+Holiday\s+Programm")
            next_button(page)
            save(page, "after_category")

            choose_option(page, r"^\s*(1|una?)\s*(Persona\(s\)|Personas?|Person\(s\)|Persons?)?\s*$")
            next_button(page)
            save(page, "results")
