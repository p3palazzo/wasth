import pytest
import wasth.valida

@pytest.fixture
def testfile():
    f = "testdata/casa/br_df-planaltina-casarao_azul.md"
    return f

# Testes de YAML linting

def test_f_read(testfile):
    assert type(wasth.valida.f_read(testfile)) is dict

def test_prt_title(testfile):
    assert wasth.valida.prt_title(testfile) == "Casarão Azul"

def test_f_lint(testfile):
    assert type(wasth.valida.f_lint(testfile)) is list
