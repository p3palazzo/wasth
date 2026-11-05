from pathlib import Path

import csv
import yaml

TSV_PATH = Path("tmp/countryInfo.tsv")
YAML_PATH = Path("src/wasth_schema/schema/classes/geonames.yaml")
ENUM_NAME = "country_code_enum"


class IndentedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


# Load the existing LinkML schema
with YAML_PATH.open(encoding="utf-8", newline="") as f:
    schema = yaml.safe_load(f)

permissible_values = {}

with TSV_PATH.open(encoding="utf-8", newline="") as f:
    reader = csv.reader(f, delimiter="\t")
    next(reader, None)  # skip header

    for row in reader:
        if not row or len(row) < 5:
            continue

        iso_code = row[0].strip()
        country_name = row[4].strip()

        # Skip GeoNames comment lines and blank/invalid rows
        if not iso_code or iso_code.startswith("#"):
            continue

        permissible_values[iso_code] = {
            "text": iso_code,
            "title": country_name,
        }

# Replace the enum's permissible values with all countries from the TSV
schema.setdefault("enums", {})
schema["enums"].setdefault(ENUM_NAME, {})
schema["enums"][ENUM_NAME]["permissible_values"] = permissible_values

# Write the updated schema with two-space list indentation and 80-column wrapping
with YAML_PATH.open("w", encoding="utf-8", newline="\n") as f:
    yaml.dump(
        schema,
        f,
        Dumper=IndentedDumper,
        sort_keys=False,
        allow_unicode=True,
        width=79,
        indent=2,
        default_flow_style=False,
    )
