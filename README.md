# 📅 Calendario de Municipal (.ics)

Calendario de partidos de **Municipal** que se actualiza solo. Toma los datos de
[ESPN](https://www.espn.com.gt/futbol/equipo/calendario/_/id/7258/gua.municipal)
cada 3 horas con GitHub Actions; si un partido se reprograma, se agrega o se
cancela, el archivo `municipal.ics` se regenera y todos los calendarios
suscritos lo reciben.

## Suscribirse con un clic

- **Google Calendar:** [➕ Agregar a Google Calendar](https://calendar.google.com/calendar/render?cid=webcal%3A%2F%2Fraw.githubusercontent.com%2Fa1053%2Fmunicipal-calendar-v2%2Fmain%2Fmunicipal.ics)
- **Outlook:** [➕ Agregar a Outlook](https://outlook.live.com/calendar/0/addfromweb?url=https%3A%2F%2Fraw.githubusercontent.com%2Fa1053%2Fmunicipal-calendar-v2%2Fmain%2Fmunicipal.ics&name=Municipal)
- **iPhone / Mac:** copia `webcal://raw.githubusercontent.com/a1053/municipal-calendar-v2/main/municipal.ics`
  y pégalo en Safari; Calendario ofrecerá suscribirse.

URL directa (para cualquier otra app, como "suscribirse desde URL"):

```
https://raw.githubusercontent.com/a1053/municipal-calendar-v2/main/municipal.ics
```

El repositorio debe ser **público** para que los calendarios puedan leer la URL.

> Importa la URL como **suscripción**, no subiendo el archivo: solo así se
> actualiza. Google Calendar refresca suscripciones cada 12–24 h; Apple y
> Outlook, más seguido. Es una limitación de Google, no del repositorio.

## Cómo funciona

```
API de ESPN ──► scripts/update_calendar.py ──► data/matches.json ──► municipal.ics
         (GitHub Actions, cada 3 h)      (base de datos)       (lo que suscribes)
```

- `data/matches.json` es la base de datos: un registro por partido (ID de ESPN).
  Cada cambio de fecha/hora/rival sube el `seq` del evento, y los clientes de
  calendario saben así que deben actualizarlo.
- Los partidos ya jugados se conservan como historial; los futuros que ESPN
  deja de listar se eliminan (cancelados).
- El `.ics` solo se vuelve a escribir (y hacer commit) si algo cambió.
- Si ESPN falla o cambia su diseño y no se extrae ningún partido, el workflow
  **falla** y no toca el calendario; te llega un correo de GitHub.

## Puesta en marcha

El repositorio ya está configurado: el workflow corre solo cada 3 horas y
cuando cambias algo en `scripts/`. Para forzar una actualización: pestaña
**Actions** → *Actualizar calendario de Municipal* → **Run workflow**.
Si alguna vez falla al hacer push, revisa *Settings → Actions → General →
Workflow permissions* y activa **Read and write permissions**.

## Notas importantes

- **Local vs. visitante:** se toma el orden de ESPN (local primero). El título
  del evento es `Local vs Visitante`.
- **Fuente:** se usa la API JSON de ESPN (partidos jugados y por jugar de la
  Liga Nacional, Central American Cup y Champions Cup), que entrega fechas en
  UTC y la sede. La página HTML de ESPN queda solo como respaldo, porque ESPN
  la devuelve vacía a los servidores de GitHub.
- Si ESPN falla, el workflow termina en rojo con el motivo en *Annotations* y
  no modifica el calendario.
- **Duración:** se asignan 2 h por partido (`MATCH_DURATION`). ESPN no publica fin.
- **Inactividad:** GitHub desactiva los workflows programados tras 60 días sin
  actividad en el repo. Mientras haya partidos, el bot hace commits y se mantiene
  activo; en la pausa entre torneos, vuelve a activarlo en la pestaña Actions.
- Uso personal: respeta los términos de uso de ESPN y no aumentes la frecuencia
  más de lo necesario.

## 🌐 Sitio web (GitHub Pages)

Además del calendario, este repo publica un sitio con el marcador del próximo
partido (o el que está en vivo), partidos y resultados, la tabla de la Liga
Bantrab con Municipal resaltado, noticias y redes (X e Instagram).

```
ESPN + Google Noticias ──► scripts/build_site_data.py ──► site/ ──► GitHub Pages
          (workflow "Publicar sitio de Municipal", cada 15 min)
```

- `site/` es el sitio estático (HTML, CSS y JS, sin pasos de compilación).
  `site/config.json` guarda las cuentas de X e Instagram y los nombres de las
  competencias.
- Los datos (`data/*.json` dentro del sitio publicado) se generan en cada
  corrida y **no se guardan en el repo**, así el historial no se llena de commits.
- Si ESPN falla al leer partidos, no se publica nada y queda el sitio anterior.
  Si falla la tabla o las noticias, se reutiliza la última versión publicada.
- El calendario `.ics` también se sirve desde el sitio (`/municipal.ics`).
- **Noticias de Municipal** de muchas fuentes, sin claves: Google Noticias y
  Bing Noticias (varias búsquedas), GDELT (índice mundial de noticias), ESPN y
  los feeds RSS de medios guatemaltecos (`scripts/news_sources.py`). Cada nota
  pasa un filtro para descartar otros "Municipal" (Perú, El Salvador, Costa
  Rica, política local). Se deduplican por titular y se guardan acumuladas
  (hasta 80 notas de los últimos 150 días). El estado de cada fuente queda en
  el log del workflow y en `news.json`. Para agregar un medio, súmalo a
  `SPORTS_FEEDS` o `WP_SEARCH`.
- **Rendimiento:** porcentaje de victorias, puntos y goles por partido,
  porterías en cero, local contra visitante y los resultados de la temporada,
  con filtro por competencia, más un resumen en texto generado con esas cifras
  (la tabla y el calendario). Todo se calcula en el navegador con
  `site/stats.js`; sus pruebas están en `tests/stats.test.js` (se corren con
  `node tests/stats.test.js` y también desde `unittest`).
- **Todos los partidos** (`#/calendario`): el calendario completo agrupado por
  mes, con filtros por competencia, próximos/jugados y local/visitante.
- **Página de cada partido** (`#/partido/ID`): cronología, estadísticas y
  alineaciones; antes del partido, el rival (posición, forma, cruces previos).
- **Jugadores:** goles, asistencias, tarjetas y partidos jugados, sumados de las
  alineaciones y eventos de ESPN de los partidos publicados.
- **Vista previa al compartir:** en cada corrida se genera `og.png` y las
  metaetiquetas de `index.html` con el próximo partido o el último resultado
  (la tipografía Poppins está en `scripts/fonts`, licencia OFL).

**Activar una sola vez:** *Settings → Pages → Build and deployment → Source:
GitHub Actions*. Luego corre el workflow desde la pestaña **Actions**.
El sitio queda en `https://a1053.github.io/municipal-calendar-v2/`.

Para verlo en tu computadora: `python scripts/build_site_data.py` y
`python -m http.server -d site`.

## Desarrollo

```bash
pip install -r requirements.txt
python -m unittest discover -s tests          # pruebas
python scripts/update_calendar.py --dry-run   # ver qué extrae sin escribir
python scripts/update_calendar.py --from-file tests/fixtures/calendar.html
```
