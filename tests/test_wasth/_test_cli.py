"""Testes da interface CLI, não das funções chamadas por ela."""

import pytest
import typer

from wasth.cli import main


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


# -----------------------------------------------------------------------------
# Test functions
# -----------------------------------------------------------------------------
def test_cli_entrypoint() -> None:
    assert 
