import os
from dataclasses import asdict

from flask import Flask, redirect, render_template, request, send_file, url_for

from exporters import COLUMN_LABELS_ES, COLUMN_ORDER, save_places_to_csv, save_places_to_pdf
from scraper import scrape_places

app = Flask(__name__)

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
CSV_PATH = os.path.join(EXPORTS_DIR, "resultados.csv")
PDF_PATH = os.path.join(EXPORTS_DIR, "resultados.pdf")

ESTADO = {
    "status": "vacio",
    "params": {},
    "places": [],
    "csv_path": None,
    "pdf_path": None,
    "error": None,
}


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

    ESTADO["params"] = {
        "search_for": busqueda,
        "total": total,
        "headless": request.form.get("headless") == "on",
        "buscar_email": request.form.get("buscar_email") == "on",
    }
    ESTADO["status"] = "pendiente"
    ESTADO["error"] = None
    return redirect(url_for("buscando"))


@app.route("/buscando")
def buscando():
    if ESTADO["status"] == "listo":
        return redirect(url_for("resultados"))
    return render_template("buscando.html")


@app.route("/ejecutar")
def ejecutar():
    if ESTADO["status"] != "pendiente":
        return redirect(url_for("formulario"))
    try:
        places = scrape_places(**ESTADO["params"])
        ESTADO["places"] = places
        ESTADO["csv_path"] = None
        ESTADO["pdf_path"] = None
        if places:
            os.makedirs(EXPORTS_DIR, exist_ok=True)
            save_places_to_csv(places, CSV_PATH)
            save_places_to_pdf(places, PDF_PATH)
            ESTADO["csv_path"] = CSV_PATH
            ESTADO["pdf_path"] = PDF_PATH
        ESTADO["status"] = "listo"
    except Exception as e:
        ESTADO["error"] = str(e)
        ESTADO["status"] = "error"
    return redirect(url_for("resultados"))


@app.route("/resultados")
def resultados():
    return render_template(
        "resultados.html",
        places=[asdict(place) for place in ESTADO["places"]],
        columnas=COLUMN_ORDER,
        etiquetas=COLUMN_LABELS_ES,
        error=ESTADO["error"],
        hay_resultados=ESTADO["status"] == "listo" and bool(ESTADO["places"]),
    )


@app.route("/descargar/csv")
def descargar_csv():
    if not ESTADO["csv_path"] or not os.path.isfile(ESTADO["csv_path"]):
        return redirect(url_for("formulario"))
    return send_file(ESTADO["csv_path"], as_attachment=True, download_name="resultados_google_maps.csv")


@app.route("/descargar/pdf")
def descargar_pdf():
    if not ESTADO["pdf_path"] or not os.path.isfile(ESTADO["pdf_path"]):
        return redirect(url_for("formulario"))
    return send_file(ESTADO["pdf_path"], as_attachment=True, download_name="resultados_google_maps.pdf")


if __name__ == "__main__":
    app.run(debug=True)
