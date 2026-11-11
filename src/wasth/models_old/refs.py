import datetime
from typing import Literal, NotRequired, Required, TypedDict

from pydantic import BaseModel, HttpUrl, PastDate, model_validator

from wasth.models import dcmi_namespace, rdf_namespace

from .place import Place
from .thing import Thing


class LIDORepository(BaseModel):
    """Definição de um repositório (continente jurídico) nas fichas de obra"""
    type: Literal[dcmi_namespace.REPO_TYPE] = 'corporate'
    name: Thing
    part_of: LIDORepository | None = None

class LIDORights(BaseModel):
    """Expressão de direitos autorais conforme LIDO."""
    rights_type: Literal['generic', 'specific'] = 'generic'
    holder: LIDORepository
    concept: XRef
    temporal: Temporal

class XRef(TypedDict, total=False):
    refid: Required[HttpUrl]
    display: str
    source: list[XRef | BibliographicCitation]

class BibliographicCitation(TypedDict, total=False):
    """Referência bibliográfica ou fonte documental nas fichas de obra

    Nomenclatura e formatação baseada no DCMI bibliographicCitation.
    """
    refid: Required[str]
    display: str
    note: str
    part_of: BibliographicCitation
    source: LIDORepository

class Spatial(TypedDict, total=False):
    site: Required[Place]
    former_site: list[Place]
    intended_site: list[Place]
    other_site: list[Place]

class LIDOEvent(TypedDict, total=False):
    type: Required[str]
    title: Required[str]
    description: str
    display_date: str
    start_date: Temporal
    end_date: Temporal
    data_date: datetime.date
    data_author: str
    source: list[BibliographicCitation]
    place: list[Place]
    role: list[Role]

class Role(TypedDict, total=False):
    pass

class Temporal(BaseModel):
    """Expressão de datas conforme LIDO

    Contém earliest_date, latest_date, date_type, etc.
    """
    earliest_date: PastDate | None = None
    latest_date: datetime.date | None = None
    display_date: str | None = None
    exact: bool = True

    @model_validator(mode="after")
    def require_at_least_one_date(self) -> Temporal:
        if self.earliest_date is None and self.latest_date is None:
            raise ValueError("At least one of 'earliest_date' or 'latest_date' must be provided.")
        return self

class LIDOAppellation(TypedDict):
    """Nomes alternativos para uma coisa"""
    display: str
    source: NotRequired[list[BibliographicCitation]]

class LIDOAppellationTitle(LIDOAppellation):
    type: dcmi_namespace.TITLE_TYPE

class LIDOAppellationActor(LIDOAppellation):
    type: dcmi_namespace.ACTOR_TYPE

class LIDORelation(TypedDict, total=False):
    """Mapeia relações do objeto com objetos externos."""
    name: Required[XRef]
    display: str
    source: list[BibliographicCitation]

class SKOSRelation(LIDORelation):
    match: rdf_namespace.RELATION_TERMS

class SKOSHierarchy(LIDORelation):
    match: rdf_namespace.BROADER_TERMS
