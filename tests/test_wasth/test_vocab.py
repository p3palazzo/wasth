"""Testa representações do vocabulário controlado em forma de objetos."""

import pytest
from rdflib import URIRef

from wasth.core.rdf_namespace import local_concept_uri, reference_id


@pytest.fixture
def local_concept() -> dict:
    return {
        "refid": "adobe",
        "uri": URIRef("https://vocabulario.tradicional.arq.br/w/adobe/"),
    }


def test_local_concept(local_concept) -> None:
    assert local_concept_uri(local_concept["refid"]) == local_concept["uri"]


def test_external_ref() -> None:
    pass
