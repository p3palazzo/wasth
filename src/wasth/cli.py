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

import typer
from dotenv import dotenv_values, set_key
from rdflib import URIRef
from rich import print as rprint

from .core import geoprocessa, models, valida_yaml
from .core.orcid import orcid_profile, parse_orcid
from .models import Thing

WASTH_ENV = ".wasth.env"

app = typer.Typer(
    help=("""
Interfaz de linha de comando da aplicação
[bold]WASTH[/bold] : Web App para Sítios Tradicionais e Históricos.

Esta aplicação foi concebida para processar as fichas dos Documentários da
Arquitetura Tradicional. O portal do projeto se encontra em
<https://tradicional.arq.br>.
A documentação da estrutura de dados pode ser consutada em
<https://tradicional.arq.br/schema/>.

Digite um dos [bold]Commands[/bold] abaixo para começar ou rode novamente o
comando [bold]wasth[/bold] com uma ou mais dentre as [bold]Options[/bold] abaixo.
"""),
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
def orcid_profile_name(orcid: str | URIRef) -> str | None:
    """Puxa o nome do usuário/utente a partir do número ORCiD informado.

    :params: orcid: o número ORCiD do usuário.
    :returns: Nome da pessoa, ou vazio se o nome do perfil não existir, se
    o número do ORCiD for inválido, ou se a API estiver inacessível.
    :rtype: str | None
    """
    orcid_number = parse_orcid(orcid)
    try:
        profile = orcid_profile(orcid_number)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    return profile.full_name if profile else None


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


# --------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------
def get_dir(label: str, workdir: str | None) -> Path:
    """Seleciona uma pasta existente, pedindo ao usuário se preciso.

    :param label: Rótulo que indica o propósito da pasta.
    :type label: str
    :param workdir: Pasta atual.
    :type workdir: str
    :return: Um caminho para a pasta selecionada.
    :rtype: pathlib.Path
    """


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    orcid: Annotated[
        str | None,
        typer.Option(envvar="WASTH_ORCID", help="Seu número do ORCiD."),
    ] = None,
    works: Annotated[
        str | None,
        typer.Option(
            envvar="WASTH_WORKS_DIR",
            help="Pasta contento as fichas de obras em formato Markdown.",
        ),
    ] = None,
    vocab: Annotated[
        str | None,
        typer.Option(
            envvar="WASTH_VOCAB_DIR",
            help="Pasta contento as fichas de vocabulário controlado em formato Markdown.",
        ),
    ] = None,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            exists=True,
            dir_okay=False,
            help=("""Arquivo/ficheiro de configuração. Se indicado, a
configuração completa é usada sem pedir confirmação (padrão: .wasth.env na
pasta atual, com confirmação)."""),
        ),
    ] = None,
) -> None:
    """
    Interfaz de linha de comando da aplicação
    [bold]WASTH[/bold] : Web App para Sítios Tradicionais e Históricos

    Esta aplicação foi concebida para processar as fichas
    dos Documentários da Arquitetura Tradicional.

    Digite os comandos e as opções abaixo para usar as funcionalidades do WASTH.
    """


if __name__ == "__main__":
    app()
