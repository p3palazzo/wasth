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
    """Gera o SchemaView do LinkML para encontrar os slots a partir do seu range."""
    return SchemaView(str(MAIN_SCHEMA_PATH))


@cache
def curie_fields() -> dict[str, tuple[str, ...]]:
    """Mapa dos slots que recebem valores de URI ou CURIE em cada classe.

    :return: Dicionário indexado por Classe, contendo tuples com nomes de slots.
    :rtype: dict[str, tuple[str, ...]]
    """
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
    """Inicializa o conversor de CURIEs.

    :param prefixes: Dicionário com os prefixos cadastrados, por padrão vindo do esquema LinkML.
    :return: Objeto conversor de CURIEs.
    :rtype: curies.Converter
    """
    prefix_map = {p["prefix_prefix"]: p["prefix_reference"] for p in prefixes.values()}
    return Converter.from_prefix_map(prefix_map)


def expand_curie(uri_or_curie: str) -> URIRef | str:
    """Produz uma URI a partir de um CURIE, ou normaliza a URI recebida.
    Retorna identificadores locais sem alteração.

    :param uri_or_curie: CURIE ou URI de uma referência.
    :return: Uma URI normalizada, não testando sua existência.
    :rtype: RDFLib.URIRef
    """
    # https://curies.readthedocs.io/en/stable/api/curies.Converter.html
    curie_converter = make_converter()
    if ":" not in uri_or_curie:
        return uri_or_curie
    try:
        expanded = curie_converter.expand_or_standardize(uri_or_curie, strict=True)
        return URIRef(expanded)
    except ExpansionError as e:
        raise ExpansionError(
            f"Não foi possível processar o valor {uri_or_curie!r}:\n {e}"
        ) from e


def expand_all_curies(obj: dict, cname: str) -> dict[str, URIRef]:
    """Processa todos os CURIEs ou URIs recebidos de um modelo.

    :param obj: Um dicionário com os valores que pedem CURIEs ou URIs nos modelos.
    :param cname: O nome da classe do modelo ao qual os valores pertencem.
    :return: O modelo com os CURIEs expandidos para URIs normalizadas.
    :rtype: dict[str, RDFLib.URIRef]
    """
    fields = curie_fields().get(cname, ())
    for key in fields:
        v = obj.get(key)
        if isinstance(v, str):
            obj[key] = expand_curie(v)
        elif isinstance(v, list):
            obj[key] = [expand_curie(i) if isinstance(i, str) else i for i in v]
    return obj
