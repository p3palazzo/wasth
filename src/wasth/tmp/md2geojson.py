from argparse import ArgumentParser
from pathlib import Path

import frontmatter
import geojson
from ruamel.yaml import YAML

yaml = YAML(typ='rt')

def main() -> Path | None:
    parser = ArgumentParser(
        description = 'Create geoJSON from spatial data in frontmatter.'
    )
    parser.add_argument(
        '--source',
        type=Path,
        required=True,
        help="Path to folder containing source markdown files"
    )
    parser.add_argument(
        "--dest",
        type=Path,
        help="Path to destination .geojson file, omit to use source folder name."
    )

    args = parser.parse_args()

    if not args.source.is_dir():
        parser.error(f"{args.source} não é uma pasta.")

    if args.dest:
        dest_file = args.dest
        if args.dest.suffix != ".geojson":
            parser.error(f"{args.dest} deve ser um arquivo .geojson")
    else:
        dest_path = args.source / args.source.name
        dest_file = dest_path.with_suffix('.geojson')


    features = []
    source = Path(args.source).glob('*.md')
    filelist = [f for f in source if f.is_file()]

    for f in filelist:
        if f.stem.isupper():
            continue
        post = frontmatter.load(f)

        ##############################################
        # 🛑 FORMATO ANTIGO spatial.site.location.
        # MIGRAR PARA FORMATO NOVO site.location
        # quando tivermos migrado as fichas.
        ##############################################
        if not post.get('spatial'):
            print(f"🚫  {f} não tem espacialização.")
            continue
        spatial = post['spatial']
        if not spatial.get('site'):
            print(f"⚠️  {f} não tem sítio.")
            continue
        site = spatial['site']
        ##############################################
        # 🛑 FIM DA PARTE QUE PRECISA SER MIGRADA.
        ##############################################
        if not site.get('location'):
            print(f"📵  {f} não tem locação.")
            continue

        slug_parts = f.stem.split('-')
        country_code = slug_parts[0].upper()
        state = slug_parts[1].upper()
        iso3166_2 = str(country_code + '-' + state).upper()
        city = slug_parts[2].replace("_", " ").title()
        location = site.get('location')
        lon = location.get('lon')
        lat = location.get('lat')

        if not (lon and lat):
            print(f"❓  {f} não tem coordenadas.")
            continue
        point = geojson.Point((lon, lat))
        site_name = None
        site_olc = None
        post_id = None
        if post.get('id'):
            post_id = post['id']
        if site.get('name'):
            if site['name'].get('display'):
                site_name = site['name']['display']
            if site['name'].get('refid'):
                site_full_id = site['name']['refid']
                site_olc = site_full_id.split('/')[-1]
        feature = geojson.Feature(
            geometry = point,
            properties = {
                "title": post['title'],
                "slug": f.stem,
                "id": post_id,
                "country_code_from_slug": country_code,
                "state_from_slug": state,
                "iso3166_2": iso3166_2,
                "muni_from_slug": city,
                "site_name": site_name,
                "site_olc": site_olc,
            }
        )
        if not feature.is_valid:
            print(f"❌  {f}: georreferenciamento inválido")
            continue
        features.append(feature)
        print(f"✅  {f} acrescentado a {dest_file}")

    if not features:
        print("Nenhum sítio georreferenciado.")
        return None
    collection = geojson.FeatureCollection(features)
    if not collection.is_valid:
        print("Nenhum sítio georreferenciado.")
        return None
    with dest_file.open('w', encoding='utf-8') as dest:
        geojson.dump(collection, dest)
        return dest_file

if __name__ == "__main__":
    raise SystemExit(main())
