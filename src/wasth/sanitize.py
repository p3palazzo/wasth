"""Limpeza na formatação das fichas

Importa e reexporta o conteúdo das fichas para limpar a formatação.
Não valida a estrutura do conteúdo.
"""

import sys
import os
import frontmatter
from ruamel.yaml import YAML
yaml = YAML(typ='safe')

def load_metadata(f, mode='r', enc='utf-8') -> frontmatter.Post:
    pass
