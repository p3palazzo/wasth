import os
import pytest
import wasth.valida_yaml
import wasth.sanitize
import yamllint.config
import yamllint.linter

@pytest.fixture
def testfile():
    f = "testdata/casa/br_df-planaltina-casarao_azul.md"
    return f

def test_sanitize(testfile):
    yaml_lint_list = wasth.valida_yaml.f_lint(testfile)
    try:
        assert len(yaml_lint_list) > 0
    except:
        print("O documento de teste não contém inconsistências de formatação.")
        exit(1)

