"""Consulta à API pública do ORCID (https://pub.orcid.org/v3.0).

Espera um número de ORCiD *já normalizado e validado* (``0000-0002-1825-0097``),
isto é, sem prefixo/CURIE e com a checksum conferida (ver ``_parse_orcid``).

Só são retornados dados que o titular marcou como públicos; qualquer campo
pode, portanto, vir vazio (``None`` ou lista vazia).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import requests

ORCID_API_BASE = "https://pub.orcid.org/v3.0"
DEFAULT_TIMEOUT = 10  # segundos
USER_AGENT = "arqtrad-wasth/0.1 (ORCID lookup)"  # ajuste com um contato real

_ORCID_RE = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


class OrcidError(Exception):
    """Erro genérico na consulta ao ORCID."""


class OrcidNotFound(OrcidError):
    """O iD é válido na checksum mas não existe no registro."""


class OrcidUnavailable(OrcidError):
    """Falha de rede, limite de requisições ou erro do servidor."""


@dataclass(frozen=True)
class Affiliation:
    organization: str | None = None
    department: str | None = None
    role: str | None = None
    city: str | None = None
    country: str | None = None
    start: str | None = None  # AAAA[-MM[-DD]]
    end: str | None = None


@dataclass(frozen=True)
class OrcidProfile:
    orcid: str
    given_names: str | None = None
    family_name: str | None = None
    credit_name: str | None = None
    other_names: tuple[str, ...] = ()
    biography: str | None = None
    country: str | None = None
    keywords: tuple[str, ...] = ()
    researcher_urls: tuple[tuple[str | None, str], ...] = ()  # (rótulo, url)
    external_ids: tuple[tuple[str, str], ...] = ()  # (tipo, valor)
    employments: tuple[Affiliation, ...] = field(default=())

    @property
    def uri(self) -> str:
        return f"https://orcid.org/{self.orcid}"

    @property
    def full_name(self) -> str | None:
        parts = [p for p in (self.given_names, self.family_name) if p]
        return " ".join(parts) or None

    @property
    def display_name(self) -> str | None:
        """Nome de crédito, se houver; senão nome completo."""
        return self.credit_name or self.full_name


# ---------------------------------------------------------------- helpers

def _get(node: Any, *path: str | int) -> Any:
    """Navega num JSON aninhado; devolve None se qualquer elo faltar/for null."""
    for key in path:
        if node is None:
            return None
        try:
            node = node[key]
        except (KeyError, IndexError, TypeError):
            return None
    return node


def _value(node: Any, *path: str | int) -> str | None:
    """Como _get, mas extrai o campo ``value`` dos objetos do ORCID."""
    return _get(node, *path, "value")


def _fmt_date(date: dict | None) -> str | None:
    if not date:
        return None
    parts = [_value(date, k) for k in ("year", "month", "day")]
    return "-".join(p for p in parts if p) or None


def _items(node: Any, *path: str | int) -> list:
    return _get(node, *path) or []


def _parse_affiliation(summary: dict) -> Affiliation:
    return Affiliation(
        organization=_get(summary, "organization", "name"),
        department=_get(summary, "department-name"),
        role=_get(summary, "role-title"),
        city=_get(summary, "organization", "address", "city"),
        country=_get(summary, "organization", "address", "country"),
        start=_fmt_date(_get(summary, "start-date")),
        end=_fmt_date(_get(summary, "end-date")),
    )


def _parse_record(orcid: str, record: dict) -> OrcidProfile:
    person = _get(record, "person") or {}

    employments = tuple(
        _parse_affiliation(s["employment-summary"])
        for group in _items(record, "activities-summary", "employments",
                            "affiliation-group")
        for s in group.get("summaries", [])
        if s.get("employment-summary")
    )

    return OrcidProfile(
        orcid=orcid,
        given_names=_value(person, "name", "given-names"),
        family_name=_value(person, "name", "family-name"),
        credit_name=_value(person, "name", "credit-name"),
        other_names=tuple(
            n["content"] for n in _items(person, "other-names", "other-name")
            if n.get("content")
        ),
        biography=_get(person, "biography", "content"),
        country=_value(person, "addresses", "address", 0, "country"),
        keywords=tuple(
            k["content"] for k in _items(person, "keywords", "keyword")
            if k.get("content")
        ),
        researcher_urls=tuple(
            (u.get("url-name"), _value(u, "url"))
            for u in _items(person, "researcher-urls", "researcher-url")
            if _value(u, "url")
        ),
        external_ids=tuple(
            (x["external-id-type"], x["external-id-value"])
            for x in _items(person, "external-identifiers",
                            "external-identifier")
            if x.get("external-id-type") and x.get("external-id-value")
        ),
        employments=employments,
    )


# ------------------------------------------------------------- public API

def fetch_orcid_profile(
    orcid: str,
    *,
    session: requests.Session | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> OrcidProfile:
    """Consulta a API pública do ORCID e devolve os dados públicos do titular.

    :param orcid: Número simples, ex.: ``0000-0002-1825-0097`` (sem prefixo).
    :param session: ``requests.Session`` opcional (reuso de conexão, testes).
    :raises ValueError: se o formato não for o de um ORCiD.
    :raises OrcidNotFound: se o iD não existir no registro.
    :raises OrcidUnavailable: em falha de rede, 429 ou 5xx.
    :raises OrcidError: para iD desativado/bloqueado (HTTP 409) ou resposta
        inesperada.
    """
    if not _ORCID_RE.fullmatch(orcid):
        # Também protege a montagem da URL contra entradas inesperadas.
        raise ValueError(f"Formato de ORCiD inválido: {orcid!r}")

    http = session or requests
    try:
        resp = http.get(
            f"{ORCID_API_BASE}/{orcid}/record",
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise OrcidUnavailable(f"Falha ao contatar o ORCID: {exc}") from exc

    if resp.status_code == 404:
        raise OrcidNotFound(f"ORCiD {orcid} não encontrado.")
    if resp.status_code == 409:
        raise OrcidError(f"ORCiD {orcid} está desativado ou bloqueado.")
    if resp.status_code == 429 or resp.status_code >= 500:
        raise OrcidUnavailable(f"ORCID respondeu HTTP {resp.status_code}.")
    if not resp.ok:
        raise OrcidError(f"ORCID respondeu HTTP {resp.status_code}.")

    try:
        record = resp.json()
    except ValueError as exc:
        raise OrcidError("Resposta do ORCID não é JSON válido.") from exc

    return _parse_record(orcid, record)
