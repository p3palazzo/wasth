"""Consulta à API pública do ORCiD.

Espera um número de ORCiD *já normalizado e validado* (``0000-0002-1825-0097``),
isto é, sem prefixo/CURIE e com a checksum conferida (ver ``_parse_orcid``).

Só são retornados dados que o titular marcou como públicos; qualquer campo
pode, portanto, vir vazio (``None`` ou lista vazia).
"""

from __future__ import annotations

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pyorcid_checksum import ORCID_Checksum
from rdflib import URIRef

ORCID_BASE_URL = "https://orcid.org"
USER_AGENT = "WASTH/0.6.0 (mailto:doc.mod@unb.br)"
DEFAULT_TIMEOUT = 10.0  # segundos

ORCID_CHECKER = ORCID_Checksum()
ORCID_PREFIXES = ("orcid:", "https://orcid.org/", "http://orcid.org/")


# --------------------------------------------------------------------------
# Checksum e recuperação do perfil.
# --------------------------------------------------------------------------
def parse_orcid(orcid: str | URIRef) -> str:
    """Retorna o número do ORCiD para conferência na API

    :param orcid: Aceita o número do ORCiD, o link completo ou a CURIE na forma
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
            orcid_number = orcid_number[len(prefix) :]
            break
    orcid_number = orcid_number.strip("/ ").upper()

    if not ORCID_CHECKER.check_orcid_checksum(orcid_number):
        raise ValueError(f"ORCID iD inválido: {orcid_number!r}")
    return ORCID_CHECKER.parse_orcid(orcid_number)


def orcid_profile(
    orcid: str,
    timeout: float = DEFAULT_TIMEOUT,
    transport: httpx.BaseTransport | None = None,
) -> OrcidRecord | None:
    """Retorna True se existir um registro ORCID público para o iD informado."""

    with httpx.Client(
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        timeout=timeout,
        transport=transport,
        follow_redirects=True,
    ) as client:
        response = client.get(f"{ORCID_BASE_URL}/{orcid}")

    if response.status_code == 404:
        raise ValueError(f"Nenhum registro encontrado para ORCiD {orcid}.")
    if response.status_code != 200:
        raise ValueError(f"O servidor ORCiD respondeu HTTP {response.status_code}.")
    return OrcidRecord.model_validate(response.json())


# -----------------------------------------------------------------------------
# ORCiD models
# -----------------------------------------------------------------------------
class OrcidIdentifier(BaseModel):
    """Modela o identificador ORCiD retornado pela consulta pública."""

    model_config = ConfigDict(populate_by_name=True)

    orcid: str = Field(alias="path")
    uri: str | None = None
    host: str | None = None


class OrcidName(BaseModel):
    """Modela o nome da pessoa com base nos dados do ORCiD."""

    model_config = ConfigDict(populate_by_name=True)

    given_names: str | None = Field(default=None, alias="given-names")
    family_name: str | None = Field(default=None, alias="family-name")
    credit_name: str | None = Field(default=None, alias="credit-name")

    @field_validator(
        "given_names",
        "family_name",
        "credit_name",
        mode="before",
    )
    @classmethod
    def unwrap_orcid_value(cls, value: object) -> object:
        if isinstance(value, dict):
            return value.get("value")
        return value


class OrcidBiography(BaseModel):
    """Modela a bio da pessoa com base nos dados do ORCiD."""

    model_config = ConfigDict(populate_by_name=True)

    content: str | None = None


class OrcidPerson(BaseModel):
    """Modela uma pessoa com base nos dados da consulta pública ao ORCiD."""

    model_config = ConfigDict(populate_by_name=True)

    name: OrcidName | None = None
    biography: OrcidBiography | None = None


class OrcidRecord(BaseModel):
    """Modela o registro ORCiD retornado pela consulta pública."""

    model_config = ConfigDict(populate_by_name=True)

    orcid_identifier: OrcidIdentifier = Field(alias="orcid-identifier")
    person: OrcidPerson | None = None

    def _name(self) -> OrcidName | None:
        person = self.person
        return person.name if person is not None else None

    @property
    def orcid(self) -> str:
        return self.orcid_identifier.orcid

    @property
    def uri(self) -> str:
        return f"https://orcid.org/{self.orcid}"

    @property
    def credit_name(self) -> str | None:
        name = self._name()
        return name.credit_name if name is not None else None

    @property
    def given_names(self) -> str | None:
        name = self._name()
        return name.given_names if name is not None else None

    @property
    def family_name(self) -> str | None:
        name = self._name()
        return name.family_name if name is not None else None

    @property
    def biography(self) -> str | None:
        return (
            self.person.biography.content
            if self.person and self.person.biography
            else None
        )

    @property
    def full_name(self) -> str | None:
        parts = [part for part in (self.given_names, self.family_name) if part]
        return " ".join(parts) or None

    @property
    def display_name(self) -> str | None:
        return self.credit_name or self.full_name
