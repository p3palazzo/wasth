"""Testes da interface CLI, não das funções chamadas por ela."""

from pathlib import Path

import pytest
import typer

from wasth.cli import WASTHConfig, main, setup_config


# -----------------------------------------------------------------------------
# Fixtures and mocks
# -----------------------------------------------------------------------------
@pytest.fixture
def valid_orcid_no():
    """Um número ORCiD válido."""
    return "0000-0002-0187-774X"


@pytest.fixture
def valid_orcid_uri():
    """Um URI ORCiD válido."""
    return "https://orcid.org/0000-0002-0187-774X"


@pytest.fixture
def invalid_orcid():
    """Um ORCiD que não valida."""
    return "0000-0002-0187-7741"


@pytest.fixture
def valid_config(valid_orcid_no):
    """Exemplo de configuração válida."""
    return WASTHConfig(
        valid_orcid_no,
        "Pedro Paulo Palazzo",
        Path("casa"),
        Path("thesaurus"),
    )


@pytest.fixture
def valid_env_payload(valid_orcid_no):
    return {
        env_file: Path("wasth.env"),
        orcid: valid_orcid_no,
        profile_name: "Pedro Paulo Palazzo",
        works: "casa",
        vocab: "thesaurus",
        confirm: True,
    }


# -----------------------------------------------------------------------------
# Test functions
# -----------------------------------------------------------------------------
def test_valid_config(
    valid_env_payload: dict[str, str | Path | bool],
    valid_config: WASTHConfig,
) -> None:
    assert setup_config(valid_env_payload) == (valid_config, False)
