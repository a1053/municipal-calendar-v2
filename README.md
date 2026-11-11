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
Bantrab con Municipal resaltado, noticias y redes (Instagram).

```
ESPN + Google Noticias ──► scripts/build_site_data.py ──► site/ ──► GitHub Pages
          (workflow "Publicar sitio de Municipal", cada 15 min)
```

- `site/` es el sitio estático (HTML, CSS y JS, sin pasos de compilación).
  `site/config.json` guarda la cuenta de Instagram y los nombres de las
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

## Liguilla "si terminara hoy"

La sección **Liguilla** arma la llave del Apertura con la tabla actual: 1.º y 2.º pasan directo a semifinales, 3.º vs 6.º y 4.º vs 5.º juegan ronda previa, y el 1.º enfrenta al peor ubicado de los ganadores. El mejor ubicado cierra siempre la vuelta en casa. Se puede tocar un equipo para avanzarlo en la llave. La fase regular termina cuando todos juegan 22 partidos (`liguilla` en `site/config.json`). La lógica está en `site/liguilla.js` con pruebas en `tests/liguilla.test.js`. Supuestos: series a ida y vuelta y orden de la tabla tal como lo entrega ESPN.

### Probabilidades de clasificar

`scripts/odds.py` simula miles de veces lo que falta de la fase regular y cuenta cuántas veces cada equipo termina entre los 6 primeros (y entre los 2 primeros). Cada equipo pesa según sus goles a favor y en contra (mezclados con el promedio de la liga mientras haya pocos partidos), con ventaja de local y goles Poisson. Los partidos que faltan salen del calendario de la liga en ESPN; los que no tienen fecha, como los aplazados, se reparten al azar entre los equipos a los que les falten. El desempate supuesto es diferencia de goles y luego goles a favor. Resultado en `data/odds.json`; pruebas en `tests/test_odds.py`. Es una estimación: no considera lesiones, refuerzos ni suspensiones.

## Pronóstico del partido

`site/forecast.js` calcula, para el próximo partido de liga, el porcentaje de victoria, empate y derrota y los marcadores más probables. Usa el mismo modelo que las probabilidades de la liguilla (goles a favor y en contra, ventaja de local, Poisson). Aparece en Partidos y en la página de cada partido que aún no empieza. Pruebas: `tests/forecast.test.js`.

## Instalar como app

El sitio se puede instalar en el celular ("Agregar a pantalla de inicio" o "Instalar app"). Incluye `manifest.webmanifest`, íconos en `site/icons/` (se regeneran con `python scripts/make_icons.py`) y `site/sw.js`, que pide todo primero a internet y, si no hay conexión, muestra lo último que se vio. El ícono es una "M", no el escudo del club.

## Datos en vivo desde el navegador

GitHub retrasa las corridas programadas (a veces horas), así que `site/live.js` pone la tabla y los marcadores al día directamente con ESPN cada vez que se abre o refresca la página (cada 3 minutos, o 45 segundos con partido en vivo). Si ESPN no responde o cambia su formato, el sitio muestra los datos de la última corrida. Las probabilidades de la liguilla se siguen calculando en cada corrida del sitio y la página indica cuándo. Pruebas: `tests/live.test.js`.

## Carrera a la liguilla

En cada corrida el sitio guarda una foto de Municipal (posición, puntos, partidos jugados y probabilidades de clasificar y de pasar directo) en `data/history.json`. Para que la historia sobreviva entre publicaciones, el flujo descarga el `history.json` ya publicado antes de construir. La gráfica de la sección Liguilla dibuja esa historia; arranca vacía y se llena con el tiempo. Si la posición, los puntos y los partidos no cambian, se reemplaza la última foto en vez de acumular una por corrida (máximo 800). Pruebas en `tests/test_odds.py`.

## Dónde verlo y calendario de los rivales

Si ESPN publica el canal o la plataforma de un partido (campo `broadcasts` en `matches.json`), se muestra "Dónde verlo" en el marcador y en la página del partido; si no lo trae, no se muestra nada. En Liguilla, el desplegable "Calendario que les falta" lista los partidos con fecha de los equipos de arriba y una dificultad (promedio de puntos por partido de los rivales que les faltan, en tercios: difícil, medio y fácil). Solo usa partidos del calendario de la liga, nunca los repartidos al azar; si el calendario no está disponible, el desplegable no aparece.

## Historial contra el rival

En la página del próximo partido, "El rival" muestra el historial entre ambos si ESPN lo trae (`headToHeadGames` en el resumen del partido): balance de victorias, empates y derrotas y los últimos cinco partidos. Si ESPN no lo da, no aparece. Incluye un enlace a la página de Municipal en FotMob; el sitio no lee ni copia datos de FotMob.

## Noticias por tema, rachas, WhatsApp y alineación en cancha

- **Noticias por tema** (`site/topics.js`): filtros Fichajes, Lesiones, Técnico y directiva y Selección, por palabras clave en el título y el resumen. Solo aparecen los temas que tienen noticias.
- **Rachas y récords** (`records` en `site/stats.js`): mayor victoria, peor derrota, partido con más goles y rachas, dentro de Rendimiento.
- **Compartir por WhatsApp** (`site/share.js`): botones en la página del partido, la tabla y la liguilla; abren WhatsApp con un texto ya armado (enlace `wa.me`, sin servidores).
- **Alineación en cancha** (`site/pitch.js`): dibuja a los titulares según la formación y el lugar que da ESPN (`formationPlace`); si faltan datos, queda la lista. Pruebas en `tests/*.test.js`.

## Minuto a minuto (complemento)

Si ESPN trae el minuto a minuto (`commentary`), la página del partido lo muestra en un desplegable "Minuto a minuto", debajo de la cronología. Es un complemento: no cambia ni quita nada de la cronología, las estadísticas ni las alineaciones que ya vienen de ESPN. Si ESPN no lo trae, no aparece.

## Eventos y alineaciones de OneFootball (complemento)

ESPN no publica todos los eventos ni las alineaciones de la Liga Nacional. Cuando faltan, el sitio los
completa con los datos públicos de OneFootball (`scripts/onefootball.py`):

- **Cronología:** si ESPN no trae eventos, se muestran los de OneFootball con su crédito. Si ESPN trae menos
  eventos, se deja lo de ESPN tal cual y se agrega "Todos los eventos" plegado.
- **Alineaciones:** si ESPN no las tiene, se muestran los 11 titulares de OneFootball (sin formación en la cancha).
- Nunca se cambia lo que ya trae ESPN. Si OneFootball falla o cambia su formato, el sitio sigue igual.
- Pocos pedidos: 3 páginas del equipo por corrida, más los partidos que aún no tenemos. Los partidos terminados
  se guardan en `data/onefootball.json` y no se vuelven a pedir.
- Se empareja con el partido de ESPN por hora (±6 h) y nombres de equipos.
- Cada bloque lleva el enlace "Datos de OneFootball".

También se corrigió que el "Minuto a minuto" de ESPN se leía pero no se guardaba en el JSON de cada partido.

## Diseño (portada, liguilla y partidos)

- Portada tipo tablero de estadio: foco de luz, rayas de camiseta, escudos grandes, marcador LED y racha de los últimos 5 partidos.
- Liguilla: posición, puntos, probabilidades (anillos), y partidos que faltan en grande; el texto queda en "Ver el detalle en palabras".
- Partidos: tarjetas con franja de color por resultado (verde ganó, gris empató, rojo perdió, ámbar en vivo).
- Solo cambia el aspecto: los datos y las funciones son los mismos.

## Jugadores por competencia

La tabla de Jugadores muestra por defecto el total de todas las competencias ("Todas"). Si hay partidos de más de una
competencia, aparece un selector para ver solo la Liga Bantrab o cada copa. `players.json` guarda el total y el
desglose por competencia (`comps`), y los dos siempre suman lo mismo.

### Jugadores con OneFootball

Para los partidos donde ESPN no trae alineación ni eventos (casi toda la Liga Bantrab), las estadísticas de Jugadores
usan los datos de OneFootball: titulares, goles, tarjetas y quién entró de cambio. Los jugadores se emparejan con los de
ESPN por nombre (sin acentos, con nombres más largos o con errores de tipeo) para no duplicarlos. Si ESPN sí trae datos
del partido, no se suma OneFootball, para no contar dos veces. OneFootball no trae asistencias ni suplentes que no entraron.

## Navegación en el celular

En pantallas angostas (hasta 720 px) el menú de arriba se oculta y aparece una barra fija abajo con Inicio, Partidos,
Tabla, Liguilla y "Más" (Jugadores, Noticias, Rendimiento, Redes y Calendario completo). La pestaña activa cambia sola
según la sección que se está viendo. En computadora se mantiene el menú de arriba.

## Imagen para compartir

El botón "Compartir imagen" de cada partido genera en el navegador una tarjeta vertical (1080x1920) con escudos,
marcador y goleadores, o con fecha y hora si el partido no se ha jugado. Se comparte como archivo si el teléfono lo
permite; si no, se descarga. Si un escudo no carga, se dibujan las iniciales. Código: `site/sharecard.js`.

## Plantel con fichas de jugador

En Jugadores hay dos vistas: **Plantel** (pestañas por posición (Porteros, Defensas, Medios, Delanteros) con una fila por jugador: número o foto, edad, país, lesión si ESPN la
reporta y PJ/goles/asistencias) y **Estadísticas** (la tabla). El selector de competencia también filtra las fichas.
El plantel sale del roster de ESPN (`scripts/roster.py`, publicado como `data/roster.json`); si ESPN falla se conserva el
último publicado (`stale`). Las estadísticas se cruzan con las de `players.json` por nombre.

## Previa del partido ("Cómo llegan")

En la página de un partido por jugar, arriba aparece la comparación de los dos equipos (`site/previa.js`): posición, puntos,
puntos y goles por partido, diferencia de goles, últimos 5 partidos, goleadores de Municipal y el pronóstico. Solo usa datos
que ya tiene el sitio. El que va mejor en cada dato se marca con una raya roja (con los valores redondeados que se ven, un
empate no marca a nadie). En partidos que no son de liga solo aparecen lo que haya (forma y goleadores).

## Dibujo táctico con formación estimada

Cuando la alineación de Municipal no trae formación (OneFootball), la página cruza los 11 titulares con las posiciones
del plantel de ESPN y cuenta defensas, medios y delanteros para dibujar la cancha (por ejemplo 4-4-2). Se marca como
"estimada". Si un titular no se encuentra en el plantel, no se dibuja nada en vez de inventar. Código: `site/formation.js`.

## Alineaciones cargadas a mano

`data/lineups.json` permite escribir a mano la alineación de un partido cuando ninguna fuente automática trae la
formación (por ejemplo, copiada de Transfermarkt). Cada entrada lleva `date` (día en Guatemala), `rival`, `formation`,
los 11 `starters` en orden (portero, luego cada fila de izquierda a derecha, de la defensa al ataque) y el `bench`.
Las `marks` (`yellow`, `red`, `goal`, `out`, `in`, `captain`) aparecen en la cancha y en el banquillo. Solo se usa para mostrar;
no entra en las estadísticas de jugadores. Ya incluye el Municipal 3-1 Comunicaciones de la jornada 17.

Para los demás partidos, las marcas (goles, tarjetas amarillas y rojas, entró y salió) se calculan solas con los eventos
del partido y se dibujan en la cancha y en las listas (`withMarks` en `site/formation.js`).

Una entrada de `data/lineups.json` también puede traer la alineación del rival con las claves `rival_formation`,
`rival_coach`, `rival_starters` y `rival_bench` (mismo formato). Ya incluye Xelajú 1-0 Municipal, jornada 16.

Las entradas de `data/lineups.json` también pueden traer `events` (cronología con `min`, `side` "me" o "rival", `kind`
goal, yellow, red o sub, `player`, `player_out`, `assist` y `text`). Si existen, mandan sobre la cronología de ESPN y
OneFootball y muestran asistencias. Ya incluye Municipal 1-1 Guastatoya, jornada 15.

ESPN y OneFootball son la fuente oficial de los eventos: la cronología y las marcas de la cancha (goles, tarjetas,
entró, salió) salen de la lista que traiga más eventos (empate: ESPN). De lo cargado a mano se toman la formación, las
posiciones, el banquillo, el entrenador, el capitán, las asistencias y los motivos de las tarjetas. Si ninguna fuente
tiene eventos de un partido, se usa lo escrito a mano.

Los nombres de los titulares (y del banquillo, cuando ESPN lo trae) se toman de la alineación oficial de ESPN u
OneFootball, reconociendo al jugador por el nombre (la camiseta solo desempata, porque los números de las fuentes no siempre coinciden). En `data/lineups.json` se escribe el apellido y el lugar en la cancha; el
nombre escrito a mano solo se usa si la fuente oficial no tiene a ese jugador. De las capturas se necesita
principalmente la formación, las posiciones y los suplentes.
