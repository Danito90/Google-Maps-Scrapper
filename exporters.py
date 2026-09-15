import logging
import os
from dataclasses import asdict, fields
from typing import List

import pandas as pd
from fpdf import FPDF

from scraper import Place

COLUMN_ORDER = [f.name for f in fields(Place)]

COLUMN_LABELS_ES = {
    "name": "Nombre",
    "place_type": "Categoría",
    "address": "Dirección",
    "phone_number": "Teléfono",
    "website": "Sitio web",
    "email": "Email",
    "reviews_count": "Cantidad de reseñas",
    "reviews_average": "Calificación promedio",
    "price_range": "Rango de precios",
    "business_status": "Estado del negocio",
    "opens_at": "Horario",
    "store_shopping": "Compra en tienda",
    "in_store_pickup": "Retiro en tienda",
    "store_delivery": "Entrega a domicilio",
    "latitude": "Latitud",
    "longitude": "Longitud",
    "google_maps_url": "URL de Google Maps",
    "introduction": "Descripción",
}

# Columnas mostradas en el resumen PDF (una tabla con las 18 columnas completas sería
# ilegible incluso en A4 apaisado). El CSV siempre incluye todas las columnas.
PDF_SUMMARY_COLUMNS = [
    "name",
    "place_type",
    "address",
    "phone_number",
    "email",
    "reviews_average",
    "reviews_count",
    "business_status",
    "opens_at",
]

_PDF_REPLACEMENTS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...",
}


def _pdf_safe(texto) -> str:
    texto = "" if texto is None else str(texto)
    for original, reemplazo in _PDF_REPLACEMENTS.items():
        texto = texto.replace(original, reemplazo)
    return texto.encode("latin-1", "replace").decode("latin-1")


def _places_to_dataframe(places: List[Place]) -> pd.DataFrame:
    df = pd.DataFrame([asdict(place) for place in places])
    return df.reindex(columns=COLUMN_ORDER)


def save_places_to_csv(places: List[Place], output_path: str = "result.csv", append: bool = False):
    df = _places_to_dataframe(places)
    if df.empty:
        logging.warning("No hay datos para guardar. La tabla está vacía.")
        return
    df = df.rename(columns=COLUMN_LABELS_ES)
    file_exists = os.path.isfile(output_path)
    mode = "a" if append else "w"
    header = not (append and file_exists)
    df.to_csv(output_path, index=False, mode=mode, header=header, encoding="utf-8-sig")
    logging.info(f"Guardados {len(df)} lugares en {output_path} (agregar={append})")


def save_places_to_pdf(places: List[Place], output_path: str = "result.pdf"):
    df = _places_to_dataframe(places)
    if df.empty:
        logging.warning("No hay datos para guardar. La tabla está vacía.")
        return

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, _pdf_safe("Informe de resultados - Google Maps"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, _pdf_safe("Resumen: para ver todos los campos, use la exportación a CSV."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    columnas = [c for c in PDF_SUMMARY_COLUMNS if c in df.columns]
    ancho_pagina = pdf.w - 2 * pdf.l_margin
    ancho_columna = ancho_pagina / len(columnas)

    pdf.set_font("Helvetica", "B", 8)
    for columna in columnas:
        pdf.cell(ancho_columna, 8, _pdf_safe(COLUMN_LABELS_ES.get(columna, columna)), border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for _, row in df.iterrows():
        for columna in columnas:
            valor = row[columna]
            texto = "" if pd.isna(valor) else _pdf_safe(valor)
            if len(texto) > 40:
                texto = texto[:37] + "..."
            pdf.cell(ancho_columna, 7, texto, border=1)
        pdf.ln()

    pdf.output(output_path)
    logging.info(f"Guardados {len(df)} lugares en {output_path}")
