"""Acesso ao CLI do Typer (assistente de preenchimento das fichas)
"""

from pathlib import Path
from typing import Annotated

import typer
from pyorcid_checksum import ORCID_Checksum
from rich import print as rprint

from wasth.core import models, valida_yaml

app = typer.Typer()

@app.command()
def orcid(orcid: str) -> str:
    """Recebe, valida e normaliza um ORCiD inserido pelo usuário

    :param orcid: o número do ORCiD ou o URI completo.
    """
    orcid = orcid.strip()
    checker = ORCID_Checksum()
    try:
        valida = checker.check_orcid_checksum(orcid)
    except Exception as e:
        raise typer.BadParameter(f":x:  Erro de validação: {e}.")
    if valida is False:
        raise typer.BadParameter(":x:  ORCiD inválido.")
    return checker.parse_orcid(orcid)

@app.command()
def valida(
    object_class: Annotated[
        str, typer.Argument(
            help="Classe de objeto a ser validado: Work (edificação), \
            Place (lugar) ou Concept (vocabulário)."
        )
    ] = "Work",
    user_path: Annotated[
        str, typer.Argument(
            help="Um caminho, absoluto ou relativo ao diretório atual, \
            para um arquivo/ficheiro ou uma pasta contendo documentos \
            a serem processados. Por padrão é o diretório atual."
        )
    ] = "."
) -> None:
    """Valida as fichas no arquivo/ficheiro ou pasta indicado pelo usuário

    :param user_path: Um caminho de arquivo/ficheiro ou pasta.
    """
    io_paths = models.paths(
        args = [user_path, user_path],
        overwrite=True
    )
    rprint(io_paths)
    for i in io_paths.get('filelist'):
        valida_yaml.f_schema(i, object_class)

@app.command()
def main() -> None:
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
uv run typer src/wasth/cli.py run --help

A qualquer momento, envie CTRL-C para sair sem gravar.
        """)

if __name__ == "__main__":
    app()
