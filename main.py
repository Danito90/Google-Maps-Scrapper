import argparse

from exporters import save_places_map, save_places_map_image, save_places_to_csv, save_places_to_excel
from scraper import scrape_places


def main():
    parser = argparse.ArgumentParser(description="Scraper de Google Maps")
    parser.add_argument("-s", "--search", type=str, help="Término de búsqueda para Google Maps")
    parser.add_argument("-t", "--total", type=int, help="Cantidad total de resultados a scrapear")
    parser.add_argument("-o", "--output", type=str, default="result.csv", help="Ruta del archivo CSV de salida")
    parser.add_argument("--append", action="store_true", help="Agregar los resultados al archivo en vez de sobrescribirlo")
    parser.add_argument("--headless", action="store_true", help="Ejecutar el navegador sin ventana visible")
    parser.add_argument("--email", action="store_true", help="Buscar email en el sitio web de cada negocio (más lento)")
    parser.add_argument("--xlsx", type=str, default=None, help="Ruta opcional para exportar también a Excel (.xlsx)")
    parser.add_argument("--mapa", type=str, default=None, help="Ruta opcional para generar un mapa interactivo (.html) con los puntos scrapeados")
    parser.add_argument("--mapa-imagen", type=str, default=None, help="Ruta opcional para generar una imagen (.png) del mapa con los puntos scrapeados")
    args = parser.parse_args()

    search_for = args.search or "turkish stores in toronto Canada"
    total = args.total or 1

    places = scrape_places(search_for, total, headless=args.headless, buscar_email=args.email)
    save_places_to_csv(places, args.output, append=args.append)
    if args.xlsx:
        save_places_to_excel(places, args.xlsx)
    if args.mapa:
        save_places_map(places, args.mapa)
    if args.mapa_imagen:
        save_places_map_image(places, args.mapa_imagen)


if __name__ == "__main__":
    main()
