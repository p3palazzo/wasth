"""Ponto de entrada do WASTH: Web App para Sítios Tradicionais e Históricos"""

from typing import Annotated

import typer

from wasth import __version__
from wasth.cli.configure import app as configure_app

app = typer.Typer()


@app.callback(invoke_without_command=True, no_args_is_help=True)
def entrypoint(
    version: Annotated[
        bool,
        typer.Option(help="Informa o número da versão e encerra."),
    ] = False,
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
    if version:
        print(f"WASTH {__version__}")
        raise typer.Exit()


app.add_typer(configure_app)

if __name__ == "__main__":
    app()
