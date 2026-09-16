import os
import sys
import threading
import webbrowser
from dataclasses import asdict
from pathlib import Path

# Debe fijarse antes de importar scraper (que importa playwright.sync_api): en el binario
# empaquetado con PyInstaller, Playwright puede resolver su cache de navegadores de forma
# menos predecible, así que se fuerza una ubicación determinística.
FROZEN = getattr(sys, "frozen", False)
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
    _base_navegadores = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "gmaps-scraper" / "ms-playwright"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_base_navegadores)

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for

from exporters import (
    COLUMN_LABELS_ES,
    COLUMN_ORDER,
    save_places_map,
    save_places_map_image,
    save_places_to_csv,
    save_places_to_excel,
)
from scraper import scrape_places


def _ruta_recurso(relativa: str) -> str:
    """Resuelve templates/static tanto en desarrollo como dentro de un binario
    PyInstaller --onefile (donde los datos empaquetados se extraen a sys._MEIPASS)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativa)


app = Flask(__name__, template_folder=_ruta_recurso("templates"), static_folder=_ruta_recurso("static"))

if FROZEN:
    # Junto al ejecutable, no en la carpeta temporal de extracción (_MEIPASS se borra al
    # cerrar la app), para que el usuario encuentre sus descargas fácilmente.
    EXPORTS_DIR = os.path.join(os.path.dirname(sys.executable), "exports")
else:
    EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
CSV_PATH = os.path.join(EXPORTS_DIR, "resultados.csv")
XLSX_PATH = os.path.join(EXPORTS_DIR, "resultados.xlsx")
MAPA_PATH = os.path.join(EXPORTS_DIR, "mapa.html")
MAPA_IMAGEN_PATH = os.path.join(EXPORTS_DIR, "mapa.png")

ESTADO = {
    "status": "vacio",
    "params": {},
    "places": [],
    "csv_path": None,
    "xlsx_path": None,
    "mapa_path": None,
    "mapa_imagen_path": None,
    "error": None,
}

PROGRESO = {"actual": 0, "total": 0}


def _ejecutar_busqueda(params):
    """Corre en un hilo de fondo para no bloquear el servidor y poder reportar progreso."""
    PROGRESO["actual"] = 0
    PROGRESO["total"] = params.get("total", 0)
    try:
        def on_progress(actual, total):
            PROGRESO["actual"] = actual
            PROGRESO["total"] = total

        places = scrape_places(**params, on_progress=on_progress)
        ESTADO["places"] = places
        ESTADO["csv_path"] = None
        ESTADO["xlsx_path"] = None
        ESTADO["mapa_path"] = None
        ESTADO["mapa_imagen_path"] = None
        if places:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            save_places_to_csv(places, CSV_PATH)
            save_places_to_excel(places, XLSX_PATH)
            ESTADO["csv_path"] = CSV_PATH
            ESTADO["xlsx_path"] = XLSX_PATH
            if save_places_map(places, MAPA_PATH):
                ESTADO["mapa_path"] = MAPA_PATH
            if save_places_map_image(places, MAPA_IMAGEN_PATH):
                ESTADO["mapa_imagen_path"] = MAPA_IMAGEN_PATH
        ESTADO["status"] = "listo"
    except Exception as e:
        ESTADO["error"] = str(e)
        ESTADO["status"] = "error"


@app.route("/")
def formulario():
    return render_template("formulario.html")


@app.route("/buscar", methods=["POST"])
def buscar():
    busqueda = (request.form.get("busqueda") or "").strip()
    try:
        total = int(request.form.get("total") or 1)
    except ValueError:
        total = 1
    total = max(1, total)

    params = {
        "search_for": busqueda,
        "total": total,
        "headless": request.form.get("headless") == "on",
        "buscar_email": request.form.get("buscar_email") == "on",
    }
    ESTADO["params"] = params
    ESTADO["status"] = "corriendo"
    ESTADO["error"] = None
    threading.Thread(target=_ejecutar_busqueda, args=(params,), daemon=True).start()
    return redirect(url_for("buscando"))


@app.route("/buscando")
def buscando():
    if ESTADO["status"] in ("listo", "error"):
        return redirect(url_for("resultados"))
    return render_template("buscando.html")


@app.route("/progreso")
def progreso():
    return jsonify(
        actual=PROGRESO["actual"],
        total=PROGRESO["total"],
        terminado=ESTADO["status"] in ("listo", "error"),
    )


@app.route("/resultados")
def resultados():
    return render_template(
        "resultados.html",
        places=[asdict(place) for place in ESTADO["places"]],
        columnas=COLUMN_ORDER,
        etiquetas=COLUMN_LABELS_ES,
        error=ESTADO["error"],
        hay_resultados=ESTADO["status"] == "listo" and bool(ESTADO["places"]),
        hay_mapa=bool(ESTADO["mapa_path"]),
    )


@app.route("/mapa")
def ver_mapa():
    if not ESTADO["mapa_path"] or not os.path.isfile(ESTADO["mapa_path"]):
        return redirect(url_for("formulario"))
    return send_file(ESTADO["mapa_path"])


@app.route("/descargar/csv")
def descargar_csv():
    if not ESTADO["csv_path"] or not os.path.isfile(ESTADO["csv_path"]):
        return redirect(url_for("formulario"))
    return send_file(ESTADO["csv_path"], as_attachment=True, download_name="resultados_google_maps.csv")


@app.route("/descargar/xlsx")
def descargar_xlsx():
    if not ESTADO["xlsx_path"] or not os.path.isfile(ESTADO["xlsx_path"]):
        return redirect(url_for("formulario"))
    return send_file(ESTADO["xlsx_path"], as_attachment=True, download_name="resultados_google_maps.xlsx")


@app.route("/descargar/mapa")
def descargar_mapa():
    if not ESTADO["mapa_imagen_path"] or not os.path.isfile(ESTADO["mapa_imagen_path"]):
        return redirect(url_for("formulario"))
    return send_file(ESTADO["mapa_imagen_path"], as_attachment=True, download_name="mapa_google_maps.png")


if __name__ == "__main__":
    if FROZEN:
        # use_reloader=False es obligatorio: el reloader de Flask re-ejecuta el propio
        # proceso, y en un binario PyInstaller eso relanza el ejecutable entero de nuevo.
        # os.environ["CI"] lo fija automáticamente GitHub Actions: evita intentar abrir un
        # navegador (no hay ninguno) durante la verificación del binario en el workflow.
        if os.environ.get("CI") != "true":
            threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
        app.run(debug=False, use_reloader=False, threaded=True)
    else:
        app.run(debug=True, threaded=True)
