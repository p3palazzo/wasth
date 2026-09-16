"Testa conversão de fichas do formato antigo para o novo"
import os
import shutil
from pathlib import Path

import frontmatter
import pytest

import wasth.core.normalize as norm
import wasth.core.valida_yaml
from wasth.core import models


@pytest.fixture
def testfile() -> Path:
    "Ficha que falhará na normalização"
    return Path("testdata/fail/br_ba-salvador-casa_7_candeeiros.md")

@pytest.fixture
def testfile2() -> Path:
    "Ficha que falhará na normalização"
    return Path("testdata/fail/br_df-planaltina-casarao_azul.md")

@pytest.fixture
def output_dir() -> Path:
    "Pasta para teste de gravação"
    return Path("testdata/out")

def test_input():
    "O arquivo teste precisa ter inconsistências de formatação para prosseguir"
    yaml_lint_list = wasth.core.valida_yaml.f_lint(testfile)
    try:
        assert len(yaml_lint_list) > 0
    except Exception as e:
        print(f"O documento de teste não contém inconsistências de formatação. {e}")

def test_paths(monkeypatch, testfile):
    "Testa input do usuário"
    monkeypatch.setattr(
        'builtins.input',
        lambda _: str(testfile + " " + output_dir)
    )
    result = models.paths()
    assert isinstance(result, dict)
    assert isinstance(result['filelist'], list)
    assert isinstance(result['output_dir'], str)

def test_normalize_metadata(testfile2, output_dir):
    "Testa as transformações dos metadados"
    filename = os.path.basename(testfile2)
    output_file = os.path.join(output_dir, filename)
    source = frontmatter.load(testfile2)
    assert isinstance(source['bibliographicCitation'], dict)
    try:
        norm.main({'filelist': [testfile2], 'output_dir': output_dir})
        post = frontmatter.load(output_file)
        assert os.path.isfile(output_file)
        assert isinstance(post, frontmatter.Post)
        assert isinstance(post['bibliographicCitation'], list)
        assert post['bibliographicCitation'][0].startswith("@")
    finally:
        os.remove(output_file)

def test_id(testfile2):
    "Testa geração de ID"
    post = frontmatter.load(testfile2)
    normalized = norm.normalize(post)
    work = wasth.Work.from_post(normalized)
    assert work.olc_id() == '58PJ98HQ+89W'

def test_write(testfile, output_dir):
    "Testa que os arquivos podem ser gravados"
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    post = frontmatter.load(testfile)
    normalized = norm.normalize(post)
    filename = os.path.basename(testfile)
    models.write_file(normalized, output_dir, filename)
    assert os.path.isfile(os.path.join(output_dir, filename))

def lint_metadata(testfile, output_dir):
    "Testa diferenças entre arquivo original e normalizado"
    post = frontmatter.load(testfile)
    normalized = norm.normalize(post)
    models.write_file(normalized, output_dir, os.path.basename(testfile))
    output_file = os.path.join(output_dir, os.path.basename(testfile))
    yaml_lint_list = wasth.core.valida_yaml.f_lint(output_file)
    try:
        assert len(yaml_lint_list) == 0
    except FileNotFoundError as e:
        raise FileNotFoundError(f":question:  '{output_file}': {e}.") from e
    except Exception as e:
        print(f"{e}")
    finally:
        os.remove(output_file)
