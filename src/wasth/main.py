"""Ponto de entrada do WASTH: Web App para Sítios Tradicionais e Históricos"""

from typing import Annotated

import typer

from . import __version__
from .cli._common import AppState, ConfigFile, app_dir_config, load_settings
from .cli.configure import app as configure_app
from .cli.export import app as export_app
from .cli.valida import app as valida_app
from .cli.vocab import app as vocab_app

app = typer.Typer()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Comandos
# -----------------------------------------------------------------------------
@app.callback(invoke_without_command=True, no_args_is_help=True)
def entrypoint(
    ctx: typer.Context,
    config_file: ConfigFile = None,
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

    Se usa o [b]WASTH[/b] pela primeira vez, comece por rodar o comando
    [b]wasth configure --help[/b]
    """
    config_file = (
        config_file.expanduser().resolve() if config_file else app_dir_config()
    )
    ctx.obj = AppState(
        config_file=config_file, config=load_settings(config_file), version=__version__
    )

    if version:
        print(f"WASTH {__version__}")
        raise typer.Exit()


app.add_typer(configure_app, name="configure")
app.add_typer(valida_app)
app.add_typer(export_app, name="export")
app.add_typer(vocab_app, name="vocab")

if __name__ == "__main__":
    app()
