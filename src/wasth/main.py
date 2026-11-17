"""Ponto de entrada do WASTH: Web App para Sítios Tradicionais e Históricos"""

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .cli.configure import app as configure_app
from .cli.settings import app_dir_config, load_settings

app = typer.Typer()


@app.callback(invoke_without_command=True, no_args_is_help=True)
def entrypoint(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(help="Informa o número da versão e encerra."),
    ] = False,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=True,
            file_okay=False,
            resolve_path=True,
            readable=True,
            dir_okay=False,
            help="Arquivo/ficheiro de configuração existente ou a criar.",
        ),
    ] = None,
):
    """Interfaz de linha de comando da aplicação
    [b]WASTH: Web App para Sítios Tradicionais e Históricos[/b].

    Esta aplicação foi concebida para processar as fichas dos Documentários da
    Arquitetura Tradicional.
    O portal do projeto se encontra em <https://tradicional.arq.br>.
    A documentação da estrutura de dados pode ser consutada em
    <https://tradicional.arq.br/schema/>.

    Digite um dos [b]Commands[/b] abaixo para começar ou rode novamente o
    comando [b]wasth[/b] com uma ou mais dentre as [bold]Options[/bold] abaixo.

    Se usa o [b]WASTH[/b] pela primeira vez, comece por rodar o comando
    [r] wasth configure [/r]
    """
    config_file = config_file or app_dir_config()
    ctx.obj = load_settings(config_file)
    if version:
        print(f"WASTH {__version__}")
        raise typer.Exit()


app.add_typer(configure_app, name="configure")

if __name__ == "__main__":
    app()
