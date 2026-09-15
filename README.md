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
- Descargar los resultados en **CSV** (todos los campos) o **PDF** (resumen para imprimir).

La búsqueda corre de forma sincrónica: se muestra una página de "Buscando..." mientras se procesa, y al terminar se muestra la tabla de resultados.

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
- `--pdf RUTA`: además del CSV, exporta un resumen en PDF a la ruta indicada

Ejemplo agregando resultados a un CSV existente y exportando también a PDF:
```bash
python main.py -s "Restaurantes turcos en Toronto Canada" -t 20 -o restaurantes.csv --append --pdf restaurantes.pdf
```

## Notas
- Por defecto el CLI abre una ventana visible del navegador (útil para depurar); usá `--headless` para ocultarla. La interfaz web usa headless por defecto.
- El CSV se guarda codificado en UTF-8 con BOM (`utf-8-sig`) para que Excel en Windows muestre bien tildes y la ñ.
- El PDF es un resumen de las columnas más relevantes (pensado para imprimir); para ver todos los campos usá el CSV.
- El DOM de Google Maps puede cambiar y romper el scraper. Si deja de funcionar, revisá los XPaths en `scraper.py`.
- Evitá correr muchas búsquedas seguidas en poco tiempo para no ser bloqueado por Google.

## Licencia
MIT
