"""
Módulo de validação do XML: roda em importação e exportação de dados

Verifica se a tradução de/para XML é válida e conforme à especificação LIDO e
ao perfil de aplicação a obras de arquitetura.
"""

import sys
import os
import xmlschema

def create_schema() -> None:
    """Mostra problemas de estrutura dos dados

       TODO: revisar erro de validação do
       http://schemas.opengis.net/gml/3.1.1/base/referenceSystems.xsd
       chamado pelo LIDO-schema.
    """
    XML_schema = xmlschema.XMLSchema("https://lido-schema.org/schema/v1.1/lido-v1.1.xsd")
    print(XML_schema)
    XML_schema.export(target='schemata', save_remote=True)
    XML_schema = xmlschema.XMLschema("schemata/lido-v1.1.xsd")
    XML_profile = xmlschema.XMLSchema("https://lido-schema.org/profiles/v1.1/lido-v1.1-profile-architecture-v1.1.xsd")
    XML_profile.export(target='schemata', save_remote=True)
    XML_profile = xmlschema.XMLSchema("schemata/lido-v1.1-profile-architecture-v1.1.xsd")
    XML_schema = xmlschema.XMLSchema([ XML_schema, XML_profile ])
    return XML_schema

