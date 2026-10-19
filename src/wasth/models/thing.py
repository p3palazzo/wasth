import datetime
from pathlib import Path
from typing import Annotated

import frontmatter
from pydantic import BaseModel, Field, PastDate, field_validator
from pyorcid_checksum import ORCID_Checksum
from rdflib import URIRef
from ruamel.yaml import YAML

from . import dcmi_namespace
from .refs import *

yaml = YAML(typ='safe')

ORCID_CHECKER = ORCID_Checksum()

class Thing(BaseModel):
    """Dados e métodos comuns a todas as classes de objetos do projeto WASTH:
    Work (obras de arquitetura), Place (lugares), e Concept (itens de vocabulário).

    Apresenta dois métodos para criar um objeto:

    1. De um arquivo Markdown, passando por um objeto frontmatter.Post;
    2. De dados já estruturados pelo frontmatter.Post.

    A inicialização do objeto valida os dados inseridos.
    """
    id: Annotated[str, Field(frozen=True)]
    author: Annotated[str, Field(frozen=True)]
    date: PastDate = Field(default_factory=datetime.date.today, frozen=True)
    # category: Concept
    title: str
    title_type: dcmi_namespace.TITLE_TYPE
    title_source: list[BibliographicCitation] | None = None
    titles: list[LIDOAppellationTitle] | None = None
    description: str
    bibliographic_citation: list[BibliographicCitation] | None = None
    identifiers: list[XRef] | None = None # LIDOPublishedID
    temporal: list[LIDOEvent] | None = None
    collection: list[dict] | None = None
    repository: list[LIDORepository] | None = None
    record_rights: list[LIDORights] | None = None
    content: str | None = None

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

    @field_validator("author", mode="before")
    @classmethod
    def validate_orcid(cls, value: str | URIRef) -> str:
        """Return a bare, validated ORCID iD using PyORCID-checker."""
        orcid = str(value)
        if ORCID_CHECKER.check_orcid_checksum(orcid) is False:
            raise ValueError(f"ORCID iD inválido: {value!r}")
        return ORCID_CHECKER.parse_orcid(orcid)
