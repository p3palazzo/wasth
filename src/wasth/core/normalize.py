"""Limpeza na formatação das fichas

Importa e reexporta o conteúdo das fichas para limpar a formatação.
Realiza algumas conversões do esquema DCMI para LIDO.
Valida a estrutura do conteúdo.
"""

from copy import deepcopy
from pathlib import Path

import frontmatter
from pyorcid_checksum import ORCID_Checksum
from rich import print as rprint
from ruamel.yaml import YAML

from wasth.core import models

yaml = YAML(typ='safe')

def normalize(post: frontmatter.Post) -> frontmatter.Post:
    """
    Processa metadados e migra DCMI para LIDO:

    - bibliographicCitation de map para lista contendo apenas citekeys
    - root:coverage:spatial para root:spatial
    - root:coverage:temporal para root:temporal
    - spatial:location:locationHistoric para root:location_historic
    - spatial:extent de map para lista
    - spatial:location de map para lista
    - format:extent e spatial:extent normalizados para format:extent (lista)
    """
    bibliographic_citation = post.get('bibliographicCitation')
    if isinstance(bibliographic_citation, dict):
        if bibliographic_citation.get('citekey') is not None:
            post['bibliographicCitation'] = [
                bibliographic_citation.get('citekey')
            ]
        else:
            raise ValueError(
f":book:  {bibliographic_citation} não contém uma chave de citação para {post['title'].upper()}."
            )
    elif isinstance(bibliographic_citation, list):
        citekeys = []
        for citation in bibliographic_citation:
            if isinstance(citation, str):
                citekeys.append(
                    citation if citation.startswith('@') else '@' + citation
                )
            elif isinstance(citation, dict) and isinstance(citation.get('relids'), str):
                citekeys.append(
                    citation['relids'] if citation['relids'].startswith('@')
                    else "@" + citation['relids']
                )
            else:
                rprint(
f":warning:  O registro {citation} não contém um campo com chave de citação, ignorando..."
                )
        if len(citekeys) > 0:
            post['bibliographicCitation'] = citekeys

    spatial = post.get('spatial')
    post_format = post.get('format')
    if post_format is not None:
        format_extent = post_format.get('extent')
        if format_extent is not None and isinstance(format_extent, list):
            measurements = deepcopy(format_extent)
            for m in measurements:
                m['extent'] = deepcopy(m.get('type'))
                m['type'] = 'http://terminology.lido-schema.org/lido00927'
                m['value'] = deepcopy(m.get('measurements'))
                m['unit'] = { 'display': m.get('unit') } # Not schema-conforming
                if m.get('measurements') is not None:
                    del m['measurements']
            post['format']['extent'] = { 'measurements': measurements }

    elif isinstance(spatial, dict) and isinstance(spatial.get('extent'), list):
        measurements = deepcopy(spatial['extent'])
        for m in measurements:
            m['extent'] = deepcopy(m.get('type'))
            m['type'] = 'http://terminology.lido-schema.org/lido00927'
            m['value'] = deepcopy(m.get('measurements'))
            m['unit'] = { 'display': m.get('unit') } # Not schema-conforming
            if m.get('measurements') is not None:
                del m['measurements']
        post['format'] = post.get('format') or {}
        post['format']['extent'] = {
            'measurements': measurements,
        }

    return post

def orcid_checksum(orcid: str) -> str | None:
    """Recebe, valida e normaliza um ORCiD inserido pelo usuário

    :param orcid: o número do ORCiD ou o URI completo.
    """
    orcid = orcid.strip()
    checker = ORCID_Checksum()
    valida = checker.check_orcid_checksum(orcid)
    if valida is False:
        rprint(f"ORCiD {orcid} inválido.")
        return None
    return checker.parse_orcid(orcid)

def make_id(work: models.Work, overwrite: bool | None = None) -> models.Work:
    "Roda o método de geração de ID Open Location no objeto models.Work"
    if work.get('spatial') is None:
        pass
    current_id = work.get('id')
    new_id = work.olc_id()
    if new_id is None:
        pass
    if current_id == new_id or new_id is None:
        return work
    if current_id is None:
        work['id'] = new_id
        return work
    if current_id != new_id:
        if overwrite is None:
            prompt = input(
f"Sobrescrever ID {current_id} existente com novo ID {new_id}? s/n"
            ).strip().lower()
            overwrite = prompt in { "s", "sim", "y", "yes", "true" }
        if overwrite is False:
            return work
    work['id'] = new_id
    return work

def write_id(source_file: Path | None, enc: str = 'utf-8') -> models.Work:
    "Grava o Open Location Code para o arquivo/ficheiro indicado."
    if not source_file:
        source_file = Path(input("Inserir um caminho de arquivo/ficheiro:"))
    if source_file.suffix != '.md':
        raise ValueError(
f":x:  Arquivo/ficheiro não encontrado em {str(source_file)} ou não é Markdown"
        )
    try:
        work = models.Work.from_file(source_file)
    except Exception as e:
        raise ValueError(f"""
:x:  Erro ao ler {source_file}:
   {e}
            """) from e
    work = make_id(work)
    with source_file.open('w', encoding=enc) as f:
        frontmatter.dump(work, f, sort_keys=False)
        rprint(
f":card_index:  ID: {make_id(work).get('id')} gravado em {str(source_file)}."
        )
    return work

def main(paths: models.InOutPaths | None = None) -> list | None:
    """Compila todos os arquivos/ficheiros a serem gravados."""
    if not paths:
        paths = models.paths(filetype='.md')
        if not paths:
            return None
    output_dir = paths['output_dir']
    models.make_output_dir(output_dir)
    files = sorted(paths['filelist'])
    for file in files:
        post = frontmatter.load(file)
        filename = Path(file)
        post = normalize(post)
# Funcionalidade temporária abaixo, remover quando não for mais necessária.
        obra = models.Work.from_post(post)
        post = make_id(obra)
# Funcionalidade temporária acima, remover quando não for mais necessária.
        models.write_file(post, output_dir, filename)
    return files

if __name__ == "__main__":
    raise SystemExit(main())
