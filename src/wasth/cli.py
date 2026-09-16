"""Acesso ao CLI do Typer (assistente de preenchimento das fichas)
"""

from pathlib import Path
from typing import Annotated

import typer
from pyorcid_checksum import ORCID_Checksum
from rich import print as rprint

from wasth.core import geoprocessa, models, valida_yaml

app = typer.Typer()

@app.command()
def valida(
    object_class: Annotated[
        str, typer.Argument(
            help="Classe de objeto a ser validado: Work (edificação), \
            Place (lugar) ou Concept (vocabulário)."
        )
    ] = "Work",
    files_path: Annotated[
        str, typer.Argument(
            help="Um caminho, absoluto ou relativo ao diretório atual, \
            para um arquivo/ficheiro ou uma pasta contendo documentos \
            a serem processados. Por padrão é o diretório atual."
        )
    ] = "."
) -> None:
    """Valida as fichas no arquivo/ficheiro ou pasta indicado pelo usuário
    (ainda não funcional).

    :param files_path: Um caminho de arquivo/ficheiro ou pasta.
    """
    io_paths = models.paths(
        args = [files_path, files_path],
        overwrite=True
    )
    for i in io_paths.get('filelist'):
        valida_yaml.valida_yaml_schema(i, object_class)

@app.command()
def geojson(
    in_files: Annotated[
        str, typer.Argument(
            help="Um caminho, absoluto ou relativo ao diretório atual, \
            para um arquivo/ficheiro ou uma pasta contendo documentos \
            a serem processados. Por padrão é o diretório atual."
        )
    ] = ".",
    out_file: Annotated[
        str, typer.Argument(
            help="Caminho e nome do arquivo a ser gravado, por padrão \
            ./wasth.geojson."
        )
    ] = "wasth.geojson"
) -> Path | None:
    """Converte fichas em um documento geoJSON que pode ser carregado no QGIS."""
    io_paths = models.paths(
        in_path = Path(in_files),
        out_path = Path(out_file)
    )
    things = []
    filelist = io_paths.get('filelist')
    if not filelist:
        raise OSError("Nenhum conteúdo para ingerir.")
    for i in io_paths.get('filelist'):
        thing = models.Thing.from_file(i)
        location = thing.location()
        if location:
            things.append(thing)
    rprint(f"{len(things)} objetos georreferenciados encontrados.")
    out_path = io_paths.get('output_path')
    geoprocessa.locations(things, out_path)
    if out_path.is_file():
        return out_path
    else:
        rprint(":warning: Nenhum objeto foi gravado!")
        return None

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
    Esta é a tela de acesso à interfaz de processamento das fichas dos
    Documentários de arquitetura tradicional.
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
