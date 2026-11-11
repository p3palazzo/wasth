import datetime
import sys
from collections.abc import Iterator
from pathlib import Path

import frontmatter
import geojson
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import \
    Concept as _Concept
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import (GeographicExtent,
                                                              GeographicPoint,
                                                              Site)
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Thing as _Thing
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Work as _Work
from openlocationcode import openlocationcode
from pydantic import field_validator, model_validator
from pyorcid_checksum import ORCID_Checksum
from rdflib import URIRef
from ruamel.yaml import YAML

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

yaml = YAML(typ='rt')


ORCID_CHECKER = ORCID_Checksum()
ORCID_PREFIXES = ("orcid:", "https://orcid.org/", "http://orcid.org/")
SITE_FIELDS = ("site", "former_site", "intended_site", "other_site")
CONCEPT_REF_FIELDS = ("broader", "narrower", "relation", "mapping")
 

def _parse_orcid(orcid: str | URIRef) -> str:
    """Retorna o número do ORCiD para conferência na API

    :params: Aceita o número do ORCiD, o link completo ou a CURIE na forma
    `orcid:1234-5678-901X`.
    :returns: Retorna o número simples do ORCiD validado para a checksum, sem
    verificar a sua existência na API.
    :rtype: str
    """

    orcid_number = str(orcid).strip()
    if not orcid_number:
        raise ValueError("ORCiD inexistente.")
    for prefix in ORCID_PREFIXES:
        if orcid_number.lower().startswith(prefix):
            orcid_number = orcid_number[len(prefix):]
            break
    orcid_number = orcid_number.strip("/ ").upper()

    if not ORCID_CHECKER.check_orcid_checksum(orcid_number):
        raise ValueError(f"ORCID iD inválido: {orcid_number!r}")
    return ORCID_CHECKER.parse_orcid(orcid_number)

def site_location(location: GeographicPoint | None) -> geojson.Point | None:
    """Ponto GeoJSON (lon, lat[, alt]) a partir das coordenadas."""
    if location is None:
        return None
    coords = (location.lon, location.lat)
    if location.alt is not None:
        coords += (location.alt,)
    p = geojson.Point(coords)
    return p if p.is_valid else None

def site_extent(
        extent: GeographicExtent | None
    ) -> geojson.Polygon | geojson.MultiPolygon | None:
    """Polígono(s) de implantação a partir das coordenadas."""
    if extent is None:
        return None
    coords = extent.coordinates
    match extent.geometry_type:
        case "Polygon":
            footprint = geojson.Polygon(coords)
        case "MultiPolygon":
            footprint = geojson.MultiPolygon(coords)
        case _:
            footprint = geojson.Polygon(coords)
    return footprint if footprint.is_valid else None


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
        :return: Um objeto em forma de dicionário que pode ser convertido, no todo ou em parte, para vários outros tipos de objetos ou reexportado para Markdown.
        :rtype: Thing
        """
        data = post.metadata.copy()
        data["content"] = post.content
        return cls.model_validate(data)

    @field_validator("author", "authors", mode="before")
    @classmethod
    def validate_orcid(
            cls,
            value: list[str | URIRef] | str | URIRef | None
    ) -> str | list[str] | None:
        """Return a bare, validated ORCID iD using PyORCID-checker."""
        if value is None:
            return value
        if isinstance(value, (list, tuple)):
            return [ _parse_orcid(v) for v in value ]
        return _parse_orcid(value)

    @field_validator("record_date", mode="after")
    def validate_record_date(
            cls,
            value: datetime.date | None
    ) -> datetime.date | None:
        today = datetime.date.today()
        if value is None:
            return today
        if value > today:
            raise ValueError(f"A data da ficha {value} não pode ser uma data futura.")
        return value

    @model_validator(mode="after")
    def exactly_one_author_field(self):
        has_author = self.author is not None
        has_authors = bool(self.authors)   # empty list counts as absent
        if has_author == has_authors:
            raise ValueError("Informe exatamente um entre `author` e `authors`")
        return self

class Work(Thing, _Work):
    """Arcabouço dos dados e métodos das fichas de obras.
    """

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
        """
        Processa entradas de georreferenciamento

        :params: Aceita a propriedade site_location do objeto Work
        :returns: Gera ID no formato Open Location Code a partir da latitude e
        longitude inseridas na ficha ou na interface.
        :rtype: str
        """
        loc = self.site_location
        if not loc:
            return None
        if loc.lat is None or loc.lon is None:
            return None
        return openlocationcode.encode(loc.lat, loc.lon, 11)

    @model_validator(mode="after")
    def _validate_site_geometry(self):
        """Valida coordenadas da locação e da implantação."""
        for name, i, site in self._iter_sites():
            if site.location is not None and site_location(site.location) is None:
                raise ValueError(f"Coordenadas inválidas em {name}[{i}].location")
            if site.extent is not None and site_extent(site.extent) is None:
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
        return site_location(self.site.location) if self.site.location else None

    @property
    def site_extent(self) -> geojson.Polygon | geojson.MultiPolygon | None:
        return site_extent(self.site.extent) if self.site.extent else None



def ref_id(ref) -> str | None:
    """`id` do conceito alvo de uma referência.
 
    Aceita tanto `concept_name` como objeto Concept (esquema atual, `inlined:
    true`) quanto como string (se o esquema passar a `inlined: false`).
    """
    target = ref.concept_name
    return target if isinstance(target, str) else getattr(target, "id", None)
 

class Concept(Thing, _Concept):
    """Modelo dos conceitos do vocabulário controlado."""
    @classmethod
    def from_post(cls, post):
        if post.metadata.get("narrower"):
            raise ValueError("`narrower` é derivado de `broader`; não preencher.")
        return super().from_post(post)

    @classmethod
    def from_file(cls, f: Path):
        post = frontmatter.load(f)
        if not post.metadata.get("id"):
            post.metadata["id"] = Path(f).stem
        return cls.from_post(post)

    def iter_references(self):
        """Percorre (campo, índice, referência) em broader/narrower/relation/mapping."""
        for name in CONCEPT_REF_FIELDS:
            for i, ref in enumerate(getattr(self, name) or []):
                yield name, i, ref
 
    @property
    def broader_ids(self) -> set[str | None]:
        return {ref_id(r) for r in self.broader or [] if ref_id(r)}
 
    @property
    def relation_ids(self) -> set[str | None]:
        return {ref_id(r) for r in self.relation or [] if ref_id(r)}

    @model_validator(mode="before")
    @classmethod
    def _stubs_from_ids(cls, data):
        if not isinstance(data, dict):
            return data
        data = dict(data)
        for name in ("broader", "narrower", "relation", "mapping"):
            data[name] = [
                {**r, "concept_name": {"id": r["concept_name"]}}
                if isinstance(r, dict) and isinstance(r.get("concept_name"), str)
                else r
                for r in data.get(name) or []
            ] or data.get(name)
        return data
 
    @model_validator(mode="after")
    def _validate_concept(self):
        if not self.id:
            raise ValueError("Todo conceito precisa de `id`.")
 
        seen: dict[str, set[str]] = {}
        for name, i, ref in self.iter_references():
            target = ref_id(ref)
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
        return self
