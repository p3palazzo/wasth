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

from wasth.core import models
from wasth.core.models import Work

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
        p_print = str
        p_print = f"\t{p_level}" + f"{p.line:>4}{':'}{p.column:>2}"\
            + f"{p.desc:<40}" + f"{'('}{p.rule}{')'}"
        yaml_lint_list.append(p_print)
    return yaml_lint_list

def valida_yaml_schema(f: Path, object_class: str) -> None:
    """Deve receber o frontmatter extraído de f_read"""
    match object_class:
        case "Work":
            yamale_schema = "work.yaml"
        case "Place":
            yamale_schema = "place.yaml"
        case "Concept":
            yamale_schema = "concept.yaml"
        case _:
            yamale_schema = "thing.yaml"
    # https://www.w3reference.com/blog/relative-file-paths-in-python-packages/
    with resources.as_file(
        resources.files("wasth.data").joinpath(yamale_schema)
    ) as schema_file:
        schema = schema_file.read_text(encoding="utf-8")
    schema = yamale.make_schema(content=schema, parser='ruamel')
    with f.open('r') as file:
        document = file.read()
        post = frontmatter.loads(document)
        if not post.metadata:
            raise ValueError(f"{f} não contém metadados a validar.")
    data = yamale.make_data(content=metadata, parser='ruamel')
    try:
        yamale.validate(schema, data)
        rprint(":white_check_mark: Estrutura de metadados é válida.")
        sys.exit(0)
    except yamale.YamaleError as e:
        rprint(":x: Erro de validação da estrutura de dados:")
        for result in e.results:
            for error in result.errors:
                rprint(f"\t{error}")
    except ValueError as e:
        rprint(f""":x: {e}""")
    sys.exit(1)

def f_valida(files: list[str]) -> int:
    """Valida arquivo/ficheiro contra esquema"""
    had_error = False
    for file in files:
        try:
            work = Work.from_file(file)
            title = work['title']
            rprint(f"""
-------------------------------------------------------------------------------
{title.upper():^79s}

:card_index: {file}
""")
            lint_result = f_lint(file)
            if not lint_result:
                rprint(":white_check_mark: Sem inconsistências de formatação.")
            else:
                rprint("Relatório de inconsistências de formatação:\n")
                for p in lint_result:
                    rprint(p)
            metadata = f_read(file)['metadata']
            valida_yaml_schema(metadata)
        except Exception as e:
            had_error = True
            rprint(f"""
-------------------------------------------------------------------------------

:prohibited: Não foi possível ler {file}:""")
            rprint('  ' + str(e))
    return 1 if had_error else 0

def main(
    args: models.InOutPaths | None = None,
    ignore_output_dir: bool = True
) -> int | None:
    """
    Recebe uma lista de arquivos YAML e relata validação de sintaxe e estilo
    """
    args = models.paths(overwrite=ignore_output_dir)
    if not args:
        return None
    files = args['filelist']
    return f_valida(files)

if __name__ == "__main__":
    raise SystemExit(main())
