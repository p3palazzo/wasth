import geojson
from geojson import utils as geojson_utils
from openlocationcode import openlocationcode

from .refs import *
from .thing import Thing


class Work(Thing):
    """Arcabouço dos dados e métodos das fichas de obras.
    """
    format: None
    spatial: Spatial
    relation: list[LIDORelation] | None = None

    def location(self) -> geojson.Point | None:
        """Cria um objeto ponto geográfico a partir de `spatial.site.location`.

        :returns: Um único ponto com a localização atual do objeto.
        :rtype: geoJSON.Point
        """
        spatial = self.spatial
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
        spatial = self.spatial
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
