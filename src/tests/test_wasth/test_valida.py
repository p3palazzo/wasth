import pytest
import wasth.valida_yaml

@pytest.fixture
def testfile():
    f = "testdata/casa/br_df-planaltina-casarao_azul.md"
    return f

# Testes de YAML linting

def test_f_read(testfile):
    assert type(wasth.valida_yaml.f_read(testfile)) is dict

def test_prt_title(testfile):
    assert wasth.valida_yaml.prt_title(testfile) == "Casarão Azul"

def test_f_lint(testfile):
    assert type(wasth.valida_yaml.f_lint(testfile)) is list

# Testes de validação do esquema
