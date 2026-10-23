"""
Funções para obter informações geográficas das edificações.
"""
import argparse
import csv
import geojson
from geojson import utils as geojson_utils
import sys
from collections.abc import Mapping
from pathlib import Path
from rich import print as rprint

import frontmatter
import geopandas as gpd
from frontmatter.default_handlers import YAMLHandler
from ruamel.yaml import YAML

yaml = YAML(typ='rt')

def work_location(path: Path) -> gpd.GeoDataFrame | None:
    post = frontmatter.load(
        str(path),
        encoding="utf-8",
    )
    spatial = post.get('spatial')
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
    if not isinstance(lat, (float, int)) or not isinstance(lon, (float, int)):
        return None
    p = geojson.Point((lon, lat))
    if not p.is_valid:
        return None
    rprint(f'{post.title} = {p}')
    gdf = gpd.GeoDataFrame.from_features(p["features"], crs="EPSG:4674")
    return gdf

def point_in_poly(point: gpd.GeoDataFrame, poly: gpd.GeoDataFrame) -> str | None:


def main():
    parser = argparse.ArgumentParser(
        description="Find municipalities for Markdown frontmatter coordinates."
    )
    parser.add_argument(
        "--geopackage",
        type=Path,
        required=True,
        help="Path to the municipal-boundary GeoPackage.",
    )
    parser.add_argument(
        "--folder",
        type=Path,
        required=True,
        help="Folder containing Markdown files; subfolders are not scanned.",
    )
    parser.add_argument(
        "--layer",
        help="GeoPackage layer to read; omitted to use the default layer.",
    )
    parser.add_argument(
        "--name-column",
        default="nome",
        help="Municipality-name column in the layer (default: nome).",
    )
    parser.add_argument(
        "--coordinates-crs",
        default="EPSG:4674",
        help="CRS of Markdown lat/lon values (default: EPSG:4674).",
    )
    args = parser.parse_args()

    if not args.geopackage.is_file():
        parser.error(f"GeoPackage not found: {args.geopackage}")

    if not args.folder.is_dir():
        parser.error(f"Folder not found: {args.folder}")

    read_options = {"layer": args.layer} if args.layer else {}
    municipalities = gpd.read_file(args.geopackage, **read_options)

    if municipalities.crs is None:
        parser.error("The municipality layer has no CRS metadata.")

    if args.name_column not in municipalities.columns:
        parser.error(
            f"Column {args.name_column!r} not found. "
            f"Available columns: {', '.join(municipalities.columns)}"
        )

    if municipalities.empty:
        parser.error("The municipality layer is empty.")

    geometry = municipalities.geometry
    if (
        geometry.isna().any()
        or geometry.is_empty.any()
        or not geometry.is_valid.all()
        or not geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all()
    ):
        parser.error(
            "The layer must contain nonempty, valid Polygon/MultiPolygon "
            "geometries. Repair or filter the source layer first."
        )

    # Normalize column names to avoid conflicts during the spatial join.
    boundaries = gpd.GeoDataFrame(
        {"municipality": municipalities[args.name_column].to_numpy()},
        geometry=list(geometry),
        crs=municipalities.crs,
    )

    files = sorted(
        path for path in args.folder.iterdir()
        if path.is_file() and path.suffix.lower() == ".md"
    )

    results = []
    valid_rows = []

    for path in files:
        row = {
            "file": path.name,
            "location": {},
            "municipality": "",
            "status": "",
            "detail": "",
        }
        results.append(row)

        try:
            p = work_location(path)
            row.update(location=p)
            valid_rows.append(len(results) - 1)
        except Exception as exc:
            row.update(status="invalid_metadata", detail=str(exc))

    if valid_rows:
        points = gpd.GeoDataFrame(
            {"row_id": valid_rows},
            geometry=gpd.points_from_features(
                [results[i]["features"] for i in valid_rows]
            ),
            crs=args.coordinates_crs,
        ).to_crs(boundaries.crs)

        joined = gpd.sjoin(
            points,
            boundaries,
            how="left",
            predicate="intersects",
        )

        for row_id, matches in joined.groupby("row_id", sort=False):
            matched = matches.loc[matches["index_right"].notna()]
            row = results[int(row_id)]

            if matched.empty:
                row["status"] = "not_found"
            else:
                names = sorted({
                    str(name)
                    for name in matched["municipality"].dropna()
                })
                row["municipality"] = " | ".join(names)

                if len(matched) > 1:
                    row["status"] = "multiple_matches"
                    row["detail"] = (
                        "Point intersects multiple boundary features."
                    )
                elif not names:
                    row["status"] = "missing_name"
                else:
                    row["status"] = "matched"

    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=[
            "file", "lat", "lon", "municipality", "status", "detail"
        ],
    )
    writer.writeheader()
    writer.writerows(results)


if __name__ == "__main__":
    main()
