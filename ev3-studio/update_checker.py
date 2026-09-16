import json
import re
import urllib.request
from dataclasses import dataclass

APP_VERSION = "0.1.0"
REPOSITORY = "NoteDarck/EV3-Studio"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASE_PAGE = f"https://github.com/{REPOSITORY}/releases"

@dataclass
class UpdateResult:
    ok: bool
    current: str
    latest: str = ""
    url: str = RELEASE_PAGE
    message: str = ""

def version_tuple(value):
    numbers = re.findall(r"\d+", value or "")
    return tuple(int(n) for n in numbers[:3]) or (0, 0, 0)

def check_latest(timeout=8):
    request = urllib.request.Request(RELEASES_URL, headers={"Accept": "application/vnd.github+json", "User-Agent": "EV3-Studio"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        latest = data.get("tag_name", "") or data.get("name", "")
        url = data.get("html_url", RELEASE_PAGE)
        if not latest:
            return UpdateResult(False, APP_VERSION, message="Nenhum Release publicado ainda.")
        if version_tuple(latest) > version_tuple(APP_VERSION):
            return UpdateResult(True, APP_VERSION, latest, url, "Nova versão disponível.")
        return UpdateResult(True, APP_VERSION, latest, url, "O EV3 Studio já está atualizado.")
    except Exception as exc:
        return UpdateResult(False, APP_VERSION, message=f"Não foi possível verificar agora: {exc}")
