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
from rdflib import URIRef
from rich import print as rprint

from wasth.core.orcid import orcid_profile, parse_orcid

from .settings import app_dir_config, load_settings, save_settings

WASTH_ENV = "wasth.env"

app = typer.Typer()


@dataclass
class WASTHConfig:
    """Configuração da sessão, disponível em `ctx.obj`."""

    orcid: str | None = None
    profile_name: str | None = None
    works: Path | None = None
    vocab: Path | None = None
    dwg: Path | None = None


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


def setup_user(
    orcid: str | None,
    profile_name: str | None,
    confirm: bool = True,
) -> tuple[WASTHConfig, bool]:
    """Processa a identidade do usuário/utente.

    :param orcid: ORCiD do usuário/utente.
    :param profile_name: Nome obtido pela consulta à API do ORCiD.
    :param confirm: Indica se é preciso confirmar as alterações.
    :return: O número ORCiD validado e o nome completo da pessoa.
    :rtype: tuple[str, str, bool]
    """
    orcid_changed = False

    orcid = parse_orcid(orcid) if orcid else None
    if orcid:
        rprint("Configuração encontrada:")
        rprint(f"  Seu ORCiD:                {orcid}")
        rprint(f"  Seu nome:                 {profile_name}")
        if confirm and not typer.confirm(
            "Prosseguir com os valores existentes?", default=True
        ):
            orcid_input = typer.prompt("ORCiD", default=orcid)
            if parse_orcid(orcid_input) != orcid:
                orcid = parse_orcid(orcid_input)
                orcid_changed = True
    else:
        print("Inicializando configuração de usuário[a]/utente.")
        orcid_input = typer.prompt("Informe seu ORCiD")
        orcid = parse_orcid(orcid_input)
        orcid_changed = True

    if not orcid:
        rprint("[red]É obrigatório informar um ORCiD válido.[/red]")
        raise typer.Abort()

    if orcid_changed or not profile_name:
        profile_name = orcid_profile_name(orcid)

    if not profile_name:
        rprint(
            "[yellow]Não foi possível obter o perfil na API do ORCiD[/yellow] "
            "(perfil inexistente, privado ou sem conexão)."
        )
        if typer.confirm("Usar este ORCiD mesmo assim?", default=False):
            profile_name = orcid
        else:
            print("Operação cancelada.")
            raise typer.Abort()

    setup = WASTHConfig(orcid=orcid, profile_name=profile_name)
    return (setup, orcid_changed)


def setup_folders(
    works: Path | None,
    vocab: Path | None,
    dwg: Path | None,
    confirm: bool = True,
) -> tuple[WASTHConfig, bool]:
    """Processa a configuração e gera objeto WASTHConfig.

    :param config_file: Localização do arquivo/ficheiro de configuração, por
    padrão é config.json dentro de typer.get_app_dir(wasth).
    :param works: Localização da pasta com as fichas de obras.
    :param vocab: Localização da pasta com o vocabulário controlado.
    :param dwg: Localização da pasta com os desenhos técnicos.
    :param confirm: Indica se é preciso confirmar as alterações.
    :return: Tuple com o objeto WASTHConfig e um bool notificando alteração.
    :rtype: tuple(WASTHConfig, bool)
    """
    values = [works, vocab, dwg]
    all_set = all(values)

    rprint("Configuração encontrada:")
    rprint(f"Fichas de obras:                  {works}")
    rprint(f"Fichas de vocabulário controlado: {vocab}")
    rprint(f"Desenhos técnicos:                {dwg}")

    if all_set:
        rprint("Configuração encontrada:")
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
            works = typer.prompt("Pasta contendo as fichas", default=works)
            vocab = typer.prompt(
                "Pasta contendo o vocabulário controlado", default=vocab
            )
            dwg = typer.prompt("Pasta contendo os desenhos técnicos", default=dwg)
            all_set = False

    works_dir = get_dir("fichas de obras", works)
    vocab_dir = get_dir("vocabulário controlado", vocab)
    dwg_dir = get_dir("desenhos técnicos", dwg)
    old_works = works.expanduser().resolve() if works else None
    old_vocab = vocab.expanduser().resolve() if vocab else None
    old_dwg = dwg.expanduser().resolve() if dwg else None

    changed = not all_set or (
        works_dir != old_works or vocab_dir != old_vocab or dwg_dir != old_dwg
    )

    setup = WASTHConfig(
        works=works_dir,
        vocab=vocab_dir,
        dwg=dwg_dir,
    )
    return (setup, changed)


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------
@app.command()
def user(
    ctx: typer.Context,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=True,
            file_okay=False,
            resolve_path=True,
            readable=True,
            writable=True,
            dir_okay=False,
            help="Arquivo/ficheiro de configuração existente ou a criar.",
        ),
    ] = None,
    orcid: Annotated[
        str | None,
        typer.Option(help="Seu número do ORCiD."),
    ] = None,
) -> None:
    """Informe o seu número do ORCiD ou um arquivo/ficheiro de configuração
    existente para carregar sua identidade na app.

    :param orcid: Aceita o número do ORCiD, o link completo ou a CURIE na forma
    `orcid:1234-5678-9012-345X`.
    :param config_file: Acionado pela opção `--config` na linha de comando,
    aceita o caminho para um arquivo/ficheiro contendo todas as opções desta
    função.
    """
    guided_setup = True
    config_file = config_file or app_dir_config()
    config_from_file = load_settings(config_file)
    if not orcid and config_from_file.get("orcid") is not None:
        guided_setup = False
    orcid = orcid or config_from_file.get("orcid")
    setup_config, changed_setup = setup_user(
        orcid=orcid,
        profile_name=config_from_file.get("profile_name"),
        confirm=guided_setup,
    )

    if changed_setup and typer.confirm(
        f"Grava as informações atualizadas em {config_file}?", default=True
    ):
        config_from_file["orcid"] = setup_config.orcid
        config_from_file["profile_name"] = setup_config.profile_name
        save_settings(config_from_file)
        rprint("""Para configurar as pastas padrão, rodar o comando
                  [b]wasth configure folders[/b]""")

    ctx.obj = config_from_file


@app.command()
def folders(
    ctx: typer.Context,
    works: Annotated[
        Path | None,
        typer.Option(
            "--fichas",
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
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="Pasta contendo os desenhos técnicos em formato DXF e SVG.",
        ),
    ] = None,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=True,
            file_okay=False,
            resolve_path=True,
            readable=True,
            writable=True,
            dir_okay=False,
            help="Arquivo/ficheiro de configuração.",
        ),
    ] = None,
) -> None:
    """Mostra, confirma, atualiza e grava as pastas padrão.

    :param works: Acionado pela opção `--fichas` na linha de comando, aceita um
    nome de pasta contendo as fichas de obras em formato Markdown.
    Por padrão é `casa`.
    :param vocab: Aceita um nome de pasta contendo as fichas de vocabulário
    controlado. Por padrão é `thesaurus`.
    :param dwg: Aceita um nome de pasta contendo os desenhos técnicos do
    projeto. Por padrão é `desenho`.
    :param config_file: Acionado pela opção `--config` na linha de comando,
    aceita o caminho para um arquivo/ficheiro contendo todas as opções desta função.
    """

    def _path_or_none(value: str | Path | None) -> Path | None:
        return Path(value).expanduser().resolve() if value else None

    if config_file and not (works or vocab or dwg):
        guided_setup = False
    else:
        config_file = app_dir_config()
        guided_setup = True
    config_from_file = load_settings(config_file)

    works = works or _path_or_none(config_from_file.get("works"))
    vocab = vocab or _path_or_none(config_from_file.get("vocab"))
    dwg = dwg or _path_or_none(config_from_file.get("dwg"))

    folder_setup, changed_setup = setup_folders(works, vocab, dwg, confirm=guided_setup)

    if changed_setup and typer.confirm(
        f"Gravar configuração em {config_file}?", default=True
    ):
        config_from_file["works"] = str(folder_setup.works)
        config_from_file["vocab"] = str(folder_setup.vocab)
        config_from_file["dwg"] = str(folder_setup.dwg)
        save_settings(config_from_file)

    ctx.obj = config_from_file


@app.callback(invoke_without_command=True)
def show(
    ctx: typer.Context,
    config_file: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=True,
            file_okay=False,
            resolve_path=True,
            readable=True,
            writable=True,
            dir_okay=False,
            help="Arquivo/ficheiro de configuração.",
        ),
    ] = None,
) -> None:
    config = ctx.obj
    rprint("Configuração encontrada:")
    rprint(f"  Seu ORCiD:                        {config.get("orcid")}")
    rprint(f"  Seu nome:                         {config.get("profile_name")}")
    rprint(f"  Fichas de obras:                  {config.get("works")}")
    rprint(f"  Fichas de vocabulário controlado: {config.get("vocab")}")
    rprint(f"  Desenhos técnicos:                {config.get("dwg")}")
    rprint("Para alterar, rode os comandos:")
    rprint("  wasth configure user")
    rprint("  wasth configure folders")
