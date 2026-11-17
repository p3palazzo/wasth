"""Exportação em diversos formatos: geoJSON, LIDO XML, RDF."""

from pathlib import Path
from typing import Annotated

import geojson as geoJSON
import typer
from rich import print as rprint

from wasth.models import Work

from ._common import FilesPath, markdown_filelist

app = typer.Typer()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def geojson_collection(works: list[Work]) -> geoJSON.FeatureCollection | None:
    """Gera uma coleção de objetos geoJSON a partir dos objetos ingeridos.
    Esta função pede os objetos já processados.
    Para passar uma pasta ou um arquivo/ficheiro, usar outra função antes.

    :param works: Objetos do WASTH que tenham georreferenciamento,
    passados enquanto tais
    :return: uma coleção de objetos geoJSON com a locação e o nome de cada objeto.
    :rtype: geojson.FeatureCollection
    """
    features = []
    for work in works:
        location = work.site_location
        if not isinstance(location, geoJSON.Point):
            continue
        feature = geoJSON.Feature(
            geometry=location,
            properties={
                "title": work.title,
                "id": work.id,
            },
        )
        if feature.is_valid:
            features.append(feature)
    if not features:
        return None
    collection = geoJSON.FeatureCollection(features)
    return collection if collection.is_valid else None


# -----------------------------------------------------------------------------
# Comandos
# -----------------------------------------------------------------------------
@app.command()
def geojson(
    ctx: typer.Context,
    input_path: FilesPath | None,
    out_file: Annotated[
        Path | None,
        typer.Option(
            "--out",
            "-o",
            dir_okay=False,
            file_okay=True,
            resolve_path=True,
            readable=True,
            writable=True,
            help=("Caminho e nome do arquivo a ser gravado, por padrão \
            ./wasth.geojson."),
        ),
    ] = None,
) -> None:
    """Converte fichas em um documento geoJSON que pode ser carregado no QGIS."""
    config = ctx.obj
    files_path: Path = input_path or config.works
    files = markdown_filelist(files_path)
    if not files:
        raise typer.Abort(
            rprint(
                f":question:  Nenhuma ficha em formato Markdown encontrada em {files_path}."
            )
        )

    works = [Work.from_file(f) for f in files]
    if not works:
        raise typer.Abort(
            rprint(f":x:  Nenhuma ficha válida encontrada em {files_path}")
        )
    rprint(f"{len(works)} objetos lidos.")

    collection = geojson_collection(works)
    if not collection:
        raise typer.Abort(
            rprint(f":no_entry:  O caminho {files_path} não contém nenhum objeto \
                georreferenciado.")
        )
    if collection:
        if collection.errors():
            rprint(f"{collection.errors()}")
        else:
            rprint("[green]Nenhum erro detectado.[green]")
        if len(works) < len(collection["features"]):
            rprint(f"[yellow]{len(works) - len(collection["features"])} \
                objetos sem georreferenciamento.[/yellow]")
    rprint(f"{len(collection["features"])} objetos georreferenciados encontrados.")

    out_file = (
        out_file.expanduser().resolve()
        if out_file
        else Path("wasth.geojson").expanduser().resolve()
    )

    if collection and typer.confirm(
        f"Grava o georreferenciamento em {out_file}?", default=True
    ):
        if out_file.exists() and not typer.confirm(
            "O destino existe. Sobrescrever?", default=False
        ):
            raise typer.Abort("Operação cancelada.")
        try:
            with open(out_file, "w", encoding="utf-8") as f:
                geoJSON.dump(collection, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise OSError(f"""
    :x:  Erro na escrita em {out_file}:
    {e}
            """) from e

    if not out_file.is_file():
        raise FileNotFoundError(":warning:  Nenhum objeto foi gravado!")
