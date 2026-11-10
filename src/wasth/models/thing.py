import datetime
from collections.abc import Iterator
from pathlib import Path

import frontmatter
import geojson
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import (GeographicExtent,
                                                              GeographicPoint,
                                                              Site)
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Thing as _Thing
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Work as _Work
from geojson import utils as geojson_utils
from openlocationcode import openlocationcode
from pydantic import field_validator, model_validator
from pyorcid_checksum import ORCID_Checksum
from rdflib import URIRef
from ruamel.yaml import YAML

yaml = YAML(typ='rt')

def _parse_orcid(orcid: str | URIRef) -> str:
    """Retorna o número do ORCiD para conferência na API

    :params: Aceita o número do ORCiD, o link completo ou a CURIE na forma
    `orcid:1234-5678-901X`.
    :returns: Retorna o número simples do ORCiD validado para a checksum, sem
    verificar a sua existência na API.
    :rtype: str
    """
    ORCID_CHECKER = ORCID_Checksum()
    ORCID_PREFIXES = ("orcid:", "https://orcid.org/", "http://orcid.org/")

    text = str(orcid).strip()
    if not text:
        raise ValueError("ORCiD inexistente.")
    for prefix in ORCID_PREFIXES:
        if text.lower().startswith(prefix):
            orcid_number = text[len(prefix):]
        else:
            orcid_number = text

    if ORCID_CHECKER.check_orcid_checksum(orcid_number) is False:
        raise ValueError(f"ORCID iD inválido: {orcid_number!r}")
    return ORCID_CHECKER.parse_orcid(orcid_number)

_SITE_FIELDS = ("site", "former_site", "intended_site", "other_site")

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
    def from_file(cls, f: Path) -> "Thing":
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
    def from_post(cls, post: frontmatter.Post) -> "Thing":
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
            value: list[str | URIRef] | str | URIRef
    ) -> str | list[str]:
        """Return a bare, validated ORCID iD using PyORCID-checker."""
        if value is None:
            return value
        if isinstance(value, (list)):
            return [ _parse_orcid(v) for v in value ]
        else:
            return _parse_orcid(value)

    @field_validator("record_date", mode="before")
    def validate_record_date(cls, value: datetime.date | None) -> datetime.date | None:
        if value is None:
            return datetime.date.today()
        if value <= datetime.date.today():
            return value
        if value > datetime.date.today():
            raise ValueError(f"A data da ficha {value} não pode ser uma data futura.")

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
        for name in _SITE_FIELDS:
            value = getattr(self, name, None)
            if value is None:
                continue
            sites = value if isinstance(value, list) else [value]
            for i, site in enumerate(sites):
                yield name, i, site

    @model_validator(mode="after")
    def _validate_site_points(self):
        """Valida coordenadas da locação."""
        for name, i, site in self._iter_sites():
            if site.location is not None and site_location(site.location) is None:
                raise ValueError(f"Coordenadas inválidas em {name}[{i}].location")
        return self

    @property
    def site_location(self) -> geojson.Point | None:
        return site_location(self.site.location) if self.site.location else None

    @property
    def site_extent(self) -> geojson.Polygon | geojson.MultiPolygon | None:
        return site_extent(self.site.extent) if self.site.extent else None

    def olc_id(self) -> str | None:
        """
        Processa entradas de georreferenciamento

        Gera ID no formato Open Location Code a partir da latitude e longitude
        inseridas na ficha ou na interface.
        """
        location = self.location()
        if not isinstance(location, geojson.Point):
            return None
        (lon, lat) = geojson_utils.coords(location)
        if lat is None or lon is None:
            return None
        return openlocationcode.encode(lat, lon, 11)
