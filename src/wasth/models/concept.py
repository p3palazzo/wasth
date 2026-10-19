from pathlib import Path

from pydantic import HttpUrl
from rdflib import Graph
from rdflib import Literal as RDFLiteral
from rdflib import URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

from wasth.models import rdf_namespace

from .refs import *
from .thing import Thing


class Concept(Thing):
    """Define um conceito de vocabulário controlado compatível com SKOS:THES.

    Fornece métodos para importar e exportar RDF:XML e JSON-LD.
    """
    broader:  list[SKOSHierarchy] | None = None
    narrower: list[SKOSHierarchy] | None = None
    relation: list[SKOSRelation] | None = None

    @classmethod
    def from_graph(cls, graph: Graph, subject: URIRef | str) -> "Concept":
        """Cria objeto Concept a partir de um grafo RDF.

        :param graph: RDF graph containing the concept.
        :param subject: URI of the concept to import.
        :returns: A validated `Concept`.
        :rtype: Concept
        """
        subject = URIRef(str(subject))

        if (subject, RDF.type, SKOS.Concept) not in graph:
            raise ValueError(f"{subject} não é um skos:Concept.")

        relation: list[SKOSRelation] = []
        broader: list[SKOSHierarchy] = []

        # Mapping and associative relations: relation[].match
        for predicate, term in rdf_namespace.RELATION_PREDICATE_TO_TERM.items():
            for obj in graph.objects(subject, predicate):
                if not isinstance(obj, URIRef):
                    continue
                related: SKOSRelation = {
                    "match": term,
                    "name": {"refid": HttpUrl(str(obj))},
                }
                relation.append(related)

        # Hierarchical relations: broader[].match
        for predicate, term in rdf_namespace.BROADER_PREDICATE_TO_TERM.items():
            for obj in graph.objects(subject, predicate):
                if not isinstance(obj, URIRef):
                    continue
                broad: SKOSHierarchy = {
                    "match": term,
                    "name": {"refid": HttpUrl(str(obj))},
                }
                broader.append(broad)

        pref_label = graph.value(subject, SKOS.prefLabel)

        description = (
            graph.value(subject, SKOS.definition)
            or graph.value(subject, SKOS.scopeNote)
        )

        content = graph.value(subject, SKOS.scopeNote) \
            if graph.value(subject, SKOS.definition) \
            and graph.value(subject, SKOS.scopeNote) else None

        data: dict[str, str | list[SKOSRelation] | list[SKOSHierarchy] | None] = {
            "id": str(id),
            "title": str(pref_label) if pref_label else str(subject),
            "description": str(description) if description else None,
            "relation": relation,
            "broader": broader,
            "content": str(content),
        }

        if graph.value(subject, DCTERMS.created) \
            or graph.value(subject, DCTERMS.modified):
            data["author"] = (str(
                graph.value(subject, DCTERMS.created)
                or graph.value(subject, DCTERMS.modified)
            ))

        if graph.value(subject, DCTERMS.creator):
            data["author"] = str(graph.value(subject, DCTERMS.creator))

        return cls.model_validate(data)

    @classmethod
    def from_rdf_xml(cls, source: Path | str) -> "Concept":
        graph = Graph().parse(source, format="xml")
        return cls._single_concept_from_graph(graph)

    @classmethod
    def from_json_ld(cls, source: Path | str) -> "Concept":
        graph = Graph().parse(source, format="json-ld")
        return cls._single_concept_from_graph(graph)

    @classmethod
    def _single_concept_from_graph(cls, graph: Graph) -> "Concept":
        concepts = [
            s
            for s in graph.subjects(RDF.type, SKOS.Concept)
            if isinstance(s, URIRef)
        ]

        if len(concepts) != 1:
            raise ValueError(
                f"Esperado exatamente um skos:Concept; encontrados {len(concepts)}."
            )

        return cls.from_graph(graph, concepts[0])

    def _add_relations(
        self,
        graph: Graph,
        subject: URIRef,
        relations: list[SKOSRelation] | list[SKOSHierarchy] | None,
        predicates: dict,
    ) -> None:
        for relation in relations or []:
            predicate = predicates[relation["match"]]
            target = URIRef(str(relation["name"]["refid"]))
            graph.add((subject, predicate, target))

    def to_graph(self) -> Graph:
        """Representa o objeto Concept como grafo do RDF"""
        graph = Graph()
        graph.bind("skos", SKOS)
        subject = URIRef(str(self.id))
        graph.add((subject, RDF.type, SKOS.Concept))

        # Preferred label.
        graph.add((subject, SKOS.prefLabel, RDFLiteral(self.title)))
        for label in self.titles or []:
            graph.add(
                (
                    subject,
                    SKOS.altLabel,
                    RDFLiteral(label["display"]),
                )
            )

        # Notes.
        if self.content:
            graph.add((subject,SKOS.scopeNote,RDFLiteral(self.content)))
        if self.description:
            graph.add((subject,SKOS.note,RDFLiteral(self.description)))

        # Scheme
        scheme = URIRef(rdf_namespace.SCHEME)
        graph.add((scheme, RDF.type, SKOS.ConceptScheme))
        graph.add(
            (
                scheme,
                SKOS.prefTitle,
                RDFLiteral("Vocabulário de Arquitetura Tradicional")
            )
        )
        graph.add((subject, RDF.type, SKOS.Concept))
        graph.add((subject, SKOS.inScheme, scheme))

        # Top-level.
        if not self.broader:
            graph.add((scheme, SKOS.hasTopConcept, subject))
            graph.add((subject, SKOS.topConceptOf, scheme))

        # Relations and matches.
        self._add_relations(
            graph=graph,
            subject=subject,
            relations=self.relation,
            predicates=rdf_namespace.RELATION_PREDICATES,
        )

        self._add_relations(
            graph=graph,
            subject=subject,
            relations=self.broader,
            predicates=rdf_namespace.BROADER_PREDICATES,
        )

        # SKOS:Broader genérico para maior compatibilidade.
        for relation in self.broader or []:
            refid = URIRef(str(relation["name"]["refid"]))
            graph.add((subject, SKOS.broader, refid))
        # TODO: relações inversas (narrower).

        return graph

    def to_rdf_xml(self) -> str:
        return self.to_graph().serialize(format="xml")

    def to_json_ld(self) -> str:
        return self.to_graph().serialize(format="json-ld")

    def write_rdf_xml(self, path: Path) -> Path:
        path.write_text(self.to_rdf_xml(), encoding="utf-8")
        return path

    def write_json_ld(self, path: Path) -> Path:
        path.write_text(self.to_json_ld(), encoding="utf-8")
        return path
