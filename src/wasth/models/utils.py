import re

from unidecode import unidecode

from .refs import *


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

def walk_repo(repo: LIDORepository) -> list[str]:
    """Gera hierarquia de nomes de repositórios para uso em slugs usando repo_label().
    """
    hierarchy: list[str] = []
    current: LIDORepository | None = repo
    while current is not None:
        label = repo_label(current)
        if label:
            hierarchy.append(label)
        current = current.part_of
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
    text = re.sub(r"ão\b", "aon", text)
    text = re.sub(r"ã\b", "an", text)
    text = re.sub(r"ões\b", "oens", text)
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
