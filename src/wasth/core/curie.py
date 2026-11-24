"""Fornece validação e processamento de CURIEs nas fichas."""

from functools import cache

from arqtrad_schema.datamodel import MAIN_SCHEMA_PATH
from arqtrad_schema.datamodel.arqtrad_schema_pydantic import linkml_meta
from curies import Converter
from curies.api import ExpansionError
from linkml_runtime import SchemaView
from rdflib import URIRef


# --------------------------------------------------------------------------------------------------
# Cached schema views
# --------------------------------------------------------------------------------------------------
@cache
def schema_view() -> SchemaView:
    return SchemaView(str(MAIN_SCHEMA_PATH))


@cache
def curie_fields() -> dict[str, tuple[str, ...]]:
    """Map class name -> data keys whose value is a uriorcurie."""
    sv = schema_view()
    result: dict[str, tuple[str, ...]] = {}
    for cname in sv.all_classes():
        names = []
        for slot in sv.class_induced_slots(cname):
            rng = slot.range
            # Direct range or any custom type derived from uriorcurie.
            if rng in sv.all_types() and "uriorcurie" in sv.type_ancestors(rng):
                names.append(slot.alias or slot.name)  # alias = key used in data
        if names:
            result[cname] = tuple(names)
    return result


# --------------------------------------------------------------------------------------------------
# Utility functions
# --------------------------------------------------------------------------------------------------
def make_converter(prefixes=linkml_meta["prefixes"]) -> Converter:
    prefix_map = {p["prefix_prefix"]: p["prefix_reference"] for p in prefixes.values()}
    return Converter.from_prefix_map(prefix_map)


def expand_curie(uri_or_curie: str) -> URIRef:
    # https://curies.readthedocs.io/en/stable/api/curies.Converter.html
    try:
        curie_converter = make_converter()
        expanded = curie_converter.expand_or_standardize(uri_or_curie, strict=True)
        return URIRef(expanded)
    except ExpansionError as e:
        raise ExpansionError(
            f"Não foi possível processar o valor {uri_or_curie!r}:\n {e}"
        ) from e


def expand_all_curies(obj: dict, cname: str) -> dict[str, URIRef]:
    fields = curie_fields().get(cname, ())
    for key in fields:
        v = obj.get(key)
        if isinstance(v, str):
            obj[key] = expand_curie(v)
        elif isinstance(v, list):
            obj[key] = [expand_curie(i) if isinstance(i, str) else i for i in v]
    return obj
