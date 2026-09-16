import json
import logging
import os
import platform
import re
import sys
import urllib.request
from pathlib import Path

GITHUB_REPO = "Danito90/Google-Maps-Scrapper"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = "gmaps-scraper-actualizador"


def _version_a_tupla(version: str) -> tuple:
    version = version.lstrip("vV")
    partes = []
    for parte in version.split("."):
        numero = re.match(r"\d+", parte)
        partes.append(int(numero.group()) if numero else 0)
    return tuple(partes)


def obtener_version_actual() -> str:
    """Lee la versión desde pyproject.toml (bundleado junto al binario con --add-data,
    o presente en la raíz del repo cuando se corre desde código fuente)."""
    import tomllib

    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    ruta = os.path.join(base, "pyproject.toml")
    try:
        with open(ruta, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception as e:
        logging.warning(f"No se pudo leer la versión actual: {e}")
        return "0.0.0"


def _clave_sistema_operativo() -> str:
    sistema = platform.system()
    if sistema == "Windows":
        return "windows"
    if sistema == "Darwin":
        return "macos"
    return "linux"


def buscar_nueva_version() -> dict:
    """Consulta el último release en GitHub y compara con la versión actual.

    Devuelve un dict con disponible/version_actual/version_nueva/notas/asset_url/asset_name.
    `disponible` queda en False si no hay versión más nueva, no hay un binario para este
    sistema operativo entre los assets, o falla la consulta (sin conexión, rate limit, etc).
    """
    version_actual = obtener_version_actual()
    resultado = {
        "disponible": False,
        "version_actual": version_actual,
        "version_nueva": None,
        "notas": "",
        "asset_url": None,
        "asset_name": None,
    }
    try:
        request = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=10) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))

        version_nueva = (datos.get("tag_name") or "").lstrip("vV")
        if not version_nueva or _version_a_tupla(version_nueva) <= _version_a_tupla(version_actual):
            return resultado

        clave_sistema = _clave_sistema_operativo()
        asset_elegido = None
        for asset in datos.get("assets", []):
            if clave_sistema in asset.get("name", "").lower():
                asset_elegido = asset
                break
        if not asset_elegido:
            logging.warning(
                f"Hay una versión nueva ({version_nueva}) pero no se encontró un "
                f"binario para este sistema ({clave_sistema}) entre los assets del release."
            )
            return resultado

        resultado.update(
            {
                "disponible": True,
                "version_nueva": version_nueva,
                "notas": datos.get("body") or "",
                "asset_url": asset_elegido["browser_download_url"],
                "asset_name": asset_elegido["name"],
            }
        )
    except Exception as e:
        logging.warning(f"No se pudo verificar si hay una versión nueva: {e}")
    return resultado


def descargar_actualizacion(asset_url: str, asset_name: str) -> str:
    """Descarga el binario nuevo junto al ejecutable actual (o en la carpeta del proyecto
    si se corre desde código fuente) y devuelve la ruta local del archivo descargado."""
    if getattr(sys, "frozen", False):
        destino_dir = Path(sys.executable).resolve().parent
    else:
        destino_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    destino = destino_dir / asset_name

    request = urllib.request.Request(asset_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as respuesta, open(destino, "wb") as f:
        while True:
            bloque = respuesta.read(1024 * 256)
            if not bloque:
                break
            f.write(bloque)

    if os.name != "nt":
        os.chmod(destino, 0o755)  # el binario descargado en Linux/macOS necesita permiso de ejecución

    logging.info(f"Actualización descargada en {destino}")
    return str(destino)
