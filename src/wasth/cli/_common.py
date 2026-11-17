"""Utilidades para os comandos do WASTH."""

from pathlib import Path
from typing import Annotated

import frontmatter
import typer

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
FilesPath = Annotated[
    Path,
    typer.Option(
        "--path",
        exists=True,
        dir_okay=True,
        file_okay=True,
        resolve_path=True,
        readable=True,
        help="Um caminho, absoluto ou relativo ao diretório atual, \
        para um arquivo/ficheiro ou uma pasta contendo documentos \
        a serem processados. Por padrão é o diretório informado nas \
        configurações do projeto para as fichas de edificações.",
    ),
]


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
