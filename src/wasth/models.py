"""Modelos derivados do arqtrad/schema/datamodel e validações adicionais."""

import datetime
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Self

import frontmatter
import geojson
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Concept as _Concept
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import (
    GeographicExtent,
    GeographicPoint,
    Site,
)
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Thing as _Thing
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Work as _Work
from openlocationcode import openlocationcode
from pydantic import field_validator, model_validator
from rdflib import URIRef
from ruamel.yaml import YAML

from .core.curie import expand_all_curies, schema_view
from .core.orcid import parse_orcid

yaml = YAML(typ="rt")


SITE_FIELDS = ("site", "former_site", "intended_site", "other_site")
CONCEPT_REF_FIELDS = ("broader", "relation", "mapping")


# -----------------------------------------------------------------------------
# Utilidades para processar Schema
# -----------------------------------------------------------------------------
def site_location(location: GeographicPoint | None) -> geojson.Point | None:
    """Ponto GeoJSON (lon, lat[, alt]) a partir das coordenadas."""

    if location is None:
        return None
    coords = (location.lon, location.lat)
    if location.alt is not None:
        coords += (location.alt,)
    p = geojson.Point(coords)
    if p.is_valid:
        return p
    return None


def site_extent(
    extent: GeographicExtent | None,
) -> geojson.Polygon | geojson.MultiPolygon | None:
    """Polígono(s) de implantação a partir das coordenadas."""
    if extent is None:
        return None
    try:
        coords = json.loads(extent.coordinates)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(
            f"Coordenadas mal conformadas em geometry_type={extent.geometry_type!r}: {e}"
        ) from e
    match extent.geometry_type:
        case "Polygon":
            footprint = geojson.Polygon(coords)
        case "MultiPolygon":
            footprint = geojson.MultiPolygon(coords)
        case _:
            raise ValueError(f"Tipo de geometria inválido: {extent.geometry_type!r}")
    return footprint if footprint.is_valid else None


# -----------------------------------------------------------------------------
# Subclasses de Schema
# -----------------------------------------------------------------------------
class Thing(_Thing):
    """Dados e métodos comuns a todas as classes de objetos do projeto WASTH:
    Work (obras de arquitetura), Place (lugares), e Concept (itens de vocabulário).

    Apresenta dois métodos para criar um objeto:

    1. De um arquivo Markdown, passando por um objeto frontmatter.Post;
    2. De dados já estruturados pelo frontmatter.Post.

    A inicialização do objeto valida os dados inseridos, especialmente o ORCiD
    do(s) autor(es).
    """

    @classmethod
    def from_file(cls, f: Path) -> Self:
        """Gera o objeto a partir de um arquivo/ficheiro.

        :param f: Caminho para um arquivo/ficheiro no sistema local, \
        em formato Markdown com um bloco (frontmatter) em formato YAML.
        :type f: Path
        :returns: Um objeto em forma de dicionário que pode ser convertido, \
        no todo ou em parte, para vários outros tipos de objetos \
        ou reexportado para Markdown.
        :rtype: Thing
        """
        return cls.from_post(frontmatter.load(f))

    @classmethod
    def from_post(cls, post: frontmatter.Post) -> Self:
        """Gera o objeto a partir de um objeto frontmatter.Post

        :param post: Um objeto já processado a partir de um documento Markdown com frontmatter YAML.
        :type post: frontmatter.Post
        :return: Um objeto que pode ser convertido, no todo ou em parte, para vários outros tipos
        de objetos ou reexportado para Markdown.
        :rtype: Thing
        """
        data = post.metadata.copy()
        if not data:
            raise ValueError("Nenhum dado encontrado neste objeto.")
        data["content"] = post.content

        linkml_class = cls.__name__

        if linkml_class not in schema_view().all_classes():
            raise ValueError(
                f"A classe de objetos {cls.__name__!r} não foi encontrada no esquema de dados."
            )

        expanded_data = expand_all_curies(data, linkml_class)

        return cls.model_validate(expanded_data)

    @field_validator("author", "authors", mode="before")
    @classmethod
    def validate_orcid(
        cls, value: list[str | URIRef] | str | URIRef | None
    ) -> str | list[str] | None:
        """Return a bare, validated ORCID iD using PyORCID-checker."""
        if value is None:
            return value
        if isinstance(value, (list, tuple)):
            return [parse_orcid(v) for v in value]
        return parse_orcid(value)

    @field_validator("record_date", mode="after")
    @classmethod
    def validate_record_date(cls, value: datetime.date | None) -> datetime.date | None:
        """Confirma que a data de criação da ficha não está no futuro."""
        today = datetime.date.today()
        if value is None:
            return today
        if value > today:
            raise ValueError(f"A data da ficha {value} não pode ser uma data futura.")
        return value

    @model_validator(mode="after")
    def exactly_one_author_field(self):
        has_author = self.author is not None
        has_authors = bool(self.authors)  # empty list counts as absent
        if has_author == has_authors:
            raise ValueError("Informe exatamente um entre `author` e `authors`")
        return self


class Work(Thing, _Work):
    """Arcabouço dos dados e métodos das fichas de obras."""

    def _iter_sites(self) -> Iterator[tuple[str, int, Site]]:
        """Percorre todos os sítios, seja campo único ou lista."""
        for name in SITE_FIELDS:
            value = getattr(self, name, None)
            if value is None:
                continue
            sites = value if isinstance(value, list) else [value]
            for i, site in enumerate(sites):
                yield name, i, site

    def olc_id(self) -> str | None:
        """Processa locação para gerar id no formato Open Location Code."""
        loc = self.site.location
        if not loc:
            return None
        if not loc.lat or not loc.lon:
            return None
        return openlocationcode.encode(loc.lat, loc.lon, 11)

    @model_validator(mode="after")
    def _validate_site_geometry(self):
        """Valida coordenadas da locação e da implantação."""
        for name, i, site in self._iter_sites():
            if site_location(site.location) is None and not self.former_site:
                raise ValueError(f"Coordenadas inválidas em {name}[{i}].location")
            if site.extent and (site_extent(site.extent) is None):
                raise ValueError(f"Geometria inválida em {name}[{i}].extent")
        return self

    @model_validator(mode="after")
    def _validate_id(self):
        """Gera o `id` a partir do OLC ou confere o `id` informado."""
        expected = self.olc_id()
        if expected is None:
            raise ValueError(
                "Não é possível gerar ou conferir o `id`: "
                "a obra não tem `site.location` válido."
            )
        if not self.id:
            self.id = expected
        elif str(self.id).strip().upper() != expected:
            raise ValueError(f"""
                `id` {self.id!r} não corresponde ao OLC {expected!r} 
                calculado a partir das coordenadas do sítio.
            """)
        return self

    @property
    def site_location(self) -> geojson.Point | None:
        """Retorna um ponto geoJSON a partir das coordenadas de locação."""
        return site_location(self.site.location) if self.site.location else None

    @property
    def site_extent(self) -> geojson.Polygon | geojson.MultiPolygon | None:
        """Retorna uma feature geoJSON para as coordenadas de implantação."""
        return site_extent(self.site.extent) if self.site.extent else None


class Concept(Thing, _Concept):
    """Modelo dos conceitos do vocabulário controlado."""

    @classmethod
    def from_file(cls, f: Path):
        """Mais validações do id."""
        post = frontmatter.load(str(f))
        if not post.metadata.get("id"):
            post.metadata["id"] = f.stem
        elif post.metadata["id"] != f.stem:
            raise ValueError(
                f"O ID {post.metadata["id"]} não corresponde ao nome do arquivo/ficheiro {f.stem}."
            )
        elif str(post.metadata["id"]).casefold() != post.metadata["id"]:
            raise ValueError(f"O ID {post.metadata["id"]} não está normalizado.")
        return cls.from_post(post)

    def iter_references(self):
        """Percorre (campo, índice, referência) em broader/relation/mapping."""
        for name in CONCEPT_REF_FIELDS:
            for i, ref in enumerate(getattr(self, name) or []):
                yield name, i, ref

    @property
    def broader_ids(self) -> set[str] | None:
        """Conjunto dos ancestrais diretos."""
        if not self.broader:
            return None
        return {ref.refid for ref in self.broader}

    @property
    def relation_ids(self) -> set[str] | None:
        """Conjunto das relações diretas."""
        if not self.relation:
            return None
        return {ref.refid for ref in self.relation if ref}

    @model_validator(mode="after")
    def _validate_concept(self):
        """Valida id e verifica consistência das relações hierárquicas e relacionais."""
        if not self.id:
            raise ValueError("Todo conceito precisa de `id`.")

        seen: dict[str, set[str]] = {}
        for name, i, ref in self.iter_references():
            target = ref.refid
            if not target:
                raise ValueError(f"{name}[{i}] não aponta para nenhum conceito.")
            if name != "mapping" and target == self.id:
                raise ValueError(f"{name}[{i}] aponta para o próprio conceito.")
            if target in seen.setdefault(name, set()):
                raise ValueError(f"{name}[{i}]: {target!r} aparece mais de uma vez.")
            seen[name].add(target)

        overlap = seen.get("broader", set()) & seen.get("relation", set())
        if overlap:
            raise ValueError(
                f"Conceitos em `broader` e `relation` ao mesmo tempo: {sorted(overlap)}"
            )

        broader_preferred_count = 0
        if self.broader:
            for ref in self.broader:
                if ref.broader_preferred:
                    broader_preferred_count += 1
                    if broader_preferred_count > 1:
                        raise ValueError(
                            "Não é permitido ter mais de uma relação com `broader_preferred: true`."
                        )
            if broader_preferred_count == 0:
                raise ValueError(
                    "É obrigatório informar uma relação com `broader_preferred: true`."
                )

        if not self.broader and self.concept_type != "facet":
            raise ValueError(
                "Todos os conceitos que não são nomes de facetas devem ter um ancestral."
            )

        if self.broader and self.concept_type == "facet":
            raise ValueError("Uma faceta não pode ter ancestrais.")

        if self.mapping:
            for concept in self.mapping:
                if concept.refid_type and concept.refid_type == "local":
                    raise ValueError(
                        "Um conceito só pode ser mapeado a conceitos de outros vocabulários.\n"
                        f"Foi atribuído o tipo {concept.refid_type} a {concept.refid}."
                    )
        return self
