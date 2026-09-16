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
from geojson import utils as geojson_utils
from openlocationcode import openlocationcode
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS
from rich import print as rprint
from ruamel.yaml import YAML
from unidecode import unidecode

from wasth.core import normalize

yaml = YAML(typ='safe')

class Thing(frontmatter.Post):
    """Esta classe define o arcabouço de dados e os métodos comuns a todas as
    classes de objetos do projeto WASTH: Work (obras de arquitetura), Place
    (lugares), e Concept (itens de vocabulário).
    Ela é baseada na classe Post do pacote frontmatter, um objeto que contém um
    bloco de metadados Post['metadata'], cujos elementos são também acessíveis
    diretamente por suas palavras-chave, e um bloco de conteúdo Post['content'].

    Esta classe apresenta dois métodos para criar um objeto:
    """
    def __init__(self, content: str = '', handler=None, **metadata) -> None:
        super().__init__(content=content, handler=handler, **metadata)

    @classmethod
    def from_file(cls, f: Path | str) -> "Thing":
        """Gera o objeto a partir de um arquivo/ficheiro.

        :param f: Caminho para um arquivo/ficheiro no sistema local, \
        em formato Markdown com um bloco (frontmatter) em formato YAML.
        :type f: str | Path
        :returns: Um objeto em forma de dicionário que pode ser convertido, \
        no todo ou em parte, para vários outros tipos de objetos \
        ou reexportado para Markdown.
        :rtype: Thing
        """
        if isinstance(f, Path):
            file = str(f)
        elif isinstance(f, str):
            file = f
        post = frontmatter.load(file)
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

    def validation_errors(self) -> dict | None:
        """Verifica se a ficha tem título, autor, data e id

        :returns: True se a ficha estiver em ordem, False se tiver problemas.
        :rtype: bool
        """
        required = ("title", "author", "date", "id")
        missing = [
            key for key in required
            if key not in self.metadata
            or self.metadata[key] in (None, "")
        ]
        errors = {}

        title = self.get('title')
        if "title" not in missing and not isinstance(title, str):
            errors['title'] = f"Formato inválido: {type(title)}."

        author = self.get('author')
        if "author" not in missing and not isinstance(author, str):
            errors['author'] = f"Formato inválido: {type(author)}."
        if isinstance(author, str):
            author_checksum = normalize.orcid_checksum(author) if author else None
            if author_checksum:
                author = author_checksum
        else:
            errors['author'] = f"ORCiD inválido: {author}."

        meta_date = self.get('date')
        if "date" not in missing:
            if not isinstance(meta_date, str):
                errors['date'] = f"Formato inválido: {type(meta_date)}."
            elif isinstance(meta_date, str):
                try:
                    date.fromisoformat(meta_date)
                except ValueError as e:
                    errors['date'] = (
                        f"{meta_date} Não é uma data válida: {e}."
                    )

        meta_id = self.get('id')
        if "id" not in missing:
            if not isinstance(meta_id, str):
                errors['id'] = f"Formato inválido: {type(meta_id)}."
            elif self.get('spatial'):
                location = self.location()
                if isinstance(location, geojson.Point):
                    check_id = self.olc_id()
                    if meta_id != check_id:
                        errors['id'] = (
f"ID existente {meta_id} difere do ID computado {check_id}."
                        )

        if missing:
            errors['missing'] = missing
        return errors if errors else None

    def valid(self) -> bool:
        return not self.validation_errors()

    def location(self) -> geojson.Point | None:
        """Cria um objeto ponto geográfico a partir de `spatial.site.location`.

        :returns: Um único ponto com a localização atual do objeto.
        :rtype: geoJSON.Point
        """
        spatial = self.get('spatial')
        if not isinstance(spatial, dict):
            return None
        site = spatial.get('site')
        if not isinstance(site, dict):
            return None
        location = site.get('location')
        if not isinstance(location, dict):
            return None
        lat = location.get('lat')
        lon = location.get('lon')
        alt = location.get('alt')
        if not isinstance(lat, (float, int)) or not isinstance(lon, (float, int)):
            return None
        if not isinstance(alt, (float, int)):
            p = geojson.Point((lon, lat))
        else:
            p = geojson.Point((lon, lat, alt))
        if p.is_valid:
            return p
        else:
            return None

    def extent(self) -> geojson.Polygon | geojson.MultiPolygon | None:
        spatial = self.get('spatial')
        if not isinstance(spatial, dict):
            return None
        site = spatial.get('site')
        if not isinstance(site, dict):
            return None
        extent = site.get('location')
        if not isinstance(extent, dict):
            return None
        geometry_type = extent.get('type')
        coords = extent.get('coordinates')
        if not isinstance(geometry_type, str) or \
            not isinstance(coords, str):
            return None
        if geometry_type == "Polygon":
            p = geojson.Polygon(coords)
        elif geometry_type == "MultiPolygon":
            p = geojson.MultiPolygon(coords)
        else:
            return None
        if p.is_valid:
            return p
        else:
            return None

    def olc_id(self) -> str | None:
        """
        Processa entradas de georreferenciamento

        Gera ID no formato Open Location Code a partir da latitude e longitude
        inseridas na ficha ou na interface.
        """
        location = self.location()
        if not isinstance(location, geojson.Point):
            return None
        (lon, lat) = geojson_utils.coords(location)
        if lat is None or lon is None:
            return None
        return openlocationcode.encode(lat, lon, 11)

class Work(Thing):
    """Arcabouço dos dados e métodos das fichas de obras.
    """
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
    """Define a ficha de lugares como variante da ficha de obra e fornece
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

class Concept(Thing):
    """Define um conceito de vocabulário controlado compatível com SKOS:THES.

    Fornece métodos para importar e exportar RDF:XML e JSON-LD.
    """
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
    output_path: Path

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
