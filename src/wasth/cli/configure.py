"""Ponto de entrada do aplicativo `wasth`.

Configuração (ORCiD, pasta de Works, pasta de Concepts) é lida, em ordem
de prioridade, de:

1. opções de linha de comando (``--orcid``, ``--fichas``, ``--vocab``);
2. variáveis de ambiente (``WASTH_ORCID``, ``WASTH_PROFILE_NAME``,
   ``WASTH_WORKS_DIR``, ``WASTH_VOCAB_DIR``);
3. arquivo ``.wasth.env`` na pasta onde o comando é executado.

Dependências: typer, rich, python-dotenv, httpx, PyORCIDChecksum
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from dotenv import dotenv_values, set_key
from rdflib import URIRef
from rich import print as rprint

from wasth.core.orcid import orcid_profile, parse_orcid

WASTH_ENV = "wasth.env"

app = typer.Typer(
    help=("""Interfaz de linha de comando da aplicação
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
"""),
    no_args_is_help=True,
)


@dataclass
class WASTHConfig:
    """Configuração da sessão, disponível em `ctx.obj`."""

    orcid: str
    profile_name: str
    works: Path
    vocab: Path


# --------------------------------------------------------------------------
# ORCiD
# --------------------------------------------------------------------------
def orcid_profile_name(orcid: str | URIRef) -> str | None:
    """Puxa o nome do usuário/utente a partir do número ORCiD informado.

    :param orcid: o número ORCiD do usuário.
    :returns: Nome da pessoa, ou vazio se o nome do perfil não existir, se
    o número do ORCiD for inválido, ou se a API estiver inacessível.
    :rtype: str | None
    """
    try:
        orcid_number = parse_orcid(orcid)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    try:
        profile = orcid_profile(orcid_number)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    return profile.full_name if profile else None


def orcid_resolve(current: str | URIRef | None) -> tuple[str, str]:
    """Consulta o ORCiD fornecido pelo usuário/utente.

    :param current: ORCiD recebido pela função.
    :returns: (orcid, full_name)
    :rtype: tuple[str, str]
    """
    orcid = current
    while True:
        if not orcid:
            orcid = typer.prompt("Informe seu número ou link do ORCiD")
        if not parse_orcid(orcid):
            rprint(f"[red]ORCiD inválido:[/red] {orcid}")
            orcid = None
            continue
        orcid = parse_orcid(orcid)
        profile_name = orcid_profile_name(orcid)
        if profile_name is None:
            rprint(
                "[yellow]Não foi possível obter o perfil na API do ORCiD "
                "(perfil inexistente, privado ou sem conexão).[/yellow]"
            )
            if typer.confirm("Usar este ORCiD mesmo assim?", default=False):
                return orcid, orcid
            orcid = None
            continue
        rprint(f"Olá, [bold green]{profile_name}[/bold green]! ({orcid})")
        return orcid, profile_name


# --------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------
def get_dir(label: str, workdir: str | None) -> Path:
    """Seleciona uma pasta existente, pedindo ao usuário se preciso.

    :param label: Rótulo que indica o propósito da pasta.
    :type label: str
    :param workdir: Pasta atualmente selecionada.
    :type workdir: str
    :return: Um caminho para a pasta selecionada.
    :rtype: pathlib.Path
    """
    value = workdir
    while True:
        if not value:
            value = typer.prompt(f"Informar a pasta contendo os arquivos de {label}:")
        dir = Path(value).expanduser().resolve()
        if not dir:
            create = typer.confirm(f"Criar pasta {str(dir)}?")
            if not create:
                continue
            dir.mkdir(parents=True)
        if dir.is_dir():
            rprint(f"pasta selecionada: {str(dir)}")
            return dir
        rprint(f"[red]Pasta não encontrada:[/red] {dir}")
        value = None


def setup_config(
    env_file: Path,
    orcid: str | None,
    profile_name: str | None,
    works: str | None,
    vocab: str | None,
    confirm: bool = True,
) -> tuple[WASTHConfig, bool]:
    """Processa a configuração e gera objeto WASTHConfig.

    :param env_file: Localização do arquivo/ficheiro de configuração.
    :param orcid: ORCiD do usuário/utente.
    :param works: Localização da pasta com as fichas de obras.
    :param vocab: Localização da pasta com o vocabulário controlado.
    :param confirm: Indica se é preciso confirmar as alterações.
    :return: Tuple com o objeto WASTHConfig e um bool notificando alteração.
    :rtype: tuple(WASTHConfig, bool)
    """
    rprint(f"[dim]Arquivo/ficheiro de configuração escolhido: {env_file}[/dim]")
    values = [orcid, works, vocab]
    all_set = all(values)

    if all_set:
        rprint("[b]Configuração encontrada:[/b]")
        rprint(f"  Seu ORCiD:              {orcid}")
        rprint(f"  Seu nome:               {profile_name}")
        rprint(f"  Fichas de obras:        {str(works)}")
        rprint(f"  Vocabulário controlado: {str(vocab)}")
        if confirm and not typer.confirm(
            "Prosseguir com os valores existentes?", default=True
        ):
            orcid = typer.prompt("ORCiD", default=orcid)
            works = typer.prompt("Pasta contendo as fichas", default=works)
            vocab = typer.prompt(
                "Pasta contendo o vocabulário controlado", default=vocab
            )
            all_set = False

    orcid_number, profile_name = orcid_resolve(orcid)
    works_dir = get_dir("fichas de obras", works)
    vocab_dir = get_dir("vocabulário controlado", vocab)
    old_works = str(Path(works).expanduser().resolve()) if works else None
    old_vocab = str(Path(vocab).expanduser().resolve()) if vocab else None

    config = WASTHConfig(orcid_number, profile_name, works_dir, vocab_dir)
    changed = not all_set or (
        orcid_number != orcid
        or str(works_dir) != old_works
        or str(vocab_dir) != old_vocab
    )

    return (config, changed)


def write_env(env_file: Path, config: WASTHConfig) -> Path:
    """Grava as configurações do usuário/utente."""
    env_file.touch(exist_ok=True)
    set_key(str(env_file), "WASTH_ORCID", config.orcid)
    set_key(str(env_file), "WASTH_PROFILE_NAME", config.profile_name)
    set_key(str(env_file), "WASTH_WORKS_DIR", str(config.works))
    set_key(str(env_file), "WASTH_VOCAB_DIR", str(config.vocab))
    rprint(f"[green]Configuração gravada em {env_file}:[/green]")
    rprint(f"  Seu ORCiD:              {config.orcid}")
    rprint(f"  Seu nome:               {config.profile_name}")
    rprint(f"  Fichas de obras:        {config.works}")
    rprint(f"  Vocabulário controlado: {config.vocab}")
    return env_file


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------
@app.callback(invoke_without_command=True)
def main():
    pass


# --------------------------------------------------------------------------
# Subcomandos
# --------------------------------------------------------------------------
@app.command()
def configure(
    ctx: typer.Context,
    orcid: Annotated[
        str | None,
        typer.Option(envvar="WASTH_ORCID", help="Seu número do ORCiD."),
    ] = None,
    works: Annotated[
        str | None,
        typer.Option(
            "--fichas",
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
    """Confirma, atualiza e grava as variáveis do usuário/utente.

    :param orcid: Aceita o número do ORCiD, o link completo ou a CURIE na forma
    `orcid:1234-5678-9012-345X`.
    :param works: Acionado pela opção `--fichas` na linha de comando, aceita um
    nome de pasta contendo as fichas de obras em formato Markdown.
    Por padrão é `casa`.
    :param vocab: Aceita um nome de pasta contendo as fichas de vocabulário
    controlado. Por padrão é `thesaurus`.
    :param env_file: Acionado pela opção `--env-file` na linha de comando,
    aceita o caminho para um arquivo/ficheiro contendo todas as opções desta
    função.
    """
    env_declared = env_file is not None
    if not env_file:
        env_file = Path.cwd() / WASTH_ENV
    env_from_file = dotenv_values(env_file) if env_file.is_file() else {}
    orcid = parse_orcid(orcid) if orcid else env_from_file.get("WASTH_ORCID")
    profile_name = (
        orcid_profile_name(orcid) if orcid else env_from_file.get("WASTH_PROFILE_NAME")
    )
    works = works or env_from_file.get("WASTH_WORKS_DIR")
    vocab = vocab or env_from_file.get("WASTH_VOCAB_DIR")

    config, changed = setup_config(
        env_file, orcid, profile_name, works, vocab, confirm=not env_declared
    )

    if changed and typer.confirm(
        f"Gravar configuração em {env_file.name}?", default=True
    ):
        write_env(env_file, config)

    ctx.obj = config


@app.command()
def info(ctx: typer.Context) -> None:
    """Mostra a configuração em uso."""
    c: WASTHConfig = ctx.obj
    rprint(f"Você: {c.profile_name} ({c.orcid})")
    rprint(f"Fichas:    {c.works}")
    rprint(f"Vocabulário controlado: {c.vocab}")
