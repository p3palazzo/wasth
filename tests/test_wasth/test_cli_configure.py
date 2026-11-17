"""Testes da interface CLI, não das funções chamadas por ela."""

from pathlib import Path

import pytest

from wasth.cli.configure import (
    WASTHConfig,
    orcid_profile_name,
    setup_folders,
    setup_user,
)


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
    dwg_dir = tmp_path / "desenho"

    works_dir.mkdir()
    vocab_dir.mkdir()
    dwg_dir.mkdir()

    return WASTHConfig(
        valid_orcid_no,
        "Pedro Paulo Palazzo",
        works_dir.resolve(),
        vocab_dir.resolve(),
        dwg_dir.resolve(),
    )


@pytest.fixture
def mock_orcid_profile_name(monkeypatch, valid_orcid_no):
    def fake_orcid_profile_name(current):
        return valid_orcid_no, "Pedro Paulo Palazzo"

    monkeypatch.setattr(
        "wasth.cli.configure.orcid_profile_name",
        fake_orcid_profile_name,
    )


# -----------------------------------------------------------------------------
# Test functions
# -----------------------------------------------------------------------------
def test_valid_config(
    valid_orcid_no: str,
    valid_config: WASTHConfig,
    tmp_path: Path,
    mock_orcid_profile_name,
) -> None:
    works = tmp_path / "casa"
    vocab = tmp_path / "thesaurus"
    dwg = tmp_path / "desenho"

    user_setup, changed_user = setup_user(
        orcid=valid_orcid_no,
        profile_name="Pedro Paulo Palazzo",
        confirm=False,
    )

    folder_setup, changed_folders = setup_folders(
        works=works,
        vocab=vocab,
        dwg=dwg,
        confirm=False,
    )

    result = WASTHConfig(
        orcid=user_setup.orcid,
        profile_name=user_setup.profile_name,
        works=folder_setup.works,
        vocab=folder_setup.vocab,
        dwg=folder_setup.dwg,
    )

    assert result == valid_config
    assert not changed_user
    assert not changed_folders
