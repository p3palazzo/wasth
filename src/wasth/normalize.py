"""Limpeza na formatação das fichas

Importa e reexporta o conteúdo das fichas para limpar a formatação.
Não valida a estrutura do conteúdo.
"""

import sys
import os
import frontmatter
from ruamel.yaml import YAML
import pandoc
yaml = YAML(typ='safe')

class NormalizedWork:
    def __init__(self, input_path, encoding='utf-8'):
        self.inp = input_path
        self.enc = encoding

    def post(self) -> frontmatter.Post:
        with open(self.inp, 'r', encoding=self.enc) as f:
            post = frontmatter.load(f)
        return post

    def metadata(post):
        metadata = post['metadata']
        return metadata

    def content(post):
        content = post['content']
        ast = pandoc.read(content)
        normalized_content = pandoc.write(ast)
        return normalized_content

def read_write_paths(input) -> dict:
    if len(input) == 3:
        args = input[1:]
    else:
        args = input("""
Informar um caminho de arquivo/ficheiro de entrada e uma pasta de saída:
(deixar em branco cancela a operação)
""").split()
    if args:
        if os.path.isfile(args[0]):
            input_path = args[0]
        else:
            print("O primeiro argumento não é um arquivo válido.")
            exit(1)
        if not os.path.isfile(args[1]):
            output_path = args[1]
        else:
            print("O segundo argumento não é uma pasta válida.")
            exit(1)
        result = { 'input': input_path, 'outdir': output_path }
        return result
    else:
        print("Operação cancelada")

def write_file(post, dir, filename):
    try:
        os.makedirs(dir)
        print(f"📁  Pasta '{dir}' criada com sucesso.")
        dest = os.path.join(dir, filename)
    except FileExistsError:
        print(f"📁  Pasta '{dir}' já existe.")
        dest = os.path.join(dir, filename)
    except PermissionError:
        print(f"❌  Não foi possível criar a pasta '{dir}': sem permissões.")
        exit(1)
    except Exception as e:
        print(f"❌  Erro na criação da pasta: {e}")
        exit(1)
    try:
        frontmatter.dump(post, dest)
        print(f"📄  Arquivo '{dest}' gravado com sucesso.")
    except Exception as e:
        print(f"❌  Erro na escrita do arquivo '{dest}': {e}")
        exit(1)

if __name__ == "__main__":
    args = read_write_paths(sys.argv)
    normalized = NormalizedWork(args['input'])
    filename = os.path.basename(args['input'])
    write_file(normalized.post(), args['outdir'], filename)
