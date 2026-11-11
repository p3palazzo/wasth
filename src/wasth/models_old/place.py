import datetime

import geojson
from openlocationcode import openlocationcode
from pydantic_extra_types.coordinate import Latitude, Longitude
from pydantic_extra_types.country import CountryAlpha2

from .refs import *
from .thing import Thing


class Place(Thing):
    """Define a ficha de lugares como variante da ficha de obra e fornece
    os métodos adicionais:

    - Gera ou atualiza a partir da base cartográfica do IBGE;
    - Gera ou atualiza a partir da toponímia de Portugal continental do DGT.
    """
    location: None
    extent: None
    part_of: Place | None = None

    @classmethod
    def from_ibge_bc250(
        cls,
        feature: geojson.Feature,
        orcid: str | None = None
    ) -> "Place | None":
        """Gera fichas a partir de geojson.Feature

Esta função recebe a base cartográfica do IBGE na escala 1:250.000 (BC250)
processada no QGIS (ou outro programa de geoprocessamento), onde:

1. As tabelas de pontos das localidades foram sobrepostas à extensão dos
   municípios (coluna municipio_nome) e das unidades da federação (coluna
   uf_sigla);
2. As layers dos diferentes tipos de localidades foram reunidas numa só,
   convertida para EPSG:4326 (WGS84) e exportada para geoJSON.

A função realiza as seguintes operações:

1. Verifica se os dados indispensáveis estão presentes;
2. Converte o nome da localidade e as coordenadas do ponto em mapas de
    metadados segundo o esquema dos documentários de arquitetura tradicional
    (data/schema.yaml), compatível com a especificação LIDO;
3. Gera um ID a partir do Open Location Code das coordenadas do ponto;
4. Gera o vocabulário controlado para work_type:context a partir dos tipos de
   povoação, usando o vocabulário do Wikidata;
5. Insere as relações partitivas com o município e a unidade da federação no
   dicionário repository.
        """
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        if feature.get('type') != 'Feature' or not props or not geom:
            return None
        if geom.get('type') != 'Point':
            return None
        coords = geom.get('coordinates', [])
        if not isinstance(coords, (list, tuple)) or len(coords) < 2:
            return None
        olc_code = openlocationcode.encode(coords[1], coords[0], 11)
        created_date = datetime.date.today()

        br: LIDORepository = {
            'type': 'site',
            'display': 'Brasil',
            'id': {
                'type': 'uri',
                'display': 'BR',
                'refid': 'https://www.wikidata.org/wiki/Q155',
            },
        }
        uf: LIDORepository = {
            'type': 'site',
            'display': props['uf_nome'].strip(),
            'id': {
                'type': 'uri',
                'display': props['uf_sigla'].strip(),
                'refid': props['uf_uri'].strip(),
            },
            'part_of': br,
        }
        municipio: LIDORepository = {
            'type': 'site',
            'display': props['municipio_nome'].strip(),
            'part_of': uf,
        }

        metadata = {
            'title': props.get('nome', str).strip(),
            'title_type': 'repository',
            'id': olc_code,
            'date': created_date,
            'author': orcid,
            'spatial': [
                {
                    'type': 'site',
                    'location': {
                        'lat': coords[1],
                        'lon': coords[0],
                    },
                    'srsName': {
                        'type': 'uri',
                        'refid': 'http://www.opengis.net/def/crs/EPSG/0/4326',
                        'display': 'EPSG:4326 WGS84',
                    },
                    'in_path': {
                        'type': 'corporate',
                        'display': 'IBGE',
                        'term': {
                            'type': 'uri',
                            'refid': 'https://www.wikidata.org/wiki/Q268072',
                            'display': 'Instituto Brasileiro de Geografia e Estatística',
                        },
                    },
                },
            ],
            'repository': [ municipio ],
        }

        if isinstance(props.get('geocodigo'), str):
            geocodigo = {
                    'term': {
                        'type': 'local',
                        'refid': props['geocodigo'].strip(),
                    },
                    'in_path': {
                        'type': 'corporate',
                        'display': 'IBGE',
                        'term': {
                            'type': 'uri',
                            'refid': 'https://www.wikidata.org/wiki/Q268072',
                            'display': 'IBGE, base cartográfica 1:250.000 2026-03-03',
                        }
                    }
                }
            metadata['identifiers'] = [geocodigo]

        context_refid = 'https://www.wikidata.org/wiki/Q486972'
        context_display = 'sítio habitado'
        function_refid = 'https://www.wikidata.org/wiki/Q98929991'
        function_display = 'lugar'
        match props.get('layer'):
            case 'lml_aglomerado_rural_p':
                context_refid = 'https://www.wikidata.org/wiki/Q10354598'
                context_display = 'aglomerado rural'
            case 'lml_vila_p':
                context_refid = 'https://www.wikidata.org/wiki/Q3957'
                context_display = 'vila'
            case 'lml_cidade_p':
                context_refid = 'https://www.wikidata.org/wiki/Q515'
                context_display = 'cidade'
                function_refid = 'https://www.wikidata.org/wiki/Q15303838'
                function_display = 'sede de município'
            case 'lml_capital_p':
                context_refid = 'https://www.wikidata.org/wiki/Q515'
                context_display = 'cidade'
            case 'lml_aglomerado_rural_isolado_p':
                context_refid = 'https://www.wikidata.org/wiki/Q10354598'
            case _:
                context_display = 'sítio habitado'
                context_refid = 'https://www.wikidata.org/wiki/Q486972'
        if props.get('tipoaglomrurisol'):
            context_display = props['tipoaglomrurisol'].lower()
            match props['tipoaglomrurisol'].strip().casefold():
                case 'povoado':
                    context_refid = 'https://www.wikidata.org/wiki/Q532'
                case 'núcleo':
                    context_refid = 'https://www.wikidata.org/wiki/Q3257686'
                case 'lugarejo':
                    context_refid = 'https://www.wikidata.org/wiki/Q55504400'
                case 'outros aglomerados rurais isolados':
                    context_refid = 'https://www.wikidata.org/wiki/Q10354598'
                case _:
                    context_display = 'sítio habitado'
                    context_refid = 'https://www.wikidata.org/wiki/Q486972'
        if props.get('tipocapital'):
            function_display = props['tipocapital'].lower()
            match props['tipocapital']:
                case 'Capital estadual':
                    function_refid = 'https://www.wikidata.org/wiki/Q11271835'
                case 'Capital federal':
                    function_refid = 'https://www.wikidata.org/wiki/Q108178728'
                case _:
                    function_display = 'capital'
                    function_refid = 'https://www.wikidata.org/wiki/Q5119'
        metadata['work_type'] = {
            'context': {
                'type': 'uri',
                'refid': context_refid,
                'display': context_display,
            },
            'function': {
                'type': 'uri',
                'refid': function_refid,
                'display': function_display,
            },
        }

        return cls(content='', **metadata)

    def slug(self) -> str | None:
        """Gera o nome do arquivo a ser gravado.

        Unidade da Federação ou distrito usando o padrão ISO 3166:2 seguido de
        nome do município ou concelho e nome da localidade.
        Os acentos gráficos em oxítonas são convertidos segundo a convenção
        telegráfica para evitar ambiguidades em nomes de lugares
        (por exemplo, Paraná vs Paranã).
        """
        repos = self.get('repository', [])
        if not repos:
            return None
        for r in repos:
            if r.get('type') != 'site':
                continue
            parts = walk_repo(r)
            title = self.get('title')
            if isinstance(title, str) and title.strip():
                if not parts or title != parts[-1]:
                    parts.append(title)
            slug = [ pt_ascii(p) for p in parts if pt_ascii(p) ]
            if slug:
                return "-".join(slug)
        return None
