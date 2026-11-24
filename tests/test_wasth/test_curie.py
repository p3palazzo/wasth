"""Testa o carregamento e a validação de CURIEs."""

import pytest

from wasth.core.curie import curie_converter


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
        "http://vocab.getty.edu/aat/",
    ]


@pytest.fixture
def invalid_uri_prefixes() -> list[str]:
    return [
        "http://schemas.talis.com/2005/address/schema#",
        "http://purl.obolibrary.org/obo/DDANAT_",
        "http://www.astro.umd.edu/~eshaya/astro-onto/owl/physics.owl#",
    ]


def test_prefixes(
    valid_prefixes, invalid_prefixes, valid_uri_prefixes, invalid_uri_prefixes
) -> None:
    prefixes = curie_converter.get_prefixes()
    for prefix in valid_prefixes:
        assert prefix in prefixes
    for prefix in invalid_prefixes:
        assert prefix not in prefixes
    uri_prefixes = curie_converter.get_uri_prefixes()
    for prefix in valid_uri_prefixes:
        assert prefix in uri_prefixes
    for prefix in invalid_uri_prefixes:
        assert prefix not in uri_prefixes
