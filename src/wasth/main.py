"""Ponto de entrada do WASTH: Web App para Sítios Tradicionais e Históricos"""

import typer

from .cli.configure import app as configure_app

app = typer.Typer()
app.add_typer(configure_app)

if __name__ == "__main__":
    app()
