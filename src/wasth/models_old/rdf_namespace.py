from typing import Literal

from rdflib import Namespace, URIRef

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SKOSTHES = Namespace("https://www.dublincore.org/specifications/skos-thes/ns/#")

BASE = "https://vocabulario.tradicional.arq.br/"
SCHEME = f"{BASE}scheme/"
CONCEPT = Namespace(f"{BASE}w/")

RELATION_TERMS = Literal[
    "exact",
    "close",
    "broad",
    "narrow",
    "related"
]

RELATION_PREDICATES: dict[RELATION_TERMS, URIRef] = {
    "exact": SKOS.exactMatch,
    "close": SKOS.closeMatch,
    "broad": SKOS.broadMatch,
    "narrow": SKOS.narrowMatch,
    "related": SKOS.relatedMatch
}

BROADER_TERMS = Literal[
    "generic",
    "instantial",
    "partitive",
    "related"
]

BROADER_PREDICATES: dict[BROADER_TERMS, URIRef] = {
    "generic": SKOSTHES.broaderGeneric,
    "instantial": SKOSTHES.broaderInstantial,
    "partitive": SKOSTHES.broaderPartitive,
    "related": SKOS.related
}

RELATION_PREDICATE_TO_TERM: dict[URIRef, RELATION_TERMS] = {
    predicate: term for term, predicate in RELATION_PREDICATES.items()
}

BROADER_PREDICATE_TO_TERM: dict[URIRef, BROADER_TERMS] = {
    predicate: term for term, predicate in BROADER_PREDICATES.items()
}
