"""Converte fichas em Markdown+YAML para geoJSON

Usa frontmatter para extrair metadados.
"""

import sys
import os
import frontmatter
import json
import geopandas as gpd

if __name__ == "__main__":
    if len(sys.argv) > 1:
        args = sys.argv[1:]
    else:
        args = input("""
Informar um caminho relativo de pasta ou nomes de arquivos/ficheiros:
(deixar em branco cancela a operação)
""").split()
    if args:
        if os.path.isdir(args[0]):
            filelist = [
                os.path.join(args[0], f) for f in os.listdir(args[0])
                if os.path.isfile(os.path.join(args[0], f))
            ]
        elif os.path.isfile(args[0]):
            filelist = args
        for file in filelist:
            pass
    else:
        print("Operação cancelada")
