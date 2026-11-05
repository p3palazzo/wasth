#!/usr/bin/env python3
"""
Replace local Place references in Work Markdown frontmatter with GeoNames IDs.

Input Work record:

    spatial:
      site:
        name:
          type: local
          refid: lugar/59V32FHX+7HV

Output Work record:

    spatial:
      site:
        name:
          type: uri
          refid: geonames:123456

The matching Place record must contain:

    id: 59V32FHX+7HV
    title: Place name
    spatial:
      site:
        location:
          lat: -12.971772
          lon: -38.501083
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import frontmatter
import numpy as np
from rapidfuzz import fuzz
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from scipy.spatial import KDTree
from tqdm import tqdm

LOGGER = logging.getLogger("wasth-lugar-to-geonames")

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class Place:
    place_id: str
    title: str
    lat: float
    lon: float
    path: Path


@dataclass(frozen=True)
class GeoName:
    geonameid: int
    name: str
    asciiname: str
    alternatenames: str
    lat: float
    lon: float
    country_code: str
    admin1_code: str | None
    admin2_code: str | None
    feature_class: str
    feature_code: str


@dataclass(frozen=True)
class Match:
    geoname: GeoName
    distance_km: float
    name_score: float
    confidence: float


class RuamelYAMLHandler(frontmatter.default_handlers.YAMLHandler):
    """YAML frontmatter handler backed by ruamel.yaml round-trip mode."""

    def __init__(self, yaml: YAML, **kwargs) -> None:
        super().__init__(**kwargs)
        self.yaml = yaml

    def load(self, stream, **kwargs):
        return self.yaml.load(stream, **kwargs)

    def export(self, metadata, **kwargs) -> str:
        kwargs.setdefault("sort_keys", False)
        buffer = StringIO()
        self.yaml.dump(metadata, buffer, **kwargs)
        return buffer.getvalue()


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)-7s %(message)s",
        stream=sys.stderr,
    )


def normalize(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^\w\s]", "", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def to_unit_sphere(lat: float, lon: float) -> tuple[float, float, float]:
    phi = math.radians(lat)
    lam = math.radians(lon)
    return (
        math.cos(phi) * math.cos(lam),
        math.cos(phi) * math.sin(lam),
        math.sin(phi),
    )


def chord_radius_for_km(radius_km: float) -> float:
    return 2 * math.sin(radius_km / (2 * EARTH_RADIUS_KM))


def load_places(
    place_dir: Path,
    allow_duplicates: bool = False,
) -> dict[str, Place]:
    paths_by_id: dict[str, list[Place]] = defaultdict(list)

    for path in sorted(place_dir.rglob("*.md")):
        try:
            post = frontmatter.load(path, handler=yaml_handler)
        except Exception as exc:
            LOGGER.warning(
                "INVALID PLACE   %s | %s: %s",
                path,
                type(exc).__name__,
                exc,
            )
            continue

        metadata = post.metadata
        place_id = metadata.get("id")
        title = metadata.get("title")

        site = metadata.get("spatial", {}).get("site", {})
        location = site.get("location", {}) if isinstance(site, dict) else {}
        lat = location.get("lat")
        lon = location.get("lon")

        if not place_id or not title or lat is None or lon is None:
            LOGGER.warning(
                "INCOMPLETE PLACE %s | id=%r title=%r lat=%r lon=%r",
                path,
                place_id,
                title,
                lat,
                lon,
            )
            continue

        place = Place(
            place_id=str(place_id),
            title=str(title),
            lat=float(lat),
            lon=float(lon),
            path=path,
        )
        paths_by_id[place.place_id].append(place)

    duplicates = {
        place_id: entries
        for place_id, entries in paths_by_id.items()
        if len(entries) > 1
    }

    if duplicates:
        for place_id, entries in sorted(duplicates.items()):
            LOGGER.error(
                "DUPLICATE PLACE ID %s (%d files):\n%s",
                place_id,
                len(entries),
                "\n".join(f"  - {entry.path}" for entry in entries),
            )

        if not allow_duplicates:
            raise SystemExit(
                f"Found {len(duplicates)} duplicate Place IDs. "
                "Resolve them or pass --allow-duplicate-place-ids."
            )

    places = {
        place_id: entries[0]
        for place_id, entries in paths_by_id.items()
    }

    return places


def load_geonames(
    tsv_path: Path,
    country_codes: set[str] | None = None,
    feature_classes: set[str] | None = None,
) -> list[GeoName]:
    records: list[GeoName] = []

    with tsv_path.open(encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            fields = line.rstrip("\n").split("\t")

            if len(fields) < 19:
                LOGGER.warning(
                    "Skipping malformed GeoNames row %d: expected at least 19 fields, found %d",
                    line_number,
                    len(fields),
                )
                continue

            try:
                record = GeoName(
                    geonameid=int(fields[0]),
                    name=fields[1],
                    asciiname=fields[2],
                    alternatenames=fields[3],
                    lat=float(fields[4]),
                    lon=float(fields[5]),
                    country_code=fields[8],
                    admin1_code=fields[10] or None,
                    admin2_code=fields[11] or None,
                    feature_class=fields[6],
                    feature_code=fields[7],
                )
            except (TypeError, ValueError) as exc:
                LOGGER.warning(
                    "Skipping invalid GeoNames row %d: %s",
                    line_number,
                    exc,
                )
                continue

            if country_codes and record.country_code not in country_codes:
                continue

            if feature_classes and record.feature_class not in feature_classes:
                continue

            records.append(record)

    return records


def build_geonames_index(
    geonames: list[GeoName],
) -> tuple[KDTree, np.ndarray]:
    coordinates = np.array(
        [to_unit_sphere(record.lat, record.lon) for record in geonames],
        dtype=np.float64,
    )
    tree = KDTree(coordinates)
    return tree, coordinates


def candidate_indices(
    tree: KDTree,
    place: Place,
    radius_km: float,
) -> list[int]:
    query_point = np.array(to_unit_sphere(place.lat, place.lon))
    return tree.query_ball_point(
        query_point,
        chord_radius_for_km(radius_km),
    )


def match_geoname(
    place: Place,
    geonames: list[GeoName],
    tree: KDTree,
    radius_km: float,
    min_name_score: float,
) -> tuple[Match | None, int]:
    indices = candidate_indices(tree, place, radius_km)
    target = normalize(place.title)

    LOGGER.debug(
        "Inspecting %s | place=%r | coords=(%.6f, %.6f) | candidates=%d",
        place.path,
        place.title,
        place.lat,
        place.lon,
        len(indices),
    )

    if not indices:
        return None, 0

    candidates: list[Match] = []

    for index in indices:
        geoname = geonames[index]
        distance_km = haversine_km(
            place.lat,
            place.lon,
            geoname.lat,
            geoname.lon,
        )

        names = [geoname.name, geoname.asciiname]
        names.extend(
            fragment.strip()
            for fragment in geoname.alternatenames.split(",")
            if fragment.strip()
        )

        name_score = max(
            (
                fuzz.token_sort_ratio(target, normalize(name))
                for name in names
            ),
            default=0.0,
        )

        if name_score < min_name_score:
            LOGGER.debug(
                "  rejected geonameid=%d name=%r distance=%.3fkm name_score=%.1f",
                geoname.geonameid,
                geoname.name,
                distance_km,
                name_score,
            )
            continue

        spatial_score = max(0.0, 1 - distance_km / radius_km)
        confidence = 0.70 * spatial_score + 0.30 * (name_score / 100)

        match = Match(
            geoname=geoname,
            distance_km=distance_km,
            name_score=name_score,
            confidence=confidence,
        )
        candidates.append(match)

        LOGGER.debug(
            "  candidate geonameid=%d name=%r distance=%.3fkm "
            "name_score=%.1f confidence=%.3f",
            geoname.geonameid,
            geoname.name,
            distance_km,
            name_score,
            confidence,
        )

    if not candidates:
        return None, len(indices)

    best_match = max(candidates, key=lambda match: match.confidence)

    LOGGER.debug(
        "  best geonameid=%d name=%r distance=%.3fkm "
        "name_score=%.1f confidence=%.3f",
        best_match.geoname.geonameid,
        best_match.geoname.name,
        best_match.distance_km,
        best_match.name_score,
        best_match.confidence,
    )

    return best_match, len(indices)


def get_site_name_node(post: frontmatter.Post) -> CommentedMap | None:
    spatial = post.metadata.get("spatial")

    if not isinstance(spatial, CommentedMap):
        return None

    site = spatial.get("site")

    if not isinstance(site, CommentedMap):
        return None

    name = site.get("name")

    return name if isinstance(name, CommentedMap) else None


def copy_to_review(review_path: Path, work_path: Path) -> None:
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        work_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def rewrite_work(
    work_path: Path,
    output_path: Path,
    review_path: Path,
    places: dict[str, Place],
    geonames: list[GeoName],
    tree: KDTree,
    radius_km: float,
    min_name_score: float,
    min_confidence: float,
    dry_run: bool,
) -> str:
    try:
        post = frontmatter.load(work_path, handler=yaml_handler)
    except Exception as exc:
        LOGGER.error(
            "FRONTMATTER ERROR %s | %s: %s",
            work_path,
            type(exc).__name__,
            exc,
        )
        if not dry_run:
            copy_to_review(review_path, work_path)
        return "frontmatter_error"

    name_node = get_site_name_node(post)

    if name_node is None:
        LOGGER.info("UNCHANGED      %s", work_path.relative_to(work_path.parents[2]))
        return "unchanged"

    refid = name_node.get("refid")

    if not isinstance(refid, str):
        LOGGER.info("UNCHANGED      %s", work_path.relative_to(work_path.parents[2]))
        return "unchanged"

    place_id = refid.removeprefix("lugar/")
    place = places.get(place_id)

    if place is None:
        LOGGER.warning(
            "MISSING PLACE  %s | refid=%s",
            work_path,
            place_id,
        )
        if not dry_run:
            copy_to_review(review_path, work_path)
        return "missing_place"

    match, candidate_count = match_geoname(
        place=place,
        geonames=geonames,
        tree=tree,
        radius_km=radius_km,
        min_name_score=min_name_score,
    )

    if match is None:
        LOGGER.warning(
            "NO MATCH       %s | place=%r | candidates=%d",
            work_path,
            place.title,
            candidate_count,
        )
        if not dry_run:
            copy_to_review(review_path, work_path)
        return "no_match"

    if match.confidence < min_confidence:
        LOGGER.warning(
            "REVIEW         %s | place=%r | geonameid=%d | "
            "distance=%.2fkm | score=%.1f | confidence=%.3f",
            work_path,
            place.title,
            match.geoname.geonameid,
            match.distance_km,
            match.name_score,
            match.confidence,
        )
        if not dry_run:
            copy_to_review(review_path, work_path)
        return "review"

    name_node["type"] = "uri"
    name_node["refid"] = f"geonames:{match.geoname.geonameid}"

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as destination:
            frontmatter.dump(
                post,
                destination,
                handler=yaml_handler,
                sort_keys=False,
            )

    LOGGER.info(
        "REPLACED       %s | lugar/%s → geonames:%d | %r | "
        "%.2fkm | confidence=%.3f",
        work_path,
        place_id,
        match.geoname.geonameid,
        match.geoname.name,
        match.distance_km,
        match.confidence,
    )

    return "replaced"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Replace local Place references in Work Markdown frontmatter "
            "with GeoNames identifiers."
        )
    )
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--place-dir", type=Path, required=True)
    parser.add_argument("--geonames-tsv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument(
        "--country",
        action="append",
        default=[],
        help="ISO 3166 country code filter; repeatable, e.g. --country BR",
    )
    parser.add_argument(
        "--feature-class",
        action="append",
        default=[],
        help=(
            "GeoNames feature-class filter; repeatable, e.g. "
            "--feature-class P for populated places"
        ),
    )
    parser.add_argument(
        "--radius-km",
        type=float,
        default=5.0,
        help="Maximum great-circle distance in kilometres (default: 5).",
    )
    parser.add_argument(
        "--min-name-score",
        type=float,
        default=70.0,
        help="Minimum fuzzy name score from 0 to 100 (default: 70).",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.85,
        help="Minimum confidence from 0 to 1 (default: 0.85).",
    )
    parser.add_argument(
        "--allow-duplicate-place-ids",
        action="store_true",
        help=(
            "Use the first Place file for each duplicated ID instead of "
            "aborting."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report matches without writing converted Work files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed candidate and matching information.",
    )
    args = parser.parse_args()

    configure_logging(args.verbose)

    if not 0 <= args.min_confidence <= 1:
        parser.error("--min-confidence must be between 0 and 1.")

    if not 0 <= args.min_name_score <= 100:
        parser.error("--min-name-score must be between 0 and 100.")

    if args.radius_km <= 0:
        parser.error("--radius-km must be greater than zero.")

    work_paths = sorted(args.work_dir.rglob("*.md"))
    LOGGER.info("Found %d Work Markdown files.", len(work_paths))

    places = load_places(
        args.place_dir,
        allow_duplicates=args.allow_duplicate_place_ids,
    )
    LOGGER.info("Loaded %d Place records.", len(places))

    countries = set(args.country) or None
    feature_classes = set(args.feature_class) or None

    geonames = load_geonames(
        args.geonames_tsv,
        country_codes=countries,
        feature_classes=feature_classes,
    )
    LOGGER.info("Loaded %d GeoNames candidate records.", len(geonames))

    if not geonames:
        raise SystemExit("No GeoNames records remained after filtering.")

    tree, _ = build_geonames_index(geonames)

    counts: Counter[str] = Counter()

    for work_path in tqdm(
        work_paths,
        desc="Matching Work records",
        unit="file",
    ):
        relative_path = work_path.relative_to(args.work_dir)
        output_path = args.output_dir / relative_path
        review_path = args.review_dir / relative_path

        try:
            result = rewrite_work(
                work_path=work_path,
                output_path=output_path,
                review_path=review_path,
                places=places,
                geonames=geonames,
                tree=tree,
                radius_km=args.radius_km,
                min_name_score=args.min_name_score,
                min_confidence=args.min_confidence,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            LOGGER.exception(
                "FAILED          %s | %s: %s",
                relative_path,
                type(exc).__name__,
                exc,
            )
            result = "failed"

        counts[result] += 1

    LOGGER.info("Summary:")
    for result, count in sorted(counts.items()):
        LOGGER.info("  %-18s %d", result, count)


if __name__ == "__main__":
    import re  # Imported here to keep the module-level import section focused.

    import frontmatter.default_handlers

    yaml_handler = RuamelYAMLHandler(
        yaml=YAML(typ="rt"),
    )
    yaml_handler.yaml.preserve_quotes = True
    yaml_handler.yaml.width = 4096
    yaml_handler.yaml.indent(mapping=2, sequence=4, offset=2)

    main()
