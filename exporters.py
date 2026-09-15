import html
import logging
import os
from dataclasses import asdict, fields
from typing import List

import folium
import pandas as pd
from staticmap import CircleMarker, StaticMap

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

# Teselas de OpenStreetMap France: son gratuitas y no piden API key (a diferencia de
# CartoDB, que ahora exige una), y no bloquean a esta app como sí hace directamente
# tile.openstreetmap.org con clientes que no cumplen su política de uso.
MAP_TILES_URL = "https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png"
MAP_ATTRIBUTION = "&copy; OpenStreetMap contributors"
MAP_TILE_HEADERS = {"User-Agent": "Google-Maps-Scrapper/1.0"}


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


def save_places_to_excel(places: List[Place], output_path: str = "result.xlsx"):
    df = _places_to_dataframe(places)
    if df.empty:
        logging.warning("No hay datos para guardar. La tabla está vacía.")
        return
    df = df.rename(columns=COLUMN_LABELS_ES)
    df.to_excel(output_path, index=False, engine="openpyxl")
    logging.info(f"Guardados {len(df)} lugares en {output_path}")


def save_places_map(places: List[Place], output_path: str = "mapa.html") -> bool:
    """Genera un mapa interactivo (Leaflet) para consultar en el navegador: zoom, clic en
    cada marcador para ver nombre/dirección/teléfono. Devuelve False si no hay coordenadas.
    """
    puntos = [p for p in places if p.latitude is not None and p.longitude is not None]
    if not puntos:
        logging.warning("No hay coordenadas disponibles para generar el mapa.")
        return False

    lat_prom = sum(p.latitude for p in puntos) / len(puntos)
    lng_prom = sum(p.longitude for p in puntos) / len(puntos)
    mapa = folium.Map(
        location=[lat_prom, lng_prom],
        zoom_start=13,
        tiles=MAP_TILES_URL,
        attr=MAP_ATTRIBUTION,
    )

    for place in puntos:
        popup_html = (
            f"<b>{html.escape(place.name)}</b><br>"
            f"{html.escape(place.address)}<br>"
            f"{html.escape(place.phone_number)}"
        )
        folium.Marker(
            [place.latitude, place.longitude],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=html.escape(place.name),
        ).add_to(mapa)

    if len(puntos) > 1:
        mapa.fit_bounds([[p.latitude, p.longitude] for p in puntos])

    mapa.save(output_path)
    logging.info(f"Guardado el mapa con {len(puntos)} puntos en {output_path}")
    return True


def save_places_map_image(places: List[Place], output_path: str = "mapa.png", width: int = 900, height: int = 650) -> bool:
    """Genera una imagen estática (foto) del mapa con los puntos, pensada para descargar.

    A diferencia de save_places_map, no es interactiva: es la versión que se ofrece en el
    botón de descarga. Devuelve False si no hay coordenadas.
    """
    puntos = [p for p in places if p.latitude is not None and p.longitude is not None]
    if not puntos:
        logging.warning("No hay coordenadas disponibles para generar la imagen del mapa.")
        return False

    mapa = StaticMap(width, height, url_template=MAP_TILES_URL, headers=MAP_TILE_HEADERS)
    for place in puntos:
        mapa.add_marker(CircleMarker((place.longitude, place.latitude), "#1a73e8", 14))
        mapa.add_marker(CircleMarker((place.longitude, place.latitude), "#ffffff", 5))

    imagen = mapa.render()
    imagen.save(output_path)
    logging.info(f"Guardada la imagen del mapa con {len(puntos)} puntos en {output_path}")
    return True
