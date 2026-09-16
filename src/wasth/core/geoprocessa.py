"""Converte fichas em Markdown+YAML para geoJSON

Usa frontmatter para extrair metadados.
Não temos previsão de implementar o caminho inverso
(geoJSON para fichas em Markdown+YAML).
"""

from pathlib import Path

import geojson
from rich import print as rprint

from wasth.core import models


def locations(
    things: list[models.Thing]
) -> geojson.FeatureCollection | None:
    """
    Gera uma coleção de objetos geoJSON a partir dos objetos ingeridos.
    Esta função pede os objetos já processados.
    Para passar uma pasta ou um arquivo/ficheiro, usar outra função antes.

    :param things: Objetos do WASTH que tenham georreferenciamento, passados enquanto tais
    :return: uma coleção de objetos geoJSON com a locação e o nome de cada objeto.
    """
    features = []
    for thing in things:
        location = thing.location()
        title = thing.get('title')
        if not isinstance(location, geojson.Point) or not isinstance(title, str):
            continue
        feature = geojson.Feature(
            geometry = thing.location,
            properties = { "title": title }
        )
        if feature.is_valid:
            features.append(feature)
    if not features:
        return None
    collection = geojson.FeatureCollection(features)
    return collection if collection.is_valid else None

def f_write(
    collection: geojson.FeatureCollection,
    output_file: Path,
    encoding: str = 'utf-8',
) -> None:
    """
    Escreve a coleção geojson.FeatureCollection para um arquivo/ficheiro.

    :param collection: Uma coleção gerada pela função locations()
    :param output_file: Um caminho Path
    :param encoding: Por padrão, a codificação de caracteres é UTF-8
    """
    try:
        directory = Path(output_file).resolve().parent
        directory.mkdir(exist_ok=True, parents=True)
        with output_file.open('w', encoding=encoding) as f:
            geojson.dump(collection, f)
        rprint(f":page_facing_up:  '{output_file}' gravado com sucesso.")
    except Exception as e:
        raise OSError(f"""
:x:  Erro na escrita de '{str(output_file)}': {e}
        """) from e

def main(
    args: models.InOutPaths | None = None,
    ignore_output_dir: bool | None = None,
    encoding: str = 'utf-8'
) -> Path | None:
    """
    Recebe um ou mais arquivos/ficheiros ou um nome de pasta,
    grava um documento .geojson.
    """
    args = models.paths(overwrite=ignore_output_dir)
    if not args:
        return None
    files = args['filelist']
    things = []
    for f in files:
        thing = models.Thing.from_file(f)
        if isinstance(thing, models.Thing):
            things.append(thing)
    if not things:
        return None
    collection = locations(things)
    if not collection:
        return None
    output_filename = input("""
    Escolha um nome de arquivo para gravar, por padrão 'wasth.geojson':
    """).strip() or 'wasth.geojson'
    output_file = Path(args['output_dir']) / Path(output_filename)
    f_write(collection, output_file=output_file, encoding=encoding)
    return output_file

if __name__ == "__main__":
    raise SystemExit(main())
