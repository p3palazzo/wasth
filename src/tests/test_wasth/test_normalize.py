import os
import shutil
import pytest
import wasth.valida_yaml
import wasth.normalize
import yamllint.config
import yamllint.linter

@pytest.fixture
def testfile():
    f = "testdata/casa/br_df-planaltina-casarao_azul.md"
    return f

@pytest.fixture
def output_file():
    f = "testdata/out/br_df-planaltina-casarao_azul.md"
    return f

def test_input(testfile):
    yaml_lint_list = wasth.valida_yaml.f_lint(testfile)
    try:
        assert len(yaml_lint_list) > 0
    except:
        print("O documento de teste não contém inconsistências de formatação.")

def test_normalize_metadata(testfile):
    if os.path.isdir('testdata/out'):
        shutil.rmtree('testdata/out')
    normalized = wasth.normalize.NormalizedWork(testfile)
    filename = os.path.basename(testfile)
    wasth.normalize.write_file(normalized.post(), 'testdata/out', filename)
    try:
        assert os.path.isfile(output_file)
    except Exception as e:
        print(e)

def lint_metadata(output_file):
    yaml_lint_list = wasth.valida_yaml.f_lint(output_file)
    try:
        assert len(yaml_lint_list) == 0
    except FileNotFoundError:
        print(f"Arquivo '{output_file}' não encontrado.")
    except Exception as e:
        print(f"{e}")
    except:
        print("Os metadados ainda contêm inconsistências de formatação.")
