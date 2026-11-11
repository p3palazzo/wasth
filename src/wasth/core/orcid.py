"""Consulta à API pública do ORCiD.

Espera um número de ORCiD *já normalizado e validado* (``0000-0002-1825-0097``),
isto é, sem prefixo/CURIE e com a checksum conferida (ver ``_parse_orcid``).

Só são retornados dados que o titular marcou como públicos; qualquer campo
pode, portanto, vir vazio (``None`` ou lista vazia).
"""

from __future__ import annotations

import httpx
from pyorcid_checksum import ORCID_Checksum
from rdflib import URIRef

from wasth.models import OrcidRecord

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
    ) as client:
        response = client.get(f"{ORCID_BASE_URL}/{orcid}")

    if response.status_code == 404:
        raise OrcidError(f"Nenhum registro encontrado para ORCiD {orcid}.")
    if response.status_code != 200:
        raise OrcidError(f"O servidor ORCiD respondeu HTTP {response.status_code}.")
    return OrcidRecord.model_validate(response.json())


# -----------------------------------------------------------------------------
# Modelo de erro
# -----------------------------------------------------------------------------
class OrcidError(Exception):
    """Erro genérico na consulta ao ORCID."""
