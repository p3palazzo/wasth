"""Ponto de entrada do aplicativo `wasth`.

Configuração (ORCiD, pasta de Works, pasta de Concepts) é lida, em ordem
de prioridade, de:

1. opções de linha de comando (``--orcid``, ``--works``, ``--concepts``);
2. variáveis de ambiente (``WASTH_ORCID``, ``WASTH_WORKS_DIR``,
   ``WASTH_CONCEPTS_DIR``);
3. arquivo ``.wasth.env`` na pasta onde o comando é executado.

Dependências: typer, rich, python-dotenv, httpx
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import httpx
import typer
from dotenv import dotenv_values, set_key
from rich import print as rprint

from .core import geoprocessa, models, valida_yaml
from .core.orcid import parse_orcid
from .models import Thing

WASTH_ENV = ".wasth.env"
API_ORCID = "https://pub.orcid.org/v3.0/{orcid}/person"

app = typer.Typer(
    help="WASTH — Web App para Sítios Tradicionais e Históricos",
    no_args_is_help=True,
)


@dataclass
class Config:
    """Configuração da sessão, disponível em `ctx.obj`."""

    orcid: str
    profile_name: str
    works: Path
    concepts: Path


# --------------------------------------------------------------------------
# ORCiD
# --------------------------------------------------------------------------


@app.command()
def valida(
    object_class: Annotated[
        str, typer.Argument(help="Classe de objeto a ser validado: Work (edificação), \
            Place (lugar) ou Concept (vocabulário).")
    ] = "Work",
    files_path: Annotated[
        str, typer.Argument(help="Um caminho, absoluto ou relativo ao diretório atual, \
            para um arquivo/ficheiro ou uma pasta contendo documentos \
            a serem processados. Por padrão é o diretório atual.")
    ] = ".",
) -> None:
    """Valida as fichas no arquivo/ficheiro ou pasta indicado pelo usuário
    (ainda não funcional).

    :param files_path: Um caminho de arquivo/ficheiro ou pasta.
    """
    io_paths = models.paths(args=[files_path, files_path], overwrite=True)
    for i in io_paths.get("filelist"):
        valida_yaml.valida_yaml_schema(i, object_class)


@app.command()
def geojson(
    in_files: Annotated[
        str, typer.Argument(help="Um caminho, absoluto ou relativo ao diretório atual, \
            para um arquivo/ficheiro ou uma pasta contendo documentos \
            a serem processados. Por padrão é o diretório atual.")
    ] = ".",
    out_file: Annotated[
        str, typer.Argument(help="Caminho e nome do arquivo a ser gravado, por padrão \
            ./wasth.geojson.")
    ] = "wasth.geojson",
) -> Path | None:
    """Converte fichas em um documento geoJSON que pode ser carregado no QGIS."""
    io_paths = models.paths(in_path=Path(in_files), out_path=Path(out_file))
    things = []
    filelist = io_paths.get("filelist")
    if not filelist:
        raise OSError("Nenhum conteúdo para ingerir.")
    for i in io_paths.get("filelist"):
        thing = Thing.from_file(i)
        location = thing.location()
        if location:
            things.append(thing)
    rprint(f"{len(things)} objetos georreferenciados encontrados.")
    out_path = io_paths.get("output_path")
    geoprocessa.locations(things, out_path)
    if out_path.is_file():
        return out_path
    else:
        rprint(":warning: Nenhum objeto foi gravado!")
        return None


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
     Interfaz de linha de comando da aplicação
     [bold]WASTH[/bold] : Web App para Sítios Tradicionais e Históricos

    Esta aplicação foi concebida para processar as fichas
    dos Documentários da Arquitetura Tradicional.

    Digite os comandos e as opções abaixo para usar as funcionalidades do WASTH.
    """
    rprint("""
-------------------------------------------------------
 Interfaz de linha de comando da aplicação
 [bold]WASTH[/bold] : Web App para Sítios Tradicionais e Históricos
-------------------------------------------------------

Esta aplicação foi concebida para processar as fichas
dos Documentários da Arquitetura Tradicional.
O site do projeto se encontra em
<https://tradicional.arq.br>.

Para instruções, digitar o comando:
uv run wasth --help
        """)


if __name__ == "__main__":
    app()
