"""Comandos de validação, por atualizar."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from pydantic_core import ErrorDetails
from rich import print as rprint
from rich.console import Console
from rich.markup import escape
from rich.progress import track

from wasth.models import Concept, Thing, Work

from ._common import markdown_filelist

error_console = Console(stderr=True)

app = typer.Typer()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
@dataclass
class FileValidationResult:
    """Objeto que descreve os erros de validação de um modelo."""

    file_path: Path
    is_valid: bool
    errors: list[ErrorDetails] = field(default_factory=list)
    load_error: str | None = None


def file_validation(
    file: Path, model: type[Thing], verbosity: str = "normal"
) -> FileValidationResult:
    try:
        ficha = model.from_file(file)
    except ValidationError as e:
        rprint(f":x:  {file.name}")
        return FileValidationResult(
            file_path=file,
            is_valid=False,
            errors=e.errors(include_input=True, include_url=False),
        )
    except Exception as e:
        rprint(f":x:  {file.name}")
        return FileValidationResult(
            file_path=file,
            is_valid=False,
            load_error=str(e),
        )
    else:
        rprint(f":white_check_mark:  {ficha.title} | {file.name}")

    return FileValidationResult(file_path=file, is_valid=True)


def display_results(
    results: list[FileValidationResult], verbosity: str = "normal"
) -> None:
    """Exibe o relatório completo após validar todos os arquivos."""
    valid_results = [result for result in results if result.is_valid]
    invalid_results = [result for result in results if not result.is_valid]

    rprint()

    if valid_results:
        rprint(f"[bold green]{len(valid_results)} fichas válidas.[/bold green]")

        for result in valid_results:
            rprint(f"  :white_check_mark:  {escape(str(result.file_path))}")

    if invalid_results:
        rprint()
        rprint(f"[bold red]{len(invalid_results)} fichas com problemas.[/bold red]")

        for result in invalid_results:
            rprint(f"  :x:  {escape(str(result.file_path))}")

            if result.load_error:
                rprint(
                    "    :no_entry: "
                    "Não foi possível carregar ou interpretar a ficha."
                )
                rprint(f"      Problema: {escape(result.load_error)}")
            else:
                for error in result.errors:
                    location = (
                        ".".join(str(part) for part in error["loc"]) or "(objeto)"
                    )

                    rprint(f"    :warning:  Campo: {escape(location)}")
                    rprint(f"      Problema: {escape(error['msg'])}")

                    if error.get("input") is not None:
                        rprint(
                            "      Valor recebido: " f"{escape(repr(error['input']))}"
                        )

            rprint()

    rprint()

    if invalid_results:
        rprint(
            f"[bold red]Validação concluída: "
            f"{len(valid_results)} válido(s), "
            f"{len(invalid_results)} com erro(s).[/bold red]"
        )
        raise typer.Exit(code=1)

    rprint(
        f"[bold green]Validação concluída: todos os "
        f"{len(valid_results)} arquivo(s) são válidos.[/bold green]"
    )


# -----------------------------------------------------------------------------
# Comandos
# -----------------------------------------------------------------------------
@app.command()
def valida(
    ctx: typer.Context,
    object_class: Annotated[
        str,
        typer.Argument(help="Classe de objeto a ser validado: Work (edificação) \
            ou Concept (vocabulário)."),
    ] = "Work",
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Mostra mensagens de erro adicionais."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q",
            "--quiet",
            help="Encaminha relatório para o console em vez de mostrar na tela.",
        ),
    ] = False,
    # Precisamos de opções para outros tipos de dados (db, etc.)
    files_path: Annotated[
        Path | None,
        typer.Option(
            "--path",
            exists=True,
            dir_okay=True,
            file_okay=True,
            resolve_path=True,
            readable=True,
            help="Um caminho, absoluto ou relativo ao diretório atual, \
            para um arquivo/ficheiro ou uma pasta contendo documentos \
            a serem processados. Por padrão, usa a pasta configurada.",
        ),
    ] = None,
) -> None:
    """Valida fichas em formato de texto com metadados.

    Uso: [b]wasth valida_ficha \\[ARGS\\] \\[--path FICHA OU PASTA\\][/b]

    [u]ARGS[/u] é o tipo de objeto a ser validado: Work (ficha de edificação)
    ou Concep (ficha de vocabulário controlado). Se omitido é Work por padrão.

    [u]--path FICHA OU PASTA[/u] permite informar o caminho relativo para uma
    ficha ou para uma pasta contendo fichas a serem validadas. Se omitido, o
    padrão é usar a pasta informada na configuração da app WASTH para a classe
    de objeto escolhida.

    As fichas devem estar em formato Markdown (extensão ".md", ".mkd", ".mkdn",
    ou ".markdown"). O arquivo/ficheiro README.md é ignorado.

    :param object_class: A classe de objetos a serem validados (Work ou Concept,
    por padrão Work).
    :param files_path: Um caminho de arquivo/ficheiro ou pasta.
    """
    config = ctx.obj
    object_class = object_class.strip().capitalize()
    match object_class:
        case "Work":
            rprint("Validando fichas de edificação.")
            files_path = files_path or config.work
            model = Work
        case "Concept":
            rprint("Validando fichas de vocabulário controlado.")
            files_path = files_path or config.vocab
            model = Concept
        case _:
            rprint(f"Classe {object_class} indefinida ou inválida, \
                usado o padrão [b]Work[/b].")
            files_path = files_path or config.work
            model = Work

    # Precisamos de opções para outros tipos de dados (db, etc.)
    files = markdown_filelist(files_path)
    if not files:
        raise typer.Abort(
            rprint(f":question:  Nenhuma ficha válida encontrada em {files_path}.")
        )

    rprint(f":hourglass:  Validando {len(files)} fichas de {object_class}...")

    verbosity = "normal"

    if verbose:
        verbosity = "verbose"
    elif quiet:
        verbosity = "quiet"

    results = [
        file_validation(file, model, verbosity=verbosity) for file in track(files)
    ]


if __name__ == "__main__":
    app()
