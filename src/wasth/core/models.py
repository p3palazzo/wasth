"""Modelos de objeto usados no WASTH, especialmente a ficha de obra"""

from pathlib import Path
from typing import TypedDict

import frontmatter
from rich import print as rprint
from ruamel.yaml import YAML

yaml = YAML(typ='safe')

class InOutPaths(TypedDict):
    """Contém uma lista de arquivos/ficheiros de entrada e uma pasta de saída."""
    filelist: list[Path]
    output_path: Path

def paths(
    in_path: Path | None = None,
    out_path: Path | None = None,
    overwrite: bool | None = None,
    filetype: str = '.md'
) -> InOutPaths:
    """Gera os nomes de arquivos de entrada e a pasta de saída a partir da
    entrada do usuário.

    :param args: Primeiro argumento: caminho de entrada (arquivo/ficheiro ou pasta)
    Segundo argumento: caminho de saída (pasta).
    :returns: Um dicionário (TypedDict) cujo primeiro elemento é o caminho de
    entrada e o segundo, opcional, é a pasta de saída.
    :rtype: InOutPaths
    """
    if not in_path:
        raw = input(f"""
Informar um caminho de arquivo/ficheiro ou pasta de leitura.
Por padrão será a pasta atual:

""").strip()
        in_path = Path(raw) if raw else Path.cwd()

    if in_path.is_dir():
        filelist = [
            p for p in in_path.iterdir() if p.is_file()
            and p.suffix.casefold() == filetype.casefold()
            and p.stem != "README"
        ]
        in_path_dir = in_path
        rprint(f"""
{len(filelist)} documentos no formato '{filetype}' encontrado(s) em {in_path.resolve()}.
        """)
    elif in_path.is_file() and in_path.suffix.casefold() == filetype.casefold():
        filelist = [in_path]
        in_path_dir = in_path.resolve().parent
    else:
        raise OSError(
f"Nenhum documento no formato '{filetype}' encontrado em {in_path.resolve()}"
        )

    if not out_path:
        raw = input(f"""
Informar um caminho de gravação.
Por padrão será a mesma pasta ou arquivo/ficheiro de entrada:

""")
        out_path = Path(raw) if raw else in_path

    if out_path == (in_path or in_path_dir) and not overwrite:
        ask_overwrite = input(
            "⚠️  Sobrescrever se existente? s/n\n"
        ).strip().casefold()
        overwrite = ask_overwrite in { "s", "sim", "y", "yes", "sobrescrever" }
        if overwrite is False:
            raise ValueError("Operação cancelada pelo usuário.")
    return { 'filelist': filelist, 'output_path': out_path}

def make_output_dir(output_dir: Path) -> Path:
    """Cria pasta de saída ou retorna erro."""
    try:
        output_dir.mkdir(exist_ok=True, parents=True)
    except PermissionError as e:
        raise PermissionError(f"""
:x:  Não foi possível criar a pasta '{str(output_dir)}': {e}.
        """) from e
    except Exception as e:
        raise OSError(f":x:  Erro na criação da pasta: {e}") from e
    return output_dir

def write_file(
        post: frontmatter.Post,
        output_dir: Path,
        filename: Path
) -> Path | None:
    """Grava cada arquivo/ficheiro conforme nome e pasta recebidos.

    :returns: Caminho onde o documento foi gravado, ou nada.
    :rtype: Path
    """
    try:
        dest = output_dir / filename
        frontmatter.dump(post, dest, sort_keys=False)
        rprint(f"""
:card_index:  {post.get('id')} --- [bold]{post.get('title')}[/bold]
   gravado em '{str(dest)}'
        """)
        return dest
    except Exception as e:
        raise OSError(f"""
:x:  Erro na escrita em '{str(output_dir)}/{str(filename)}':\n {e}
        """) from e
