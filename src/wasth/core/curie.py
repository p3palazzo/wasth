"""Fornece validação e processamento de CURIEs nas fichas."""

import re

import curies
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import linkml_meta

prefix_dict = linkml_meta["prefixes"]
prefix_map = {
    prefix: value["prefix_reference"] for prefix, value in prefix_dict.items()
}
curie_converter = curies.load_prefix_map(prefix_map)

CURIE_RE = re.compile(
    "^(?:(?P<prefix>[A-Za-z_][A-Za-z0-9\\.\\-_]*)?:)?(?P<identifier>(/[^\\s/][^\\s]*|[^\\s/][^\\s]*|[^\\s]?))$"
)


def validate_curie(pat: str) -> str | None:
    # https://gist.github.com/niklasl/2506955
    # https://curies.readthedocs.io/en/stable/api/curies.w3c.CURIE_RE.html
    if CURIE_RE.match(pat):
        return pat
    return None
