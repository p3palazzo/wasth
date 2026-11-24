"""Testa o carregamento e a validação de CURIEs."""

import pytest
from curies import Converter

from wasth.core.curie import expand_curie, make_converter


@pytest.fixture
def valid_prefixes() -> list[str]:
    return ["dcterms", "geonames", "schema", "wd"]


@pytest.fixture
def invalid_prefixes() -> list[str]:
    return ["obo", "chebi", "whatever"]


@pytest.fixture
def valid_uri_prefixes() -> list[str]:
    return [
        "http://www.lido-schema.org/",
        "http://purl.org/iso25964/skos-thes#",
        "https://vocab.getty.edu/aat/",
    ]


@pytest.fixture
def invalid_uri_prefixes() -> list[str]:
    return [
        "http://schemas.talis.com/2005/address/schema#",
        "http://purl.obolibrary.org/obo/DDANAT_",
        "http://www.astro.umd.edu/~eshaya/astro-onto/owl/physics.owl#",
    ]


@pytest.fixture
def valid_curies() -> list[dict]:
    return [
        {"curie": "aat:300081138", "uri": "https://vocab.getty.edu/aat/300081138"},
        {"curie": "geonames:3408360", "uri": "https://sws.geonames.org/3408360"},
        {"curie": "wd:Q2", "uri": "http://www.wikidata.org/entity/Q2"},
        {
            "curie": "isni:0000000122385157",
            "uri": "https://isni.org/isni/0000000122385157",
        },
    ]


@pytest.fixture
def invalid_curies() -> list[dict]:
    return []


def test_prefix_map() -> None:
    assert isinstance(make_converter(), Converter)


def test_prefixes(
    valid_prefixes, invalid_prefixes, valid_uri_prefixes, invalid_uri_prefixes
) -> None:
    prefixes = make_converter().get_prefixes()
    for prefix in valid_prefixes:
        assert prefix in prefixes
    for prefix in invalid_prefixes:
        assert prefix not in prefixes
    uri_prefixes = make_converter().get_uri_prefixes()
    for prefix in valid_uri_prefixes:
        assert prefix in uri_prefixes
    for prefix in invalid_uri_prefixes:
        assert prefix not in uri_prefixes


def test_expand(valid_curies, invalid_curies) -> None:
    for item in valid_curies:
        assert expand_curie(item["curie"]) == item["uri"]
