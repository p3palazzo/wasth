"""Operações com as fichas de lugares

Cria e edita fichas de lugares.
"""
from pathlib import Path

import geojson
from rich import print

from wasth import cli
from wasth.core import models


def main(
    orcid: str | None = None,
    paths: models.InOutPaths | None = None,
    encoding: str = 'utf-8',
) -> list | None:
    """Compila, processa e grava todas as fichas de lugares encontradas."""
    if not orcid:
        orcid_input = input("Informar ORCiD do usuário:").strip()
        orcid = cli.user_orcid(orcid_input)
    if not paths:
        paths = models.paths(filetype='.geojson')
        if not paths:
            return None
    output_dir = paths['output_dir']
    models.make_output_dir(output_dir)
    files = sorted(paths['filelist'])
    result = []

    for f in files:
        with f.open('r', encoding=encoding) as file:
            collection = geojson.load(file)
        if f.stem.startswith('BR') and 'bc250' in f.stem:
            print(f"""
:card_index:  Encontrado documento {str(f)}.
            """)
            for feature in collection['features']:
                lugar = models.Place.from_ibge_bc250(feature, orcid=orcid)
                if lugar is None:
                    print(f"""
:warning:  Não foi possível gerar nome o conteúdo da ficha para o lugar
    "{feature['properties']['nome']}". A ficha não foi gravada.
                    """)
                    continue
                basename = lugar.slug()
                if basename is None:
                    print(f"""
:warning:  Não foi possível gerar nome de arquivo/ficheiro para o lugar
    "{feature['properties']['nome']}". A ficha não foi gravada.
                    """)
                    continue
                filename = Path(f"{basename}.md")
                dest = models.write_file(lugar, output_dir, filename)
                if dest:
                    result.append(dest)
        if f.stem.startswith('PT'):
            continue
        if f.stem.startswith('CV'):
            continue
        if f.stem.startswith('AO'):
            continue
    return result

if __name__ == "__main__":
    raise SystemExit(main())
