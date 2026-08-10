"""Acesso ao CLI do Typer (assistente de preenchimento das fichas)
"""

from typing import Annotated, Optional

import typer
from pyorcid_checksum import ORCID_Checksum
from rich import print as rprint

app = typer.Typer()

def user_orcid(orcid: str) -> str:
    """Recebe, valida e normaliza um ORCiD inserido pelo usuário

    Aceita o número do ORCiD ou o URI completo.
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
def main(
    orcid: Annotated[
        str,
        typer.Argument(
            envvar="ORCID",
            metavar="ORCiD",
            prompt="Para começar, digite o seu ORCiD. Também pode cadastrá-lo na variável de ambiente 'ORCID'",
            callback=user_orcid,
            help="Seu número ou URI do ORCiD. Se não possuir um, cadastre-se em https://orcid.org",
        ),
    ]
) -> None:
    """
    Esta é a tela de acesso à interfaz de preenchimento das fichas dos
    Documentários de arquitetura tradicional.
    """
    typer.echo(f":white_check_mark: ORCiD {orcid} válido.")
    rprint("""
-------------------------------------------------------
 Interfaz de linha de comando da aplicação
 [bold]WASTH[/bold] : Web App para Sítios Tradicionais e Históricos
-------------------------------------------------------

Para instruções, digitar o comando:
uv run typer src/wasth/app.py run --help
        """)
    rprint("""
Por ora, não temos funcionalidade nenhuma nesta app.
    """)

if __name__ == "__main__":
    app()
