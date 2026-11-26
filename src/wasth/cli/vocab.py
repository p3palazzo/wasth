"""Funções que resolvem vários conceitos do vocabulário controlado entre si."""

from pathlib import Path
from typing import Annotated

import typer
from rdflib import Graph
from rich import print as rprint
from rich.progress import track

from wasth.core.vocab import Vocabulary
from wasth.models import Concept

from ._common import AppState, get_app_dir, markdown_filelist

app = typer.Typer()


def dump_vocabulary_graph(graph: Graph, save_path: Path, s_format: str | None) -> Path:
    """Grava o grafo do vocabulário num arquivo/ficheiro."""
    if format:
        graph.serialize(destination=save_path, format=s_format)
    else:
        graph.serialize(destination=save_path)
    if save_path.is_file():
        rprint(f":page_facing_up:  Grafo gravado em {save_path}")
        return save_path
    raise OSError(f"Não foi possível gravar o grafo em {save_path}")


@app.command()
def build(
    ctx: typer.Context,
    source: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=True,
            file_okay=False,
            readable=True,
            resolve_path=True,
            help="Pasta contendo as fichas do vocabulário controlado em formato Markdown.",
        ),
    ] = None,
    dest: Annotated[
        Path | None,
        typer.Option(
            "--save-file",
            dir_okay=True,
            file_okay=True,
            writable=True,
            resolve_path=True,
            help="Caminho de destino para gravar o grafo processado.",
        ),
    ] = None,
    s_format: Annotated[
        str | None,
        typer.Option(
            "--format", help="Formato de exportação do grafo."
        )
    ] = None,
) -> None:
    """Cria o grafo do vocabulário controlado a partir das fichas."""
    state: AppState = ctx.obj
    config_source = Path(state.config["vocab"])
    source_dir = source or config_source

    if not source:
        rprint(f""":warning:  Pasta de origem não informada ou inválida,
            usando pasta configurada {config_source}.""")

    files = markdown_filelist(source_dir)
    if not files:
        raise typer.Abort(f"Nenhuma ficha válida encontrada em {source_dir}.")

    concepts = [Concept.from_file(file) for file in track(files)]
    vocabulary = Vocabulary.from_concepts(concepts)

    vocab_check = vocabulary.check()
    if vocab_check:
        rprint("[red]Erros encontrados no processamento do vocabulário:[/red]")
        for i in vocab_check:
            rprint(f"{i}")
        if not typer.confirm("Processar o grafo mesmo assim?", default=False):
            raise typer.Abort("Operação cancelada.")
    else:
        rprint("[green]Vocabulário processado sem erros estruturais.[/green]")

    save_path = dest.expanduser().resolve() if dest else None
    if save_path and save_path.is_dir():
        save_path = save_path / "vocab.ttl"
    if not save_path:
        save_path = get_app_dir() / "vocab.ttl"

    graph = vocabulary.graph
    if not graph:
        raise typer.Abort("Nenhum objeto inserido no grafo.")
    if typer.confirm(f"Gravar o grafo em {save_path}?", default=True):
        dump_vocabulary_graph(graph, save_path, s_format)


@app.callback(invoke_without_command=True)
def show_vocab(
    ctx: typer.Context,
):
    """Funções do vocabulário controlado."""
    state: AppState = ctx.obj
    config_source = Path(state.config["vocab"])

    if config_source.is_dir():
        rprint(f"Pasta configurada para o vocabulário controlado: {config_source}")
    else:
        rprint(
            "Para saber como configurar as pastas padrão, envie [b]wasth configure[/b]"
        )
    rprint("Envie [b]wasth vocab --help[/b] para ver os comandos disponíveis.")


if __name__ == "__main__":
    app()
