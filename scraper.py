import logging
import re
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

LAT_LNG_PATTERN = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
# El href del listado incluye la coordenada exacta del negocio como "!3d<lat>!4d<lng>",
# más precisa y confiable que el "@lat,lng" del viewport del mapa (ver extract_lat_lng).
HREF_LAT_LNG_PATTERN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


@dataclass
class Place:
    name: str = ""
    place_type: str = ""
    address: str = ""
    phone_number: str = ""
    website: str = ""
    email: str = ""
    reviews_count: Optional[int] = None
    reviews_average: Optional[float] = None
    price_range: str = ""
    business_status: str = ""
    opens_at: str = ""
    store_shopping: str = "No"
    in_store_pickup: str = "No"
    store_delivery: str = "No"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: str = ""
    introduction: str = ""


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def extract_text(page: Page, xpath: str) -> str:
    try:
        if page.locator(xpath).count() > 0:
            return page.locator(xpath).inner_text()
    except Exception as e:
        logging.warning(f"No se pudo extraer texto para el xpath {xpath}: {e}")
    return ""


def extract_lat_lng(url: str) -> Tuple[Optional[float], Optional[float]]:
    match = LAT_LNG_PATTERN.search(url)
    if not match:
        return None, None
    try:
        return float(match.group(1)), float(match.group(2))
    except ValueError:
        return None, None


def extract_lat_lng_from_href(href: str) -> Tuple[Optional[float], Optional[float]]:
    match = HREF_LAT_LNG_PATTERN.search(href)
    if not match:
        return None, None
    try:
        return float(match.group(1)), float(match.group(2))
    except ValueError:
        return None, None


def extract_email_from_website(browser: Browser, website_url: str, timeout_ms: int = 8000) -> str:
    if not website_url or not website_url.startswith("http"):
        return ""
    page = None
    try:
        page = browser.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(website_url, wait_until="domcontentloaded", timeout=timeout_ms)
        for link in page.locator('a[href^="mailto:"]').all():
            href = (link.get_attribute("href") or "").replace("mailto:", "").split("?")[0].strip()
            if href:
                return href
        match = EMAIL_PATTERN.search(page.content())
        return match.group(0) if match else ""
    except Exception as e:
        logging.warning(f"No se pudo obtener el email de {website_url}: {e}")
        return ""
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


def extract_place(page: Page, browser: Browser, buscar_email: bool = False) -> Place:
    # XPaths
    name_xpath = '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]'
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
    reviews_count_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]'
    reviews_average_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]'
    info1 = '//div[@class="LTs0Rc"][1]'
    info2 = '//div[@class="LTs0Rc"][2]'
    info3 = '//div[@class="LTs0Rc"][3]'
    opens_at_xpath = '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]'
    opens_at_xpath2 = '//div[@class="MkV9"]//span[@class="ZDu9vd"]//span[2]'
    place_type_xpath = '//div[@class="LBgpqf"]//button[@class="DkEaL "]'
    # Mismo contenedor que place_type_xpath, pero el texto completo suele venir como
    # "Categoría · $$ · Descripción corta"; de ahí se extrae el rango de precios.
    category_block_xpath = '//div[@class="LBgpqf"]'
    intro_xpath = '//div[@class="WeS02d fontBodyMedium"]//div[@class="PYvSYb "]'
    # Textos de estado del negocio: más estables entre cambios de DOM que las clases CSS.
    closed_permanently_xpath = (
        '//span[contains(text(), "Cerrado permanentemente") '
        'or contains(text(), "Permanently closed")]'
    )
    closed_temporarily_xpath = (
        '//span[contains(text(), "Cerrado temporalmente") '
        'or contains(text(), "Temporarily closed")]'
    )

    place = Place()
    place.name = extract_text(page, name_xpath)
    place.address = extract_text(page, address_xpath)
    place.website = extract_text(page, website_xpath)
    place.phone_number = extract_text(page, phone_number_xpath)
    place.place_type = extract_text(page, place_type_xpath)
    place.introduction = extract_text(page, intro_xpath) or "No encontrada"

    # URL, latitud y longitud
    place.google_maps_url = page.url
    place.latitude, place.longitude = extract_lat_lng(page.url)

    # Cantidad de reseñas
    reviews_count_raw = extract_text(page, reviews_count_xpath)
    if reviews_count_raw:
        try:
            temp = reviews_count_raw.replace("\xa0", "").replace("(", "").replace(")", "").replace(",", "")
            place.reviews_count = int(temp)
        except Exception as e:
            logging.warning(f"No se pudo interpretar la cantidad de reseñas: {e}")
    # Calificación promedio
    reviews_avg_raw = extract_text(page, reviews_average_xpath)
    if reviews_avg_raw:
        try:
            temp = reviews_avg_raw.replace(" ", "").replace(",", ".")
            place.reviews_average = float(temp)
        except Exception as e:
            logging.warning(f"No se pudo interpretar la calificación promedio: {e}")
    # Información de tienda
    for info_xpath in (info1, info2, info3):
        info_raw = extract_text(page, info_xpath)
        if info_raw:
            temp = info_raw.split("·")
            if len(temp) > 1:
                check = temp[1].replace("\n", "").lower()
                if "shop" in check or "tienda" in check:
                    place.store_shopping = "Sí"
                if "pickup" in check or "recogida" in check or "retiro" in check:
                    place.in_store_pickup = "Sí"
                if "delivery" in check or "domicilio" in check or "entrega" in check:
                    place.store_delivery = "Sí"
    # Horario de apertura
    opens_at_raw = extract_text(page, opens_at_xpath)
    if opens_at_raw:
        opens = opens_at_raw.split("⋅")
        if len(opens) > 1:
            place.opens_at = opens[1].replace(" ", "")
        else:
            place.opens_at = opens_at_raw.replace(" ", "")
    else:
        opens_at2_raw = extract_text(page, opens_at_xpath2)
        if opens_at2_raw:
            opens = opens_at2_raw.split("⋅")
            if len(opens) > 1:
                place.opens_at = opens[1].replace(" ", "")
            else:
                place.opens_at = opens_at2_raw.replace(" ", "")

    # Rango de precios (best-effort: depende de que Google incluya el símbolo "$" en el bloque de categoría)
    category_block_raw = extract_text(page, category_block_xpath)
    if category_block_raw:
        for segment in category_block_raw.split("·"):
            segment = segment.strip()
            if segment and re.fullmatch(r"[$€]+(-[$€]+)?", segment):
                place.price_range = segment
                break

    # Estado del negocio (best-effort: basado en texto, ya que las clases CSS cambian seguido)
    if extract_text(page, closed_permanently_xpath):
        place.business_status = "Cerrado permanentemente"
    elif extract_text(page, closed_temporarily_xpath):
        place.business_status = "Cerrado temporalmente"
    else:
        place.business_status = "Abierto"

    # Email (opcional, más lento: visita el sitio web externo del negocio)
    if buscar_email and place.website:
        try:
            website_url = place.website
            if not website_url.startswith("http"):
                website_url = f"https://{website_url}"
            place.email = extract_email_from_website(browser, website_url)
        except Exception as e:
            logging.warning(f"Falló la búsqueda de email para {place.name}: {e}")

    return place


PLACE_LINK_XPATH = '//a[contains(@href, "https://www.google.com/maps/place")]'
# Textos de los botones del diálogo de consentimiento de cookies que Google muestra a
# veces (varía según región/idioma); si no aparece ninguno, simplemente no hay diálogo.
_BOTONES_CONSENTIMIENTO = ["Aceptar todo", "Rechazar todo", "Accept all", "Reject all", "I agree"]
# Texto que muestra Google cuando la búsqueda no encuentra ningún resultado.
_SIN_RESULTADOS_XPATH = (
    '//*[contains(text(), "no puede encontrar") or contains(text(), "can\'t find") '
    'or contains(text(), "No se han encontrado resultados")]'
)


def _aceptar_cookies(page: Page):
    """Cierra el diálogo de consentimiento de cookies si Google lo muestra."""
    for texto in _BOTONES_CONSENTIMIENTO:
        try:
            boton = page.get_by_role("button", name=texto)
            if boton.count() > 0:
                boton.first.click(timeout=3000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _buscar_en_maps(page: Page, search_for: str, total: int) -> List[Page]:
    """Escribe la búsqueda y espera resultados. Devuelve la lista de <a> de cada listado
    (vacía si Google no encontró nada, o con un único elemento sintético si Google navegó
    directo a un solo resultado en vez de mostrar una lista).
    """
    page.locator("//form[contains(@jsaction,'searchboxFormSubmit')]//input[@name='q']").fill(search_for)
    page.keyboard.press("Enter")

    try:
        page.wait_for_selector(f"{PLACE_LINK_XPATH} | {_SIN_RESULTADOS_XPATH}", timeout=30000)
    except PlaywrightTimeoutError:
        raise RuntimeError(
            f'Google Maps no respondió para la búsqueda "{search_for}" (tardó demasiado). '
            "Probá de nuevo en unos segundos o con otro término de búsqueda."
        )

    if page.locator(PLACE_LINK_XPATH).count() > 0:
        try:
            # Solo para posicionar el mouse sobre la lista y que el scroll siguiente
            # afecte al panel de resultados (y no al mapa). force=True evita que una
            # miniatura superpuesta bloquee la acción con un timeout innecesario.
            page.hover(PLACE_LINK_XPATH, timeout=5000, force=True)
        except PlaywrightTimeoutError:
            pass
        previously_counted = 0
        while True:
            page.mouse.wheel(0, 10000)
            page.wait_for_selector(PLACE_LINK_XPATH)
            found = page.locator(PLACE_LINK_XPATH).count()
            logging.info(f"Encontrados hasta ahora: {found}")
            if found >= total:
                break
            if found == previously_counted:
                logging.info("Se llegó a todos los resultados disponibles")
                break
            previously_counted = found
        return page.locator(PLACE_LINK_XPATH).all()[:total]

    if "/maps/place/" in page.url:
        # Google encontró una coincidencia tan fuerte que navegó directo a la ficha del
        # negocio, sin mostrar una lista de resultados con links.
        logging.info("Google navegó directo a un único resultado.")
        return []

    logging.warning(f'Google Maps no encontró resultados para "{search_for}".')
    return []


def _asegurar_chromium_instalado() -> None:
    """Instala Chromium de Playwright si falta. Se invoca en el mismo proceso (no vía
    subprocess+sys.executable, que no funciona dentro de un binario PyInstaller, ya que
    ahí sys.executable apunta al propio binario y no a un intérprete de Python real)."""
    import sys as _sys

    from playwright.__main__ import main as playwright_main

    logging.info("Chromium no está instalado. Instalando automáticamente (puede tardar unos minutos)...")
    argv_original = _sys.argv
    try:
        _sys.argv = ["playwright", "install", "chromium"]
        playwright_main()
    except SystemExit:
        pass  # playwright.__main__ termina con sys.exit(0) al finalizar OK
    finally:
        _sys.argv = argv_original


def scrape_places(
    search_for: str,
    total: int,
    headless: bool = False,
    buscar_email: bool = False,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> List[Place]:
    setup_logging()
    places: List[Place] = []
    if on_progress:
        on_progress(0, total)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=headless)
        except Exception as e:
            if "Executable doesn't exist" not in str(e):
                raise
            _asegurar_chromium_instalado()
            browser = p.chromium.launch(headless=headless)  # un solo reintento, sin loop
        page = browser.new_page()
        try:
            page.goto("https://www.google.com/maps/@32.9817464,70.1930781,3.67z?", timeout=60000)
            page.wait_for_timeout(1000)
            _aceptar_cookies(page)

            listing_links = _buscar_en_maps(page, search_for, total)

            if not listing_links and "/maps/place/" in page.url:
                # Resultado único: la propia página actual ya es la ficha del negocio.
                place = extract_place(page, browser, buscar_email=buscar_email)
                place.google_maps_url = page.url
                if place.name:
                    places.append(place)
                    if on_progress:
                        on_progress(len(places), total)
                return places

            # El href original trae la coordenada exacta del negocio (!3d..!4d..); se guarda
            # antes de resolver el contenedor padre, que es lo que se termina clickeando.
            hrefs = [link.get_attribute("href") or "" for link in listing_links]
            listings = [link.locator("xpath=..") for link in listing_links]
            logging.info(f"Total encontrado: {len(listings)}")
            for idx, listing in enumerate(listings):
                try:
                    listing.click()
                    page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]', timeout=10000)
                    time.sleep(1.5)  # Da tiempo a que carguen los detalles
                    place = extract_place(page, browser, buscar_email=buscar_email)
                    href = hrefs[idx]
                    if href:
                        place.google_maps_url = href
                        lat, lng = extract_lat_lng_from_href(href)
                        if lat is not None:
                            place.latitude, place.longitude = lat, lng
                    if place.name:
                        places.append(place)
                    else:
                        logging.warning(f"No se encontró nombre para el listado {idx + 1}, se omite.")
                except Exception as e:
                    logging.warning(f"Falló la extracción del listado {idx + 1}: {e}")
                finally:
                    if on_progress:
                        on_progress(len(places), total)
        finally:
            browser.close()
    return places
