"""Converte fichas em Markdown+YAML para geoJSON

Usa frontmatter para extrair metadados.
Não temos previsão de implementar o caminho inverso
(geoJSON para fichas em Markdown+YAML).
"""

from pathlib import Path

import geojson
from rich import print

from wasth.core import models


def collect_features(
        features: list[geojson.Feature]
) -> geojson.FeatureCollection | None:
    """
    Gera uma coleção de objetos geoJSON a partir dos objetos ingeridos.
    """
    collection = geojson.FeatureCollection(features)
    return collection

def f_write(
    collection: geojson.FeatureCollection,
    output_file: Path,
    encoding: str = 'utf-8',
) -> None:
    """
    Escreve a coleção geojson.FeatureCollection para um arquivo/ficheiro.
    """
    try:
        directory = Path(output_file).resolve().parent
        directory.mkdir(exist_ok=True, parents=True)
        with output_file.open('w', encoding=encoding) as f:
            geojson.dump(collection, f)
        print(f":page_facing_up:  Arquivo '{output_file}' gravado com sucesso.")
    except Exception as e:
        raise OSError(f"""
:x:  Erro na escrita do arquivo '{str(output_file)}': {e}
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
    features = []
    for f in files:
        obra = models.Work.from_file(f)
        places = obra.places()
        if not places:
            return None
        for place in places['features']:
            if isinstance(place, geojson.Point) and\
                place['properties']['type'] == 'site':
                features.append(place)
                break
    if len(features) == 0:
        return None
    collection = collect_features(features)
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
