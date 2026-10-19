"""Módulo de validação do YAML: roda antes e depois de editar

Verifica se o arquivo/ficheiro existe, e se a sua sintaxe é válida.
"""

import os
import sys
from importlib import resources
from pathlib import Path

import frontmatter
import yamale
import yamllint.config
import yamllint.linter
from rich import print as rprint
from ruamel.yaml import YAML

from wasth.models import Work

from . import models

yaml = YAML(typ='safe')

def f_read(file: Path, enc="utf-8") -> dict:
    """Lê o arquivo/ficheiro se ele não estiver vazio"""
    with file.open('r', encoding=enc) as markdown:
        contents = markdown.read().split('\n---\n\n', 2)
        metadata = contents[0] + '\n'
        body = contents[1].lstrip() or ''
        document = {
            'metadata': metadata.lstrip(),
            'body': body
        }
    return document

def parse_metadata(file, encoding="utf-8") -> frontmatter.Post:
    """Carrega metadados em forma de dicionário com python-frontmatter"""
    with open(file, 'r', encoding=encoding) as document:
        post = frontmatter.load(document)
    return post

def serialize(data) -> str | None:
    """Devolve metadados ao formato texto"""
    if isinstance(data, dict):
        metadata = frontmatter.dumps(data)
        return metadata
    raise TypeError("Data type is not a dict")

def f_lint(f) -> list:
    """Mostra os problemas de formatação"""
    metadata = f_read(f)['metadata']
    yaml_config = yamllint.config.YamlLintConfig("extends: relaxed")
    yaml_lint = yamllint.linter.run(metadata, yaml_config)
    yaml_lint_list = []
    for p in yaml_lint:
        match p.level:
            case "error":
                p_level = ":x: "
            case "warning":
                p_level = ":warning: "
            case _:
                p_level = p.level
        p_print = f"\t{p_level}" + f"{p.line:>4}{':'}{p.column:>2}"\
            + f"{p.desc:<40}" + f"{'('}{p.rule}{')'}"
        yaml_lint_list.append(p_print)
    return yaml_lint_list

def main():
    pass

if __name__ == "__main__":
    raise SystemExit(main())
