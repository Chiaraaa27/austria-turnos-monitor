"""Read-only appointment availability checker. Never books appointments."""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL = 'https://appointment.bmeia.gv.at/?Office=buenos-aires'
OUT = Path('diagnostics')
OUT.mkdir(exist_ok=True)


def save(page, name):
    page.screenshot(path=str(OUT / f'{name}.png'), full_page=True)
    (OUT / f'{name}.txt').write_text(page.locator('body').inner_text(timeout=15000), encoding='utf-8')


def choose_option(page, pattern):
    """Select a matching visible option in a native select; fail closed otherwise."""
    for select in page.locator('select').all():
        if not select.is_visible():
            continue
        options = select.locator('option').all()
        matches = [(o.get_attribute('value'), o.inner_text().strip()) for o in options
                   if re.search(pattern, o.inner_text().strip(), re.I)]
        if len(matches) == 1:
            value, label = matches[0]
            if value is None:
                continue
            select.select_option(value=value)
            print(f'Selected option: {label}')
            return True
    return False


def next_button(page):
    # Only click the known navigation button, never confirmation or booking buttons.
    candidates = page.get_by_role('button', name=re.compile(r'^(Continuar|Next|Weiter)$', re.I))
    if candidates.count() == 1:
        candidates.click()
        return
    candidates = page.get_by_text(re.compile(r'^(Continuar|Next|Weiter)$', re.I), exact=True)
    if candidates.count() == 1:
        candidates.click()
        return
    raise RuntimeError('Cannot identify unique Continue button')


def alert(message):
    topic = os.environ.get('NTFY_TOPIC', '').strip()
    if not topic:
        raise RuntimeError('NTFY_TOPIC GitHub secret is missing')
    response = requests.post(f'https://ntfy.sh/{topic}', data=message.encode('utf-8'),
                             headers={'Title': 'Austria Working Holiday: revisar turnos',
                                      'Priority': 'high', 'Click': URL, 'Tags': 'calendar'}, timeout=20)
    response.raise_for_status()


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(locale='es-AR', timezone_id='America/Argentina/Buenos_Aires')
        try:
            page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_timeout(1200)
            save(page, '01-start')
            if not choose_option(page, r'Working\s*Holiday\s*Programm'):
                raise RuntimeError('Working Holiday category not found in native selects')
            next_button(page)
            page.wait_for_load_state('domcontentloaded', timeout=20000)
            page.wait_for_timeout(800)
            save(page, '02-people')
            if not choose_option(page, r'^\s*1\s*(Persona|Person|Personas|Person\(s\))?\s*$'):
                raise RuntimeError('1-person option not found in native selects')
            next_button(page)
            page.wait_for_load_state('domcontentloaded', timeout=20000)
            page.wait_for_timeout(1200)
            save(page, '03-availability')
            text = page.locator('body').inner_text()
            if not re.search(r'Working\s*Holiday\s*Programm', text, re.I) or not re.search(r'1\s*Persona', text, re.I):
                raise RuntimeError('Cannot verify category and party size on results page')
            no_slots = bool(re.search(r'Actualmente no hay fechas disponibles|no appointments available|keine Termine verfügbar', text, re.I))
            # A real slot must have a visible interactive time or date option; text changes alone are not enough.
            slot_candidates = page.locator('a, button, input[type="radio"], input[type="submit"]')
            slot_labels = []
            for el in slot_candidates.all():
                if not el.is_visible() or not el.is_enabled():
                    continue
                label = (el.inner_text() if el.evaluate('(e) => e.tagName.toLowerCase()') != 'input' else (el.get_attribute('value') or el.get_attribute('aria-label') or '')).strip()
                if re.search(r'\b(?:[01]?\d|2[0-3]):[0-5]\d\b', label):
                    slot_labels.append(label[:100])
            if no_slots and not slot_labels:
                print('NO_AVAILABILITY: no appointments shown on selected week')
            elif slot_labels and not no_slots:
                print('POSSIBLE_AVAILABILITY: ' + repr(slot_labels))
                alert('Se detectaron horarios seleccionables para Working Holiday (1 persona): '
                      + ', '.join(slot_labels[:5]) + '\nEntrá a verificar y reservar: ' + URL)
            else:
                print('UNKNOWN: page does not conclusively indicate availability; see diagnostics')
        except (Exception, PlaywrightTimeout) as exc:
            print(f'CHECK_FAILED: {exc}', file=sys.stderr)
            try:
                save(page, 'error')
            except Exception:
                pass
            raise
        finally:
            browser.close()


if __name__ == '__main__':
    main()
