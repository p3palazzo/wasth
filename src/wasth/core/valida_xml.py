"""
Módulo de validação do XML: roda em importação e exportação de dados

Verifica se a tradução de/para XML é válida e conforme à especificação LIDO e
ao perfil de aplicação a obras de arquitetura.
"""

import os
from pathlib import Path

import xmlschema
from rich import print as rprint


def create_schema(
    schema_path: str = "data/xml/lido-v1.1-profile-architecture-v1.1.xsd",
) -> xmlschema.XMLSchema11:
    """Mostra problemas de estrutura dos dados"""
    root_dir = Path(__file__).resolve().parent.parent
    abs_path = os.path.join(root_dir, schema_path)
    if not os.path.isfile(abs_path):
        # Usamos XMLSchema11 em vez de XMLSchema por causa deste problema de
        # validação do OpenGML:
        # https://github.com/sissaschool/xmlschema/issues/425
        xml_profile = xmlschema.XMLSchema11(
"https://lido-schema.org/profiles/v1.1/lido-v1.1-profile-architecture-v1.1.xsd"
        )
        xml_profile.export(target=os.path.dirname(abs_path), save_remote=True)
        return xml_profile
    xml_profile = xmlschema.XMLSchema11(abs_path)
    return xml_profile
    # type: <class 'xmlschema.validators.schemas.XMLSchema11'>


def valid_xml(
    doc_path: Path | None = None,
    xml_profile: xmlschema.validators.schemas.XMLSchema11 = create_schema(),
    encoding: str = "utf-8",
) -> bool | None:
    """Valida um arquivo XML contra especificação XSD"""
    if not doc_path or not doc_path.is_file():
        doc_path = Path(input("Informar um caminho de arquivo/ficheiro."))
        if not doc_path or not doc_path.is_file():
            rprint(f":x:  {str(doc_path)} não é um caminho válido, cancelando.")
            return None
    document = doc_path.read_text(encoding=encoding)
    if xml_profile.is_valid(document):
        rprint(f":white_check_mark: O documento '{str(doc_path)}' é válido.")
    else:
        xml_profile.validate(document)
    return xml_profile.is_valid(document)
