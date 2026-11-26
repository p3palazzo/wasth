"""Construção de um vocabulário a partir de várias fichas de Concept ao mesmo tempo.

O módulo só depende dos atributos `id`, `broader`, `relation`, `mapping`,
`narrower`, `bibliographic_citation` e `title` dos conceitos (e de
`models.ref_id`), de modo que funciona igualmente com fichas lidas de
arquivos, de um banco de dados ou de qualquer outro suporte.
"""

from functools import cache

from arqtrad_schema.datamodel.arqtrad_schema_pydantic import (
    SkosBroaderRelation,
    SkosMappingRelation,
    linkml_meta,
)
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS
from rich import print as rprint

from wasth.models import Concept

from .curie import expand_curie


# --------------------------------------------------------------------------------------------------
# Funções auxiliares
# --------------------------------------------------------------------------------------------------
def schema_namespaces() -> dict[str, Namespace]:
    prefixes = linkml_meta["prefixes"]
    return {
        p["prefix_prefix"]: Namespace(p["prefix_reference"]) for p in prefixes.values()
    }


namespaces = schema_namespaces()

VASCON = namespaces["arqtrad"]
ISO = namespaces["iso"]

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
    """Gera as categorias de descendentes a partir das categorias de ancestrais."""
    if broader_predicate == SKOS.broader:
        return SKOS.narrower

    local_name = str(broader_predicate).rsplit("#", 1)[-1]
    narrower_name = local_name.replace("broader", "narrower", 1)

    return URIRef(f"{ISO}{narrower_name}")


@cache
def local_concept_uri(local_id: str) -> URIRef:
    """Obtém uma URI do Vocabulário de Arquitetura e Sistemas Construtivos Tradicionais a partir
    de um identificador local.

    :param local_id: Texto do identificador local.
    :return: URI completa para o objeto.
    :rtype: RDFLib.URIRef
    """
    if ":" in local_id:
        return URIRef(expand_curie(local_id))
    return URIRef(f"{str(VASCON)}{local_id}/")


def reference_id(reference) -> URIRef:
    """Resolve a URI completa de uma referência inserida nas fichas."""
    target = reference.refid
    id_type = reference.refid_type or "uri"

    match id_type:
        case "local":
            return local_concept_uri(target)
        case "uri" | "iri":
            return URIRef(expand_curie(target))
        case _:
            raise ValueError(
                f"{reference.refid_type!r} não é um tipo de referência válido."
            )


# --------------------------------------------------------------------------------------------------
# Construção do grafo
# --------------------------------------------------------------------------------------------------
def add_concept(graph: Graph, concept: Concept) -> None:
    """Insere os triplos de um conceito no grafo."""
    subject = local_concept_uri(concept.id)

    graph.add((subject, RDF.type, SKOS.Concept))
    graph.add((subject, SKOS.prefLabel, Literal(concept.title, lang="pt")))

    if concept.content:
        graph.add((subject, SKOS.scopeNote, Literal(concept.content, lang="pt")))

    if concept.description:
        graph.add((subject, SKOS.definition, Literal(concept.description, lang="pt")))

    for reference in concept.broader or []:
        parent = reference_id(reference)
        broader = BROADER_PREDICATES[reference.broader_match]
        narrower = narrower_predicate(broader)

        graph.add((subject, broader, parent))
        graph.add((parent, narrower, subject))

        if reference.broader_preferred:
            graph.add((subject, ISO.broaderPreferred, parent))

    for reference in concept.relation or []:
        related = reference_id(reference)

        graph.add((subject, SKOS.related, related))

    for reference in concept.mapping or []:
        external = reference_id(reference)

        graph.add((subject, MAPPING_PREDICATES[reference.mapping_match], external))


def build_vocabulary_graph(concepts: list[Concept]) -> Graph:
    """Inicializa o grafo preenchendo-o com a lista de conceitos recebida."""
    graph = Graph()

    graph.bind("vascon", VASCON)
    graph.bind("skos", SKOS)
    graph.bind("iso", ISO)

    count = 1
    for concept in concepts:
        add_concept(graph, concept)
        rprint(
            f"{count}. [b]{concept.title}[/b] [dim]({concept.concept_type})[/dim] adicionado ao grafo."
        )
        count += 1

    return graph
