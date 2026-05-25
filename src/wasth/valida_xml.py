"""
Módulo de validação do XML: roda em importação e exportação de dados

Verifica se a tradução de/para XML é válida e conforme à especificação LIDO e
ao perfil de aplicação a obras de arquitetura.
"""

import sys
import os
import xmlschema

def create_schema(schema_path="schemata/lido-v1.1-profile-architecture-v1.1.xsd"):
    """Mostra problemas de estrutura dos dados
    """
    schema_path = "schemata/lido-v1.1-profile-architecture-v1.1.xsd"
    if not os.path.isfile(schema_path):
        # Usamos XMLSchema11 em vez de XMLSchema por causa deste problema de
        # validação do OpenGML:
        # https://github.com/sissaschool/xmlschema/issues/425
        xml_profile = xmlschema.XMLSchema11("https://lido-schema.org/profiles/v1.1/lido-v1.1-profile-architecture-v1.1.xsd")
        xml_profile.export(target='schemata', save_remote=True)
    xml_profile = xmlschema.XMLSchema11(schema_path)
    return xml_profile
    # type: <class 'xmlschema.validators.schemas.XMLSchema11'>

def valid_xml(doc_path):
    if os.path.isfile(doc_path):
        xml_profile = create_schema()
        if xml_profile.is_valid(doc_path):
            print(f"✅ O documento '{doc_path}' é válido.")
            return True
        else:
            xml_profile.validate(doc_path)
            return False
    else:
        print("Documento não encontrado.")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        args = sys.argv[1:]
    else:
        args = input("""
Informar um caminho relativo de pasta ou nomes de arquivos/ficheiros:
(deixar em branco para cancelar a operação)
""").split()
    if args:
        if os.path.isdir(args[0]):
            from glob import glob
            filelist = glob(os.path.join(args[0]) + "*.xml")
        elif os.path.isfile(args[0]):
            filelist = args
            for file in filelist:
                try:
                    valid_xml(file)
                except:
                    print(f"""
-------------------------------------------------------------------------------

🚫 Não foi possível ler {file}""")
    else:
        print("Operação cancelada")
