# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright==1.55.0"]
# ///
"""Run the exported marimo app in a headless browser and click through it.

Usage: python test_marimo_app.py <site directory> <expected pyevtgen version>
"""

from __future__ import annotations

import functools
import logging
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import Page, sync_playwright

_LOGGER = logging.getLogger(__name__)
TIMEOUT = 300_000  # ms, loading Pyodide and initializing EvtGen is slow


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # ruff: ignore[builtin-argument-shadowing]
        pass


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    site, version = sys.argv[1:3]
    handler = functools.partial(QuietHandler, directory=site)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/explorer/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        errors: list[str] = []
        console: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: console.append(message.text))
        page.goto(url)
        try:
            click_through(page, version)
        except Exception:
            _LOGGER.exception("Page text:\n%s", page.inner_text("body")[-5000:])
            _LOGGER.info("Console:\n%s", "\n".join(console[-60:]))
            raise
        browser.close()
    server.shutdown()
    if errors:
        msg = "Errors in the page:\n" + "\n".join(errors)
        raise RuntimeError(msg)


def click_through(page: Page, version: str) -> None:
    page.get_by_text(f"Running pyevtgen {version}").wait_for(timeout=TIMEOUT)
    page.wait_for_function(
        "document.querySelectorAll('img').length >= 2", timeout=TIMEOUT
    )
    _LOGGER.info("Phase space plots rendered")
    page.get_by_role("button", name="Start EvtGen").click()
    page.get_by_text("Most frequent final states").wait_for(timeout=TIMEOUT)
    page.locator("svg[aria-roledescription=flowchart-v2]").first.wait_for(
        timeout=TIMEOUT
    )
    _LOGGER.info("EvtGen decays rendered")
    n_images = page.locator("img").count()
    page.get_by_role("button", name="Apply and generate").click()
    page.wait_for_function(
        f"document.querySelectorAll('img').length > {n_images}", timeout=TIMEOUT
    )
    _LOGGER.info("Forced decay rendered")


if __name__ == "__main__":
    main()
