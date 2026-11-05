from pathlib import Path

import csv
import yaml

TSV_PATH = Path("tmp/featureCodes_en.txt")
YAML_PATH = Path("src/wasth_schema/schema/classes/geonames.yaml")
ENUM_NAME = "feature_code_enum"

# Load the existing LinkML schema
with YAML_PATH.open(encoding="utf-8") as f:
    schema = yaml.safe_load(f)

# Read the GeoNames feature-code TSV
with TSV_PATH.open(encoding="utf-8") as f:
    rows = list(csv.reader(f, delimiter="\t"))

permissible_values = {}

for row in rows:
    if not row or len(row) < 3:
        continue

    full_code, name, description = (field.strip() for field in row[:3])
    code = full_code.split(".")[-1]  # T.MT -> MT

    permissible_values[code] = {
        "title": name,
        "description": description,
    }

# Ensure the enum exists, then replace only its permissible values
schema.setdefault("enums", {})
schema["enums"].setdefault(ENUM_NAME, {})
schema["enums"][ENUM_NAME]["permissible_values"] = permissible_values

# Write the updated schema
with YAML_PATH.open("w", encoding="utf-8") as f:
    yaml.safe_dump(schema, f, sort_keys=False, allow_unicode=True)
