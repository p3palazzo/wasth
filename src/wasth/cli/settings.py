import json
from pathlib import Path
from typing import Any

import typer

APP_NAME = "wasth"
DEFAULT_CONFIG = "config.json"


def app_dir_config(config_file_name: str | None = None) -> Path:
    """Return the WASTH user configuration file path."""
    app_dir = Path(typer.get_app_dir(APP_NAME))
    app_dir.mkdir(parents=True, exist_ok=True)
    if not config_file_name:
        config_file_name = DEFAULT_CONFIG
    return app_dir / config_file_name


def load_settings(user_path: Path = app_dir_config()) -> dict[str, Any]:
    """Load persisted user settings, returning an empty mapping if absent."""
    if not user_path or not user_path.is_file():
        return {}

    try:
        return json.loads(user_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise typer.BadParameter(
            f"Não foi possível ler {user_path}: {error}"
        ) from error


def save_settings(settings: dict[str, Any]) -> Path:
    """Persist user settings to the WASTH configuration directory."""
    path = app_dir_config()
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
