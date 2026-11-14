"""Testes da interface CLI, não das funções chamadas por ela."""

from pathlib import Path

import pytest
import typer

from wasth.cli.configure import WASTHConfig, setup_config


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
        Path("testdata/casa").expanduser().resolve(),
        Path("testdata/thesaurus").expanduser().resolve(),
    )


# -----------------------------------------------------------------------------
# Test functions
# -----------------------------------------------------------------------------
def test_valid_config(
    valid_orcid_no: str,
    valid_config: WASTHConfig,
) -> None:
    result = setup_config(
        env_file=Path("wasth.env"),
        orcid=valid_orcid_no,
        profile_name="Pedro Paulo Palazzo",
        works="testdata/casa",
        vocab="testdata/thesaurus",
        confirm=False,
    )
    assert result == (valid_config, False)
