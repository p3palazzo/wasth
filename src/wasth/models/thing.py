import datetime
from pathlib import Path
from typing import Annotated

import frontmatter
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import Thing as _Thing
from pydantic import Field, PastDate, field_validator
from pyorcid_checksum import ORCID_Checksum
from rdflib import URIRef
from ruamel.yaml import YAML

from . import dcmi_namespace
from .refs import *

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

class Thing(_Thing):
    """Dados e métodos comuns a todas as classes de objetos do projeto WASTH:
    Work (obras de arquitetura), Place (lugares), e Concept (itens de vocabulário).

    Apresenta dois métodos para criar um objeto:

    1. De um arquivo Markdown, passando por um objeto frontmatter.Post;
    2. De dados já estruturados pelo frontmatter.Post.

    A inicialização do objeto valida os dados inseridos.
    """
    record_date: datetime.date = Field(default_factory=datetime.date.today, le=datetime.date.today(), frozen=True)

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

    @model_validator(mode="after")
    def exactly_one_author_field(self):
        has_author = self.author is not None
        has_authors = bool(self.authors)   # empty list counts as absent
        if has_author == has_authors:
            raise ValueError("Informe exatamente um entre `author` e `authors`")
        return self
