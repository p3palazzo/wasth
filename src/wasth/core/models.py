"""Modelos de objeto usados no WASTH, especialmente a ficha de obra"""

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Required, TypedDict

import frontmatter
import geojson
import yamale
from openlocationcode import openlocationcode
from rich import print
from ruamel.yaml import YAML
from unidecode import unidecode

yaml = YAML(typ='safe')

class Thing(frontmatter.Post):
    """Esta classe define o arcabouço de dados e os métodos comuns a todas as
    classes de objetos do projeto WASTH: Work (obras de arquitetura), Place
    (lugares), e Term (termos de vocabulário).
    Ela é baseada na classe Post do pacote frontmatter, um objeto que contém um
    bloco de metadados Post['metadata'], cujos elementos são também acessíveis
    diretamente por suas palavras-chave, e um bloco de conteúdo Post['content'].

    Esta classe apresenta dois métodos para criar um objeto:
    """
    def __init__(self, content: str = '', handler=None, **metadata) -> None:
        super().__init__(content=content, handler=handler, **metadata)

    @classmethod
    def from_file(cls, f: str) -> "Thing":
        """Gera o objeto a partir de um arquivo/ficheiro.

        :param f: Caminho para um arquivo/ficheiro no sistema local, em formato Markdown com um bloco (frontmatter) em formato YAML.
        :type f: str
        :returns: Um objeto em forma de dicionário que pode ser convertido, no todo ou em parte, para vários outros tipos de objetos ou reexportado para Markdown.
        :rtype: Thing
        """
        post = frontmatter.load(f)
        return cls(content=post.content, handler=post.handler, **post.metadata)

    @classmethod
    def from_post(cls, post: frontmatter.Post) -> "Thing":
        """Gera o objeto a partir de um objeto frontmatter.Post

        :param post: Um objeto já processado a partir de um documento Markdown com frontmatter YAML.
        :type post: frontmatter.Post
        :return: Um objeto em forma de dicionário que pode ser convertido, no todo ou em parte, para vários outros tipos de objetos ou reexportado para Markdown.
        :rtype: Thing
        """
        return cls(content=post.content, handler=post.handler, **post.metadata)


class Work(Thing):
    """Arcabouço dos dados e métodos das fichas de obras.
    """
    def places(self) -> geojson.FeatureCollection | None:
        """Cria geoJSON a partir de 'spatial'"""
        spatial = self.get('spatial')
        if not spatial:
            raise ValueError(
                ":globe_with_meridians::w:  A obra não está georreferenciada."
            )
        places = []
        for place in spatial:
            props = {
                'type': place.get('type') or 'site',
            }
            if place.get('display'):
                props['display'] = place['display']
            if place.get('zoom'):
                props['zoom'] = place['zoom']
            if place.get('location'):
                location = place.get('location')
                lat = location.get('lat')
                lon = location.get('lon')
                alt = location.get('alt')
                if lat is None or lon is None:
                    raise ValueError(
                ":globe_with_meridians::x:  Latitude e/ou longitude ausentes."
                    )
                if alt is not None:
                    geom = geojson.Point((lon, lat, alt))
                else:
                    geom = geojson.Point((lon, lat))
            elif place.get('extent'):
                extent = place['extent']
                coords = extent.get('coordinates')
                geom_type = extent.get('type') or 'Polygon'
                if geom_type == 'Polygon':
                    geom = geojson.Polygon(coords)
                elif geom_type == 'MultiPolygon':
                    geom = geojson.MultiPolygon(coords)
                else:
                    raise ValueError(
f":globe_with_meridians::x:  {geom_type} não é um tipo de geometria válido."
                                     )
            else:
                raise ValueError(
":globe_with_meridians::x:  Dados de georreferenciamento inexistentes."
                                 )
            feature = geojson.Feature(geometry=geom, properties=props)
            if feature.is_valid:
                places.append(feature)
            else:
                raise ValueError(f"""
:globe_with_meridians::x:  Dados de georreferenciamento inválidos:
{feature.errors()}
                    """)
        return geojson.FeatureCollection(places)

    def olc_id(self) -> str | None:
        """
        Processa entradas de georreferenciamento

        Gera ID no formato Open Location Code a partir da latitude e longitude
        inseridas na ficha ou na interface.
        """
        spatial = self.get('spatial', [])
        if spatial is None:
            return None
        for place in spatial:
            if place.get('type') != "site":
                continue
            location = place.get('location')
            if not location:
                continue
            lat = location.get('lat')
            lon = location.get('lon')
            if lat is None or lon is None:
                continue
            return openlocationcode.encode(lat, lon, 11)

    def valida(
        self,
        schema_file: str = "data/schema.yaml",
        parser: str = "ruamel",
        encoding: str = 'utf-8'
    ) -> None:
        """Valida os dados do objeto contra o esquema usando Yamale"""
        root_dir = Path(__file__).resolve().parent.parent
        schema_path = os.path.join(root_dir, schema_file)
        with open(schema_path, 'r', encoding=encoding) as f:
            schema = f.read()
        schema = yamale.make_schema(content=schema, parser=parser)
        content = yaml.dump(self.metadata)
        data = yamale.make_data(content=content, parser=parser)
        yamale.validate(schema, data)

class Place(Thing):
    """
    Define a ficha de lugares como variante da ficha de obra e fornece
    os métodos adicionais:

    - Gera ou atualiza a partir da base cartográfica do IBGE;
    - Gera ou atualiza a partir da toponímia de Portugal continental do DGT.
    """
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
        created_date = date.today()

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
                    'source': {
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
                    'source': {
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
Os acentos gráficos em oxítonas são convertidos segundo a convenção telegráfica
para evitar ambiguidades em nomes de lugares (por exemplo, Paraná vs Paranã).
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

class Concept(Thing):
    pass

class LIDORepository(TypedDict, total=False):
    """Definição de um repositório (continente jurídico) nas fichas de obra"""
    type: Required[str]
    display: str
    name: dict
    id: dict
    part_of: LIDORepository

class InOutPaths(TypedDict):
    """Contém uma lista de arquivos/ficheiros de entrada e uma pasta de saída."""
    filelist: list[Path]
    output_dir: Path

def repo_label(repo: LIDORepository) -> str | None:
    """Gera nome do repositório para uso em slugs."""
    repo_id = repo.get('id', {})
    if isinstance(repo_id, dict):
        code = repo_id.get('display')
        if isinstance(code, str) and code.strip():
            return code.strip()
    repo_display = repo.get('display')
    if isinstance(repo_display, str) and repo_display.strip():
        return repo_display
    return None

def walk_repo(repo: LIDORepository) -> list[str] | None:
    """Gera hierarquia de nomes de repositórios para uso em slugs usando repo_label().
    """
    hierarchy = []
    current = repo
    while current:
        label = repo_label(current)
        if label:
            hierarchy.append(label)
            current = current.get('part_of')
    hierarchy.reverse()
    return hierarchy

def pt_ascii(text: str) -> str:
    """Normaliza nomes sem acentos, usando convenções telegráficas."""
    text = text.strip().casefold()
    # text = re.sub(r"\b(da|de|das|dos|e|em|na|no|nos)\b", "", text)
    # text = re.sub(r"\bcasal\b", "c", text)
    text = re.sub(r"\b(são|sant[ao])\b", "s", text)
    text = re.sub(r"\bvila\b", "v", text)
    text = re.sub(r"\bcapitã[o]?\b", "cap", text)
    text = re.sub(r"\bmajor\b", "maj", text)
    text = re.sub(r"\bcomendador[a]?\b", "com", text)
    text = re.sub(r"\bcoronel\b", "cel", text)
    text = re.sub(r"\bgeneral\b", "gal", text)
    text = re.sub(r"\balmirante\b", "alm", text)
    text = re.sub(r"\bmarechal\b", "mal", text)
    text = re.sub(r"\bconselheir[ao]\b", "cons", text)
    text = re.sub(r"\bministr[ao]\b", "min", text)
    text = re.sub(r"\bpresidente\b", "pres", text)
    text = re.sub(r"\b(dom|dona)\b", "d", text)
    text = re.sub(r"\bpadre\b", "pe", text)
    text = re.sub(r"ã\b", "an", text)
    text = re.sub(r"õ\b", "on", text)
    text = re.sub(r"(?<=[aeiou])á\b", "ha", text)
    text = re.sub(r"(?<=[aeiou])é\b", "he", text)
    text = re.sub(r"(?<=[aeiou])í\b", "hi", text)
    text = re.sub(r"(?<=[aeiou])ó\b", "ho", text)
    text = re.sub(r"(?<=[aeiou])ú\b", "hu", text)
    text = re.sub(r"á\b", "ah", text)
    text = re.sub(r"é\b", "eh", text)
    text = re.sub(r"í\b", "ih", text)
    text = re.sub(r"ó\b", "oh", text)
    text = re.sub(r"ú\b", "uh", text)
    text = unidecode(text)
    text = re.sub(r"[^\w]+", "_", text)
    text = re.sub(r"_[_-]+", "_", text)
    return text.strip("_-")

def paths(
    args: list[str] | None = None,
    overwrite: bool | None = None,
    filetype: str = '.md'
) -> InOutPaths | None:
    """Gera os nomes de arquivos de entrada e a pasta de saída a partir da
    entrada do usuário.

    Primeiro argumento: caminho de entrada (arquivo/ficheiro ou pasta)
    Segundo argumento: caminho de saída (pasta), opcional;
    se for deixado em branco sobrescreve o existente.
    """
    if not args:
        if 2 <= len(sys.argv) <= 3:
            args = sys.argv[1:]
        else:
            args = input("""
Informar um caminho de arquivo/ficheiro ou pasta de leitura
e opcionalmente uma pasta de gravação.
Omitir a pasta de gravação sobrescreve os arquivos/ficheiros existentes.
                """).strip().split()
    if not args:
        print("Operação cancelada.")
        return None
    source = Path(args[0])
    if len(args) == 1:
        if overwrite is None:
            prompt = input(
                ":warning:  Sobrescrever arquivos/ficheiros existentes? s/n"
            ).strip().casefold()
            overwrite = prompt in { "s", "sim", "y", "yes", "sobrescrever" }
        if overwrite is False:
            print("Operação cancelada.")
            return None
    if len(args) > 2:
        raise OSError("Número excessivo de argumentos.")
    if len(args) == 2 and Path(args[1]).is_file():
        raise OSError("O segundo argumento deve ser uma pasta ou ser omitido.")
    if source.is_dir():
        filelist = [
            source.joinpath(f)
            for f in source.iterdir()
            if source.joinpath(f).is_file()
            and source.joinpath(f).suffix == filetype
        ]
        if len(filelist) == 0:
            print(f"""
:x:  Nenhum arquivo/ficheiro no formato {filetype} encontrado.
            """)
            return None
        output_dir = Path(args[1]) if len(args) == 2 else source
        return { 'filelist': filelist, 'output_dir': output_dir }
    output_dir = Path(args[1]) if len(args) == 2\
        else source.resolve().parent
    return { 'filelist': [source], 'output_dir': output_dir}

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
        post: frontmatter.Post | Work | Place | Concept,
        output_dir: Path,
        filename: Path
) -> Path | None:
    """Grava cada arquivo/ficheiro conforme nome e pasta recebidos.

    :returns: Caminho onde o documento foi gravado, ou nada.
    :rtype: Path
    """
    try:
        dest = Path(output_dir) / Path(filename)
        frontmatter.dump(post, dest, sort_keys=False)
        print(f"""
:card_index:  {post.get('id')} --- [bold]{post.get('title')}[/bold]
   gravado em '{str(dest)}'
        """)
        return dest
    except Exception as e:
        raise OSError(f"""
:x:  Erro na escrita em '{str(output_dir)}/{str(filename)}':\n {e}
        """) from e
