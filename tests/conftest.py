from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


@pytest.fixture
def valid_dir() -> Path:
    return HERE / "data" / "valid"


@pytest.fixture
def valid_works(valid_dir):
    return [f for f in valid_dir.iterdir() if f.stem.startswith("Work")]


@pytest.fixture
def invalid_works():
    invalid_dir = HERE / "data" / "invalid"
    return [f for f in invalid_dir.iterdir() if f.stem.startswith("Work")]
