"""Módulo de validação do YAML: roda antes e depois de editar

Verifica se o arquivo/ficheiro existe, e se a sua sintaxe é válida.
"""

import os
import sys
from pathlib import Path

import frontmatter
import yamale
import yamllint.config
import yamllint.linter
from rich import print
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

def f_schema(f):
    """Deve receber o frontmatter extraído de f_read"""
    this_dir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_dir, '../data/schema.yaml'), 'r') as schema_file:
        schema = schema_file.read()
    schema = yamale.make_schema(content=schema, parser='ruamel')
    data = yamale.make_data(content=f, parser='ruamel')
    try:
        yamale.validate(schema, data)
        print(":white_check_mark: Estrutura de metadados é válida.")
        sys.exit(0)
    except yamale.YamaleError as e:
        print(":x: Erro de validação da estrutura de dados:")
        for result in e.results:
            for error in result.errors:
                print(f"\t{error}")
    except ValueError as e:
        print(f""":x: {e}""")
    sys.exit(1)

def f_valida(files: list[str]) -> int:
    """Valida arquivo/ficheiro contra esquema"""
    had_error = False
    for file in files:
        try:
            work = Work.from_file(file)
            title = work['title']
            print(f"""
-------------------------------------------------------------------------------
{title.upper():^79s}

:card_index: {file}
""")
            lint_result = f_lint(file)
            if not lint_result:
                print(":white_check_mark: Sem inconsistências de formatação.")
            else:
                print("Relatório de inconsistências de formatação:\n")
                for p in lint_result:
                    print(p)
            metadata = f_read(file)['metadata']
            f_schema(metadata)
        except Exception as e:
            had_error = True
            print(f"""
-------------------------------------------------------------------------------

:prohibited: Não foi possível ler {file}:""")
            print('  ' + str(e))
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
