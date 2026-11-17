"""Testes de geoprocessamento com geoJSON, leitura e escrita."""

from wasth.cli._common import markdown_filelist
from wasth.cli.export import geojson_collection
from wasth.models import Work


def test_geoprocessa(valid_works):
    """Testa tipos de objetos retornados pelas funções."""
    files = markdown_filelist(valid_works)
    assert files
    works = [Work.from_file(f) for f in files]
    assert works
    collection = geojson_collection(works)
    assert collection
