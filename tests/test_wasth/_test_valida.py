"""Testes de validação contra esquema XML
"""
from pathlib import Path

import frontmatter
import pytest
import xmlschema

from wasth.core import valida_xml, valida_yaml


@pytest.fixture
def obra_formato_antigo() -> Path:
    "Ficha do Casarão Azul no formato antigo"
    return Path("testdata/casa/br_df-planaltina-casarao_azul.md")

@pytest.fixture
def invalid_xml() -> Path:
    "Um documento XML mal estruturado."
    return Path("testdata/invalid.xml")

@pytest.fixture
def valid_xml() -> Path:
    "Um documento exemplar do LIDO-Handbuch."
    return Path("testdata/lido/Stabkirche_Gol_Original_de_en_v1.1_20250331.xml")

def test_f_read():
    "Testa se o arquivo pode ser lido"
    assert isinstance(valida_yaml.f_read(obra_formato_antigo), dict)

def test_parse_metadata():
    "Testa se os metadados podem ser lidos"
    post = valida_yaml.parse_metadata(obra_formato_antigo)
    assert post['title'] == "Casarão Azul"
    assert len(post.content) > 1
    assert isinstance(post, frontmatter.Post)

def test_f_lint():
    "Verifica se a função gerou uma lista"
    assert isinstance(valida_yaml.f_lint(obra_formato_antigo), list)


def test_create_schema():
    "Testa o esquema XML"
    xml_profile = valida_xml.create_schema()
    assert isinstance(xml_profile, xmlschema.XMLSchema11)

def test_valid_xml(valid_xml):
    "Testa que o arquivo exemplo valida com o esquema"
    assert valida_xml.valid_xml(valid_xml) is True

def test_invalid_xml(invalid_xml):
    "Testa que um arquivo inválido falha na validação"
    with pytest.raises(xmlschema.exceptions.XMLResourceParseError):
        valida_xml.valid_xml(invalid_xml)
