"""Funções de configuração do aplicativo `wasth`.

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

app = typer.Typer()


@dataclass
class WASTHConfig:
    """Configuração da sessão, disponível em `ctx.obj`."""

    orcid: str
    profile_name: str
    works: Path
    vocab: Path
    dwg: Path


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
    return profile.display_name if profile else None


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
def get_dir(label: str, current: Path | None) -> Path:
    """Seleciona uma pasta existente, pedindo ao usuário se preciso.

    :param label: Rótulo que indica o propósito da pasta.
    :type label: str
    :param current: Pasta atualmente selecionada.
    :type current: str
    :return: Um caminho para a pasta selecionada.
    :rtype: pathlib.Path
    """
    value = current
    while True:
        if not value or not Path(value).is_dir():
            value = typer.prompt(f"Informar a pasta contendo os arquivos de {label}")
        new_dir = Path(value).expanduser().resolve()
        if not new_dir:
            create = typer.confirm(f"Criar pasta {new_dir}?", default=True)
            if not create:
                continue
            new_dir.mkdir(parents=True)
        if new_dir.is_dir():
            rprint(f":open_file_folder:  Pasta selecionada para {label}: {new_dir}\n")
            return new_dir
        rprint(f":question:  Pasta não encontrada: {new_dir}")
        value = None
        continue


def setup_config(
    env_file: Path,
    orcid: str | None,
    profile_name: str | None,
    works: Path | None,
    vocab: Path | None,
    dwg: Path | None,
    confirm: bool = True,
) -> tuple[WASTHConfig, bool]:
    """Processa a configuração e gera objeto WASTHConfig.

    :param env_file: Localização do arquivo/ficheiro de configuração.
    :param orcid: ORCiD do usuário/utente.
    :param works: Localização da pasta com as fichas de obras.
    :param vocab: Localização da pasta com o vocabulário controlado.
    :param dwg: Localização da pasta com os desenhos técnicos.
    :param confirm: Indica se é preciso confirmar as alterações.
    :return: Tuple com o objeto WASTHConfig e um bool notificando alteração.
    :rtype: tuple(WASTHConfig, bool)
    """
    env_file = env_file.expanduser().resolve()
    rprint(f"\
           [dim]:page_facing_up:  Arquivo/ficheiro de configuração escolhido: \
            {env_file}[/dim]\
    ")
    values = [orcid, works, vocab, dwg]
    all_set = all(values)

    if all_set:
        rprint("Configuração encontrada:")
        rprint(f"  Seu ORCiD:              {orcid}")
        rprint(f"  Seu nome:               {profile_name}")
        rprint(f"  Fichas de obras:        {works.expanduser().resolve() \
            if works else ":question:"}")
        rprint(f"  Vocabulário controlado: {vocab.expanduser().resolve() \
            if vocab else ":question:"}")
        rprint(f"  Desenhos técnicos:      {dwg.expanduser().resolve() \
            if dwg else ":question:"}")
        print("\n")
        if confirm and not typer.confirm(
            "Prosseguir com os valores existentes?", default=True
        ):
            orcid = typer.prompt("ORCiD", default=orcid)
            works = typer.prompt("Pasta contendo as fichas", default=works)
            vocab = typer.prompt(
                "Pasta contendo o vocabulário controlado", default=vocab
            )
            dwg = typer.prompt("Pasta contendo os desenhos técnicos", default=dwg)
            all_set = False

    orcid_number, profile_name = orcid_resolve(orcid)
    works_dir = get_dir("fichas de obras", works)
    vocab_dir = get_dir("vocabulário controlado", vocab)
    dwg_dir = get_dir("vocabulário controlado", dwg)
    old_works = str(works.expanduser().resolve()) if works else None
    old_vocab = str(vocab.expanduser().resolve()) if vocab else None
    old_dwg = str(dwg.expanduser().resolve()) if dwg else None

    config = WASTHConfig(orcid_number, profile_name, works_dir, vocab_dir, dwg_dir)
    changed = not all_set or (
        orcid_number != orcid
        or str(works_dir) != old_works
        or str(vocab_dir) != old_vocab
        or str(dwg_dir) != old_dwg
    )

    return (config, changed)


def write_env(env_file: Path, config: WASTHConfig) -> Path:
    """Grava as configurações do usuário/utente."""
    env_file.touch(exist_ok=True)
    set_key(str(env_file), "WASTH_ORCID", config.orcid)
    set_key(str(env_file), "WASTH_PROFILE_NAME", config.profile_name)
    set_key(str(env_file), "WASTH_WORKS_DIR", str(config.works))
    set_key(str(env_file), "WASTH_VOCAB_DIR", str(config.vocab))
    set_key(str(env_file), "WASTH_DWG_DIR", str(config.dwg))
    rprint(f"[green]Configuração gravada em {env_file}:[/green]")
    rprint(f"  Seu ORCiD:              {config.orcid}")
    rprint(f"  Seu nome:               {config.profile_name}")
    rprint(f"  Fichas de obras:        {config.works}")
    rprint(f"  Vocabulário controlado: {config.vocab}")
    rprint(f"  Desenhos técnicos:      {config.dwg}")
    return env_file


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
        Path | None,
        typer.Option(
            "--fichas",
            envvar="WASTH_WORKS_DIR",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Pasta contento as fichas de obras em formato Markdown.",
        ),
    ] = None,
    vocab: Annotated[
        Path | None,
        typer.Option(
            envvar="WASTH_VOCAB_DIR",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Pasta contento as fichas de vocabulário controlado em formato Markdown.",
        ),
    ] = None,
    dwg: Annotated[
        Path | None,
        typer.Option(
            "--desenhos",
            envvar="WASTH_DWG_DIR",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Pasta contendo os desenhos técnicos em formato DXF e SVG.",
        ),
    ] = None,
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            exists=True,
            file_okay=False,
            resolve_path=True,
            readable=True,
            writable=True,
            dir_okay=False,
            help=("""Arquivo/ficheiro de configuração. Se indicado, a
configuração completa é usada sem pedir confirmação (padrão: .wasth.env na
pasta atual, com confirmação)."""),
        ),
    ] = None,
) -> None:
    """Mostra, confirma, atualiza e grava as variáveis do usuário/utente.

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
    dwg = dwg or env_from_file.get("WASTH_DWG_DIR")

    config, changed = setup_config(
        env_file, orcid, profile_name, works, vocab, dwg, confirm=not env_declared
    )

    if changed and typer.confirm(
        f"Gravar configuração em {env_file.name}?", default=True
    ):
        write_env(env_file, config)

    ctx.obj = config
