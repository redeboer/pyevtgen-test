# cspell:ignore autouse
from __future__ import annotations

import pytest

from pyevtgen import Generator


@pytest.fixture(scope="session")
def generator() -> Generator:
    return Generator(seed=0)


@pytest.fixture(autouse=True)
def _add_generator_to_doctests(doctest_namespace: dict, generator: Generator) -> None:
    doctest_namespace["generator"] = generator
