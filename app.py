import os
import socket
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

from actualizador import buscar_nueva_version, descargar_actualizacion
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

ACTUALIZACION = {
    "disponible": False,
    "version_actual": None,
    "version_nueva": None,
    "notas": "",
    "asset_url": None,
    "asset_name": None,
    "estado_descarga": "idle",  # idle | descargando | lista | error
    "ruta_descargada": None,
    "error_descarga": None,
}


def _chequear_actualizacion_en_segundo_plano():
    ACTUALIZACION.update(buscar_nueva_version())


def _descargar_actualizacion_en_segundo_plano():
    ACTUALIZACION["estado_descarga"] = "descargando"
    ACTUALIZACION["error_descarga"] = None
    try:
        ruta = descargar_actualizacion(ACTUALIZACION["asset_url"], ACTUALIZACION["asset_name"])
        ACTUALIZACION["ruta_descargada"] = ruta
        ACTUALIZACION["estado_descarga"] = "lista"
    except Exception as e:
        ACTUALIZACION["error_descarga"] = str(e)
        ACTUALIZACION["estado_descarga"] = "error"


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
    hay_busqueda_previa = ESTADO["status"] in ("listo", "error") and bool(ESTADO["places"] or ESTADO["error"])
    return render_template("formulario.html", hay_busqueda_previa=hay_busqueda_previa)


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


@app.route("/actualizacion")
def actualizacion():
    return jsonify(ACTUALIZACION)


@app.route("/actualizacion/buscar", methods=["POST"])
def actualizacion_buscar():
    """Chequeo manual, disparado por el botón "Buscar actualización" (no hay polling
    automático: la app solo verifica al iniciar y cuando el usuario lo pide)."""
    ACTUALIZACION.update(buscar_nueva_version())
    return jsonify(ACTUALIZACION)


@app.route("/actualizacion/descargar", methods=["POST"])
def actualizacion_descargar():
    if ACTUALIZACION["disponible"] and ACTUALIZACION["estado_descarga"] in ("idle", "error"):
        threading.Thread(target=_descargar_actualizacion_en_segundo_plano, daemon=True).start()
    return jsonify(ACTUALIZACION)


PUERTO = 5000


def _puerto_realmente_libre(puerto: int, host: str = "127.0.0.1") -> bool:
    """Chequea si el puerto está libre de verdad, sin SO_REUSEADDR. En Windows, el
    servidor de desarrollo de Flask/Werkzeug activa SO_REUSEADDR, lo que permite que dos
    procesos se "bindeen" al mismo puerto sin error (a diferencia de Linux): el segundo
    proceso arranca en apariencia bien, pero nunca recibe tráfico real, porque el sistema
    operativo lo sigue enrutando a la instancia vieja. Por eso este chequeo se hace con un
    socket aparte que NO usa SO_REUSEADDR, para detectar instancias previas de verdad."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, puerto))
            return True
        except OSError:
            return False


if __name__ == "__main__":
    if FROZEN and not _puerto_realmente_libre(PUERTO):
        print(f"Ya hay otra instancia de Google Maps Scraper corriendo en el puerto {PUERTO}.")
        print("Cerrala (buscá 'gmaps-scraper' en el Administrador de tareas) antes de abrir esta versión.")
        if os.environ.get("CI") != "true":
            webbrowser.open(f"http://127.0.0.1:{PUERTO}/")
            try:
                input("Presioná Enter para cerrar esta ventana...")
            except (EOFError, KeyboardInterrupt):
                pass  # sin consola interactiva (o cerrada); no hay nada más que hacer acá
        sys.exit(0)

    threading.Thread(target=_chequear_actualizacion_en_segundo_plano, daemon=True).start()

    if FROZEN:
        # use_reloader=False es obligatorio: el reloader de Flask re-ejecuta el propio
        # proceso, y en un binario PyInstaller eso relanza el ejecutable entero de nuevo.
        # os.environ["CI"] lo fija automáticamente GitHub Actions: evita intentar abrir un
        # navegador (no hay ninguno) durante la verificación del binario en el workflow.
        if os.environ.get("CI") != "true":
            threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PUERTO}/")).start()
        app.run(host="127.0.0.1", port=PUERTO, debug=False, use_reloader=False, threaded=True)
    else:
        app.run(debug=True, threaded=True)
