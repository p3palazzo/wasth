"""Testes da interface CLI, não das funções chamadas por ela."""

from pathlib import Path

import pytest

from wasth.cli.configure import WASTHConfig, orcid_resolve, setup_config


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
def valid_config(valid_orcid_no, tmp_path: Path):
    """Exemplo de configuração válida."""
    works_dir = tmp_path / "casa"
    vocab_dir = tmp_path / "thesaurus"

    works_dir.mkdir()
    vocab_dir.mkdir()

    return WASTHConfig(
        valid_orcid_no,
        "Pedro Paulo Palazzo",
        works_dir.resolve(),
        vocab_dir.resolve(),
    )


@pytest.fixture
def mock_orcid_resolve(monkeypatch, valid_orcid_no):
    def fake_orcid_resolve(current):
        return valid_orcid_no, "Pedro Paulo Palazzo"

    monkeypatch.setattr(
        "wasth.cli.configure.orcid_resolve",
        fake_orcid_resolve,
    )


# -----------------------------------------------------------------------------
# Test functions
# -----------------------------------------------------------------------------
def test_valid_config(
    valid_orcid_no: str,
    valid_config: WASTHConfig,
    tmp_path: Path,
    mock_orcid_resolve,
) -> None:
    works = tmp_path / "casa"
    vocab = tmp_path / "thesaurus"

    result = setup_config(
        env_file=Path("wasth.env"),
        orcid=valid_orcid_no,
        profile_name="Pedro Paulo Palazzo",
        works=str(works),
        vocab=str(vocab),
        confirm=False,
    )
    assert result == (valid_config, False)
