import csv
import re
import unicodedata
from pathlib import Path

import yaml

class IndentedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

INPUT_DIR = Path("/Users/palazzo/Library/CloudStorage/OneDrive-unb.br–Documentação,ModelagemeConservaçãodoPatrimônio-Documentos/Arquitetura tradicional/5.10-Referências/5.10.22-Listas/sicg")
OUTPUT_DIR = Path("fichas")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

IPHAN = {
            "legal_body_type": "corporate",
            "weblink": "https://www.gov.br/iphan/",
            "title": "IPHAN",
            "id": "isni:0000000121547935",
            "identifiers": [
                {
                    "refid": "wd:Q391537",
                    "title": "Wikidata"
                }
            ]
        }
GBA_LOD1 = {
      "legal_body_type": "corporate",
      "title": "Global Building Atlas LoD1",
      "id": "doi:10.14459/2025MP1782307",
}

def ascii_slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")

def typed_identifier(refid, description=None, id_type="uri"):
    item = {"refid": refid}
    if description:
        item["description"] = description
    if id_type:
        item["type"] = id_type
    item["source"] = IPHAN
    return item

csv_files = sorted(INPUT_DIR.glob("*.csv"))
if not csv_files:
    raise FileNotFoundError(f"No *.csv files found in {INPUT_DIR}")

total = 0
for file in csv_files:

    with file.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    for row in rows:
        nome = row["Nome do Bem"].strip()
        classifica = row["Classificação"].strip()
        uf = row["UF"].strip()
        municipio = row["Município"].strip()
        codigo = "SICG " + str(row["Código IPHAN"].strip())
        sei = row["Número do SEI"].strip()
        estado_conserva = {
            "concept_name": None,
            "description": "Estado de Conservação : " + row["Estado de Conservação"],
            "source": IPHAN
        }
        estado_preserva = {
            "concept_name": None,
            "description": "Estado de Preservação : " + row["Estado de Preservação"],
            "source": IPHAN
        }
        uso_solo = {
            "concept_name": None,
            "description": "Uso do solo : " + row["Uso do solo"].strip(),
            "source": IPHAN
        }
        entorno = {
            "concept_name": None,
            "description": "Entorno : " + row["Entorno"].strip(),
            "source": IPHAN
        }
        genre = [
            {
                "concept_name": None,
                "description": classifica,
                "source": IPHAN
            }
        ]
        propriedade = row["Propriedade"].strip()

        work = {
            "title": nome,
            "title_type": "geographic",
            "category": "term:lido00096",
            "identifiers": [
                {
                    "refid": "https://sicg.iphan.gov.br/sicg/bem/visualizar/",
                    "refid_type": "uri",
                    "description": codigo,
                    "source": IPHAN,
                }
            ],
            "work_type_condition": [estado_conserva , estado_preserva],
            "work_type_context": [ uso_solo, entorno ],
            "classification_genre": genre,
            "site": {
                "site_type": "geographic",
                "name": {"geonameid": None},
                "description": municipio + "\n" + uf,
                "location": {
                    "lon": None,
                    "lat": None,
                    "alt": None,
                    "source": IPHAN,
                },
                "extent": {
                    "geometry_type": "Polygon",
                    "coordinates": None,
                    "srs_name": "EPSG:4326",
                    "source": GBA_LOD1,
                }
            },
            "work_rights": [
                {
                    "rights_type": "generic",
                    "statement": { "title": "Propriedade : " + propriedade,
                                   "source": IPHAN,
                                  },
                },
                {
                    "rights_type": "specific",
                    "statement": {
                        "refid_type": "uri",
                        "refid": "https://rightsstatements.org/vocab/NKC/1.0/",
                        "title": "Sem direito autoral conhecido",
                    }
                },
            ],
        }

        if sei:
            work["identifiers"].append(
                {
                    "refid": sei,
                    "refid_type": "local",
                    "description": "Processo SEI " + sei,
                    "source": IPHAN,
                    }
            )

        filename = f"br-{ascii_slug(uf)}-{ascii_slug(municipio)}-{ascii_slug(nome)}.md"
        output = INPUT_DIR / OUTPUT_DIR / filename

        frontmatter = yaml.dump(
            work,
            Dumper=IndentedDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
        ).rstrip()

        output.write_text(
            f"---\n{frontmatter}\n---\n",
            encoding="utf-8",
        )

    print(f"{file.name}: Wrote {len(rows)} files to {OUTPUT_DIR}")
