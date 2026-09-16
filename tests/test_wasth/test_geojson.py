"""Testes de geoprocessamento com geoJSON, leitura e escrita."""
from pathlib import Path

import frontmatter
import geojson
import pytest

import wasth
import wasth.core.normalize as norm
from wasth.core import models
from wasth.lugar import lugar


@pytest.fixture
def testfile():
    """Ficha de obra no formato antigo."""
    return Path("testdata/casa/br_df-planaltina-casarao_azul.md")

@pytest.fixture
def input_dir():
    """Pasta de leitura das fichas no formato novo."""
    return Path("testdata/casa")

@pytest.fixture
def output_dir() -> Path:
    """Pasta para teste de gravação."""
    return Path("testdata/out")

@pytest.fixture
def geojson_ibge():
    """Amostra de lugares na base cartográfica do IBGE:
    povoado, cidade, capital estadual e federal
    """
    return Path("testdata/BR-bc250.geojson")

def test_geoprocessa(testfile):
    """Testa tipos de objetos retornados pelas funções."""
    metadata = frontmatter.load(testfile)
    post = norm.normalize(metadata)
    assert isinstance(post, frontmatter.Post)
    work = wasth.Work.from_post(post)
    assert isinstance(work, wasth.Work)
    places = work.places()
    assert isinstance(places, geojson.FeatureCollection)
    assert places.errors() == []
    for place in places['features']:
        assert isinstance(place, geojson.Feature)

def test_lugar(geojson_ibge, output_dir) -> list | None:
    """Testa escrita de fichas a partir do geoJSON da Base Cartográfica IBGE."""
    paths: models.InOutPaths = {'filelist': [ geojson_ibge ], 'output_dir': output_dir}
    result = lugar.main(paths)
    assert len(paths['filelist']) > 0
    assert isinstance(result, list)
    assert len(result) > 0
