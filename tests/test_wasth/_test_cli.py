"""Testes da interface CLI, não das funções chamadas por ela."""
import pytest
import typer

import wasth.cli


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
    return  "0000-0002-0187-7741"

def test_orcid_no_passes(valid_orcid_no):
    "O número ORCiD é válido, o teste passa"
    assert wasth.cli.user_orcid(valid_orcid_no) == valid_orcid_no

def test_orcid_uri_passes(valid_orcid_no, valid_orcid_uri):
    "O URI do ORCiD é válido, o teste passa e retorna o número"
    assert wasth.cli.user_orcid(valid_orcid_uri) == valid_orcid_no

def test_orcid_fails(invalid_orcid):
    "O ORCiD é inválido, o teste retorna um erro."
    with pytest.raises(typer.BadParameter) as e:
        wasth.cli.user_orcid(invalid_orcid)
    assert str(e.value) == ":w:  ORCiD inválido."
