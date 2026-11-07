# cspell:ignore hrefs
# /// script
# requires-python = ">=3.12"
# dependencies = ["packaging"]
# ///
"""Create a PEP 503 package index from new distributions and the published index.

GitHub Pages replaces the whole site on each deployment. Recent versions are
therefore copied over from the published index, so that downstream lock files keep
working after a new build.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import shutil
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING

from packaging.utils import parse_sdist_filename, parse_wheel_filename

if TYPE_CHECKING:
    from packaging.version import Version

PACKAGE = "pyevtgen"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path, help="Directory with new distributions")
    parser.add_argument("site", type=Path, help="Output directory of the site")
    parser.add_argument("url", help="Base URL of the published site")
    parser.add_argument("--keep", default=5, type=int, help="Versions to keep")
    args = parser.parse_args()

    output_dir = args.site / "simple" / PACKAGE
    output_dir.mkdir(parents=True)
    new_files = sorted(p for p in args.dist.iterdir() if is_distribution(p.name))
    for path in new_files:
        shutil.copy(path, output_dir)
    new_versions = {get_version(p.name) for p in new_files}
    url = f"{args.url.rstrip('/')}/simple/{PACKAGE}/"
    published = fetch_filenames(url)
    old_versions = {get_version(name) for name in published} - new_versions
    n_old = max(args.keep - len(new_versions), 0)
    kept_versions = set(sorted(old_versions, reverse=True)[:n_old])
    for name in published:
        if get_version(name) in kept_versions:
            urllib.request.urlretrieve(  # ruff: ignore[suspicious-url-open-usage]
                url + urllib.parse.quote(name), output_dir / name
            )
    write_index(output_dir)
    (args.site / "simple" / "index.html").write_text(
        f'<!DOCTYPE html><a href="{PACKAGE}/">{PACKAGE}</a>\n'
    )


def is_distribution(filename: str) -> bool:
    return filename.endswith((".whl", ".tar.gz"))


def get_version(filename: str) -> Version:
    if filename.endswith(".whl"):
        return parse_wheel_filename(filename)[1]
    return parse_sdist_filename(filename)[1]


def fetch_filenames(url: str) -> list[str]:
    try:
        with urllib.request.urlopen(url) as response:  # ruff: ignore[suspicious-url-open-usage]
            content = response.read().decode()
    except urllib.error.HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:  # first deployment
            return []
        raise
    hrefs = re.findall(r'href="([^"#]+)', content)
    names = [urllib.parse.unquote(href) for href in hrefs]
    return [name for name in names if is_distribution(name)]


def write_index(directory: Path) -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    requires_python = html.escape(pyproject["project"]["requires-python"])
    lines = ["<!DOCTYPE html>"]
    for path in sorted(directory.iterdir()):
        if not is_distribution(path.name):
            continue
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        href = f"{urllib.parse.quote(path.name)}#sha256={sha256}"
        lines.append(
            f'<a href="{href}" data-requires-python="{requires_python}">'
            f"{html.escape(path.name)}</a><br>"
        )
    (directory / "index.html").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
