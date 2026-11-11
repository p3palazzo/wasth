"""Verificações que envolvem várias fichas de Concept ao mesmo tempo.

O módulo só depende dos atributos `id`, `broader`, `relation`, `mapping`,
`narrower`, `bibliographic_citation` e `title` dos conceitos (e de
`models.ref_id`), de modo que funciona igualmente com fichas lidas de
arquivos, de um banco de dados ou de qualquer outro suporte.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from arqtrad_schema.datamodel.arqtrad_schema_pydantic import \
    NarrowerConceptReference
from pydantic import ValidationError

from wasth.models import Concept, ref_id


@dataclass
class Vocabulary:
    concepts: dict[str, Concept] = field(default_factory=dict)
    load_errors: list[tuple[str, str]] = field(default_factory=list)

    # ------------------------------------------------------------ loading
    @classmethod
    def from_concepts(cls, concepts: Iterable[Concept]) -> "Vocabulary":
        vocab = cls()
        for c in concepts:
            if c.id in vocab.concepts:
                vocab.load_errors.append((c.id, "`id` duplicado."))
            else:
                vocab.concepts[c.id] = c
        return vocab

    @classmethod
    def from_directory(cls, root: Path, pattern: str = "**/*.md") -> "Vocabulary":
        """Carrega todas as fichas; erros de validação são coletados, não lançados."""
        vocab = cls()
        for path in sorted(Path(root).glob(pattern)):
            try:
                c = Concept.from_file(path)
            except (ValidationError, ValueError) as exc:
                vocab.load_errors.append((str(path), str(exc)))
                continue
            if c.id in vocab.concepts:
                vocab.load_errors.append((str(path), f"`id` duplicado: {c.id!r}."))
            else:
                vocab.concepts[c.id] = c
        return vocab

    # -------------------------------------------------------------- graph
    def _broader_graph(self) -> dict[str, set[str]]:
        return {cid: set(c.broader_ids) for cid, c in self.concepts.items()}

    def ancestors(self, cid: str) -> set[str]:
        graph, seen, stack = self._broader_graph(), set(), [cid]
        while stack:
            for parent in graph.get(stack.pop(), ()):
                if parent not in seen:
                    seen.add(parent)
                    stack.append(parent)
        return seen

    def descendants(self, cid: str) -> set[str]:
        return {o for o in self.concepts if cid in self.ancestors(o)}

    def top_concepts(self) -> list[str]:
        return sorted(cid for cid, c in self.concepts.items() if not c.broader_ids)

    # ------------------------------------------------------------- checks
    def check(self) -> list[str]:
        """Devolve uma lista de problemas legíveis (vazia = vocabulário íntegro)."""
        problems = [f"{where}: {msg}" for where, msg in self.load_errors]

        # Alvos inexistentes (mapping aponta para vocabulários externos: ignorado).
        for cid, c in self.concepts.items():
            for name, i, ref in c.iter_references():
                target = ref_id(ref)
                if name != "mapping" and target not in self.concepts:
                    problems.append(f"{cid}: {name}[{i}] aponta para {target!r}, que não existe.")

        # Ciclos em broader.
        try:
            TopologicalSorter(self._broader_graph()).prepare()
        except CycleError as exc:
            problems.append(f"Ciclo em `broader`: {' -> '.join(map(str, exc.args[1]))}")
            return problems  # ancestors() abaixo assume ausência de ciclos

        for cid, c in self.concepts.items():
            # SKOS S27: related não pode ligar um conceito a seu ancestral/descendente.
            for other in c.relation_ids & self.concepts.keys():
                if other in self.ancestors(cid) or cid in self.ancestors(other):
                    problems.append(
                        f"{cid}: `relation` com {other!r}, que é ancestral/descendente (viola SKOS S27)."
                    )
                # skos:related é simétrica.
                elif cid not in self.concepts[other].relation_ids:
                    problems.append(f"{cid}: `relation` com {other!r} não é recíproca.")

            # A descrição da classe exige citação bibliográfica.
            if not c.bibliographic_citation:
                problems.append(f"{cid}: sem `bibliographic_citation`.")
        return problems

    # ----------------------------------------------------- derived fields
    def with_derived_narrower(self) -> dict[str, Concept]:
        """Cópias dos conceitos com `narrower` calculado a partir de `broader`.

        Usa `model_copy(update=...)`, que não revalida; por isso é seguro
        mesmo com validate_assignment=True. Ao reexportar para Markdown,
        exclua `narrower` (é derivado, não deve ser gravado na ficha).
        """
        children: dict[str, list[NarrowerConceptReference]] = {}
        for child in self.concepts.values():
            for ref in child.broader or []:
                parent = ref_id(ref)
                if parent in self.concepts:
                    children.setdefault(parent, []).append(
                        NarrowerConceptReference(
                            # Esquema atual: concept_name é um Concept embutido.
                            # Se virar `inlined: false`, passar `child.id`.
                            narrower_match=ref.broader_match,  # enums idênticos
                            concept_name=child,
                        )
                    )
        return {
            cid: c.model_copy(update={"narrower": children.get(cid) or None})
            for cid, c in self.concepts.items()
        }
