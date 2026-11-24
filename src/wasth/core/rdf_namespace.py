from pathlib import Path

from arqtrad_schema.datamodel.arqtrad_schema_pydantic import (
    SkosBroaderRelation,
    SkosMappingRelation,
    SkosNarrowerRelation,
)
from linkml_runtime import SchemaView
from rdflib import Graph, Literal, Namespace, URIRef

from .curie import expand_curie

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ISO = Namespace("http://purl.org/iso25964/skos-thes#")

ARQTRAD = "https://vocabulario.tradicional.arq.br/w/"

BROADER_PREDICATES = {
    SkosBroaderRelation.broader: SKOS.broader,
    SkosBroaderRelation.generic: ISO.broaderGeneric,
    SkosBroaderRelation.partitive: ISO.broaderPartitive,
    SkosBroaderRelation.instantial: ISO.broaderInstantial,
}

MAPPING_PREDICATES = {
    SkosMappingRelation.exact: SKOS.exactMatch,
    SkosMappingRelation.close: SKOS.closeMatch,
    SkosMappingRelation.broad: SKOS.broadMatch,
    SkosMappingRelation.narrow: SKOS.narrowMatch,
    SkosMappingRelation.related: SKOS.relatedMatch,
}


def narrower_predicate(broader_predicate: URIRef) -> URIRef:
    if broader_predicate == SKOS.broader:
        return SKOS.narrower

    local_name = str(broader_predicate).rsplit("#", 1)[-1]
    narrower_name = local_name.replace("broader", "narrower", 1)

    return URIRef(f"{ISO}{narrower_name}")


def local_to_uri(local_id: str) -> URIRef:
    if local_id.startswith("arqtrad:") or local_id.startswith(ARQTRAD):
        return expand_curie(local_id)
    return URIRef(f"{ARQTRAD}{local_id}/")


def reference_id(reference) -> str:
    target = reference.concept_name

    if isinstance(target, str):
        return target

    return target.id
