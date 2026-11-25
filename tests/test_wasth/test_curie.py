"""Testa o carregamento e a validação de CURIEs."""

import pytest
from curies import Converter
from curies.api import ExpansionError
from rdflib import URIRef

from wasth.core.curie import expand_curie, make_converter


@pytest.fixture
def valid_prefixes() -> list[str]:
    """Prefixos CURIE cadastrados no esquema ArqTrad."""
    return ["dcterms", "geonames", "schema", "wd"]


@pytest.fixture
def invalid_prefixes() -> list[str]:
    """Prefixos CURIE não cadastrados no esquema ArqTrad."""
    return ["obo", "chebi", "whatever"]


@pytest.fixture
def valid_uri_prefixes() -> list[str]:
    """Prefixos URI cadastrados no esquema ArqTrad."""
    return [
        "http://www.lido-schema.org/",
        "http://purl.org/iso25964/skos-thes#",
        "https://vocab.getty.edu/aat/",
    ]


@pytest.fixture
def invalid_uri_prefixes() -> list[str]:
    """Prefixos URI não cadastrados no esquema ArqTrad."""
    return [
        "http://schemas.talis.com/2005/address/schema#",
        "http://purl.obolibrary.org/obo/DDANAT_",
        "http://www.astro.umd.edu/~eshaya/astro-onto/owl/physics.owl#",
    ]


@pytest.fixture
def valid_curies() -> list[dict]:
    """CURIEs válidos e suas URIs correspondentes."""
    return [
        {
            "curie": "aat:300081138",
            "uri": URIRef("https://vocab.getty.edu/aat/300081138"),
        },
        {
            "curie": "geonames:3408360",
            "uri": URIRef("https://sws.geonames.org/3408360"),
        },
        {"curie": "wd:Q2", "uri": URIRef("http://www.wikidata.org/entity/Q2")},
        {
            "curie": "isni:0000000122385157",
            "uri": URIRef("https://isni.org/isni/0000000122385157"),
        },
    ]


@pytest.fixture
def invalid_curies() -> list[str]:
    """CURIEs com prefixos inválidos."""
    return ["abc:1234", "whatever:something", "wx:XPTO"]


def test_prefix_map() -> None:
    """Testa que a inicialização do conversor de CURIE resultou."""
    assert isinstance(make_converter(), Converter)


def test_prefixes(
    valid_prefixes, invalid_prefixes, valid_uri_prefixes, invalid_uri_prefixes
) -> None:
    """Testa a obtenção de prefixos CURIE e de URIs válidos."""
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
    """Testa que os CURIEs válidos retornam os URIs esperados e que os inválidos dão erro.

    Obs.: Se o prefixo for válido, a expansão terá sucesso, mesmo que o ID seja inexistente.
    """
    for item in valid_curies:
        assert expand_curie(item["curie"]) == item["uri"]
    for item in invalid_curies:
        with pytest.raises(ExpansionError):
            expand_curie(item)
