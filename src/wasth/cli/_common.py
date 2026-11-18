"""Utilidades para os comandos do WASTH."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any

import frontmatter
import typer
from rich import print as rprint

from wasth import __version__

# -----------------------------------------------------------------------------
# Models, objects, and aliases
# -----------------------------------------------------------------------------
ConfigFile = Annotated[
    Path | None,
    typer.Option(
        "--config-file",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        readable=True,
        writable=True,
        help="Arquivo/ficheiro de configuração existente ou a criar.",
    ),
]

FilesPath = Annotated[
    Path,
    typer.Option(
        "--path",
        exists=True,
        dir_okay=True,
        file_okay=True,
        resolve_path=True,
        readable=True,
        help=(
            "Um caminho, absoluto ou relativo ao diretório atual, "
            "para um arquivo/ficheiro ou uma pasta contendo documentos "
            "a serem processados. Por padrão é o diretório informado nas "
            "configurações do projeto para as fichas de edificações."
        ),
    ),
]


@dataclass
class AppState:
    """Reúne informações sobre a configuração da app durante a execução."""

    config_file: Path
    config: dict[str, Any]
    version: str = __version__


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

APP_NAME = "wasth"
DEFAULT_CONFIG = "config.json"


def app_dir_config(config_file_name: str | None = None) -> Path:
    """Return the WASTH user configuration file path."""
    app_dir = Path(typer.get_app_dir(APP_NAME))
    app_dir.mkdir(parents=True, exist_ok=True)
    if not config_file_name:
        config_file_name = DEFAULT_CONFIG
    return app_dir / config_file_name


def load_settings(user_path: Path = app_dir_config()) -> dict[str, Any]:
    """Load persisted user settings, returning an empty mapping if absent."""
    if not user_path or not user_path.is_file():
        return {}

    try:
        return json.loads(user_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise typer.BadParameter(
            f"Não foi possível ler {user_path}: {error}"
        ) from error


def save_settings(state: AppState) -> Path:
    """Grava as configurações de usuário/utente e pastas num arquivo/ficheiro.

    Por padrão usa [b]app_dir[/b] apropriado ao sistema operacional."""
    path = state.config_file or app_dir_config()
    path.parent.mkdir(parents=True, exist_ok=True)
    state.config["version"] = __version__
    contents = json.dumps(state.config, ensure_ascii=False, indent=2) + "\n"

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        os.replace(tmp_path, path)
    except OSError as e:
        rprint(f"[red]Erro ao gravar a configuração em {state.config_file}:[/red]")
        raise typer.Exit(code=1) from e
    return path


# Precisamos de opções para outros tipos de dados (db, etc.)
def markdown_filelist(files_path: Path | list[Path]) -> list[Path] | None:
    """Retorna uma lista de fichas Markdown a partir do caminho fornecido."""

    def _is_markdown(file: Path) -> Path | None:
        if (
            not file.is_file()
            or file.stem == "README"
            or file.suffix.casefold() not in (".md", ".mkd", ".mkdn", ".markdown")
            or not frontmatter.check(file)
        ):
            return None
        return file

    if isinstance(files_path, list):
        return sorted(file for file in files_path if _is_markdown(file))

    target = files_path.expanduser().resolve() if files_path else None
    if not target:
        raise FileNotFoundError(f"Caminho {files_path} não encontrado.")

    if target.is_file():
        if not _is_markdown(target):
            raise ValueError(f"{target.name} não é um documento Markdown válido.")
        return [target]

    if target.is_dir():
        return sorted(file for file in target.iterdir() if _is_markdown(file)) or None

    raise ValueError(f"{target.name} não é um arquivo/ficheiro ou pasta.")
