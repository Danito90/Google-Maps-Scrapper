# Google-Maps-Scrapper

Este proyecto usa Playwright para hacer web scraping de Google Maps y extraer información de negocios: nombre, dirección, teléfono, sitio web, email, coordenadas, reseñas y más. Incluye una interfaz web (Flask) para lanzar búsquedas desde el navegador, además de la línea de comandos original.

<br>
Para un proyecto de web scraping a medida me pueden encontrar en Upwork o LinkedIn<br><br>

<a href="https://www.upwork.com/freelancers/~01dbb4d47d167c2d43" target="_blank">
<img src=https://img.shields.io/badge/Upwork-6FDA44?&style=for-the-badge&logo=medium&logoColor=white alt=medium style="margin-bottom: 5px;" />
</a>

<a href="https://www.linkedin.com/in/zohaibbashir" target="_blank">
<img src="https://img.shields.io/badge/LinkedIn-0077B5?&style=for-the-badge&logo=linkedin&logoColor=white" alt="linkedin" style="margin-bottom: 5px;" />
</a>


## Índice
- [Requisitos previos](#requisitos-previos)
- [Campos extraídos](#campos-extraídos)
- [Instalación](#instalación)
- [Interfaz web](#interfaz-web)
- [Línea de comandos (CLI)](#línea-de-comandos-cli)
- [Notas](#notas)
- [Generar un release (binarios)](#generar-un-release-binarios)
- [Licencia](#licencia)

## Requisitos previos
- Python 3.9 o superior.
- No se necesita tener Google Chrome instalado: Playwright usa su propio Chromium (ver instalación).

## Campos extraídos
Por cada negocio se intenta obtener:

| Campo | Descripción |
|---|---|
| Nombre | Nombre del negocio |
| Categoría | Tipo de negocio (ej. "Panadería") |
| Dirección | Dirección completa |
| Teléfono | Número de teléfono |
| Sitio web | URL del sitio web, si figura en la ficha |
| Email | Opcional: se obtiene visitando el sitio web del negocio (ver más abajo) |
| Cantidad de reseñas / Calificación promedio | Reputación en Google |
| Rango de precios | Cuando Google lo muestra (ej. "$$") |
| Estado del negocio | Abierto / Cerrado temporalmente / Cerrado permanentemente |
| Horario | Horario de apertura |
| Compra en tienda / Retiro en tienda / Entrega a domicilio | Servicios detectados |
| Latitud / Longitud | Coordenadas exactas del negocio |
| URL de Google Maps | Enlace directo a la ficha del negocio |
| Descripción | Introducción/descripción del negocio, si existe |

**Nota sobre el email**: Google Maps no expone el email directamente. Cuando se activa la opción "Buscar email en sitio web", el scraper visita el sitio del negocio y busca un enlace `mailto:` o un email en el texto de la página. Es más lento y no siempre encuentra resultados; por eso está desactivado por defecto.

## Instalación

1. Cloná este repositorio:
   ```bash
   git clone https://github.com/zohaibbashir/Google-Maps-Scrapper.git
   cd Google-Maps-Scrapper
   ```
2. Instalá las dependencias de Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Instalá el navegador Chromium que usa Playwright (una sola vez):
   ```bash
   playwright install chromium
   ```

## Interfaz web

Para usar la interfaz gráfica en el navegador:

```bash
python app.py
```

Y abrí [http://127.0.0.1:5000](http://127.0.0.1:5000) en el navegador. Desde ahí podés:
- Ingresar el término de búsqueda y la cantidad de resultados.
- Activar/desactivar la búsqueda de email en el sitio web de cada negocio.
- Elegir modo invisible (headless) o ver el navegador mientras scrapea.
- Ver un **mapa interactivo** con un marcador por negocio (clic para ver nombre/dirección/teléfono).
- Descargar los resultados en **CSV** o **Excel (.xlsx)** (todos los campos), y el mapa como **imagen (.png)**.

La búsqueda corre de forma sincrónica: se muestra una página de "Buscando..." mientras se procesa, y al terminar se muestra el mapa y la tabla de resultados.

## Línea de comandos (CLI)

También se puede usar desde la terminal:

```bash
python main.py -s "Restaurantes turcos en Toronto Canada" -t 20
```

- `-s` / `--search`: término de búsqueda (default: "turkish stores in toronto Canada")
- `-t` / `--total`: cantidad de resultados a scrapear (default: 1)
- `-o` / `--output`: ruta del CSV de salida (default: `result.csv`)
- `--append`: agrega los resultados al archivo existente en vez de sobrescribirlo
- `--headless`: corre el navegador sin ventana visible
- `--email`: busca el email en el sitio web de cada negocio (más lento)
- `--xlsx RUTA`: además del CSV, exporta también a Excel (.xlsx) en la ruta indicada
- `--mapa RUTA.html`: genera un mapa interactivo (Leaflet) con los puntos scrapeados
- `--mapa-imagen RUTA.png`: genera una imagen (foto) del mapa con los puntos scrapeados

Ejemplo agregando resultados a un CSV existente y generando también Excel y una imagen del mapa:
```bash
python main.py -s "Restaurantes turcos en Toronto Canada" -t 20 -o restaurantes.csv --append --xlsx restaurantes.xlsx --mapa-imagen restaurantes_mapa.png
```

## Notas
- Por defecto el CLI abre una ventana visible del navegador (útil para depurar); usá `--headless` para ocultarla. La interfaz web usa headless por defecto.
- El CSV se guarda codificado en UTF-8 con BOM (`utf-8-sig`) para que Excel en Windows muestre bien tildes y la ñ.
- El mapa usa teselas de OpenStreetMap France (`tile.openstreetmap.fr`), gratuitas y sin API key, en vez de `tile.openstreetmap.org` directamente (que bloquea a apps que no cumplen con su política de uso) o CartoDB (que ahora exige API key).
- El DOM de Google Maps puede cambiar y romper el scraper. Si deja de funcionar, revisá los XPaths en `scraper.py`.
- Evitá correr muchas búsquedas seguidas en poco tiempo para no ser bloqueado por Google.

## Generar un release (binarios)

El workflow `.github/workflows/release.yml` compila `app.py` (la interfaz web) como un binario standalone para Linux, Windows y macOS (Apple Silicon), y publica un GitHub Release con los tres adjuntos. Al abrir el binario se levanta el servidor y se abre solo el navegador en `http://127.0.0.1:5000` — queda corriendo (con una consola visible) hasta que se cierra la ventana. Chromium no viene empaquetado (pesaría cientos de MB): se instala solo la primera vez que se hace una búsqueda.

Para publicar una nueva versión, alcanza con:
1. Actualizar `version` en `pyproject.toml` (ej. `"1.1.0"`).
2. Hacer push a `main`.

El workflow se dispara solo al detectar el cambio en `pyproject.toml` (también se puede ejecutar manualmente desde **Actions** → **Release** → **Run workflow**). Antes de compilar, chequea si el tag `v<version>` ya existe: si es así, no hace nada (evita releases duplicados si `pyproject.toml` cambia por otro motivo sin tocar la versión). Si la versión es nueva, compila, verifica y publica el Release con el tag `v<version>` y los binarios `gmaps-scraper-linux-x64`, `gmaps-scraper-windows-x64.exe` y `gmaps-scraper-macos-arm64`.

Para probar el build localmente antes de correr el workflow:
```bash
pip install -r requirements.txt pyinstaller
pyinstaller app.py --name gmaps-scraper --onefile --collect-all playwright --collect-data folium \
  --add-data "templates:templates" --add-data "static:static"   # en Windows usar ; en vez de :
./dist/gmaps-scraper
```

## Licencia
MIT
