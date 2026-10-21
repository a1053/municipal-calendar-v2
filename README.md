# 📅 Calendario de Municipal (.ics)

Calendario de partidos de **Municipal** que se actualiza solo. Toma los datos de
[ESPN](https://www.espn.com.gt/futbol/equipo/calendario/_/id/7258/gua.municipal)
cada 3 horas con GitHub Actions; si un partido se reprograma, se agrega o se
cancela, el archivo `municipal.ics` se regenera y todos los calendarios
suscritos lo reciben.

## Suscribirse (una sola vez)

Reemplaza `USUARIO` y `REPO` por los tuyos. URL del calendario:

```
https://raw.githubusercontent.com/USUARIO/REPO/main/municipal.ics
```

El repositorio debe ser **público** para que los calendarios puedan leer la URL.

| App | Cómo |
|---|---|
| **Google Calendar** | Otros calendarios → **+** → *Desde URL* → pega la URL. |
| **iPhone / Mac** | Ajustes → Calendario → Cuentas → Añadir cuenta → Otro → *Añadir calendario suscrito*. O abre `webcal://raw.githubusercontent.com/USUARIO/REPO/main/municipal.ics`. |
| **Outlook** | Agregar calendario → *Suscribirse desde la web*. |

> Importa la URL como **suscripción**, no subiendo el archivo: solo así se
> actualiza. Google Calendar refresca suscripciones cada 12–24 h; Apple y
> Outlook, más seguido. Es una limitación de Google, no del repositorio.

## Cómo funciona

```
ESPN ──► scripts/update_calendar.py ──► data/matches.json ──► municipal.ics
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

1. Crea un repositorio **público** en GitHub y sube estos archivos.
2. *Settings → Actions → General → Workflow permissions* → **Read and write permissions**.
3. Pestaña **Actions** → *Actualizar calendario de Municipal* → **Run workflow**
   para la primera corrida real y confirma que termina en verde.

## Notas importantes

- **Local vs. visitante:** se toma el orden de ESPN (local primero). El título
  del evento es `Local vs Visitante`.
- **Horas:** si ESPN entrega el JSON embebido, se usa su fecha en UTC. Si usa el
  respaldo HTML, se asume que las horas de la tabla están en hora de Guatemala
  (`SOURCE_TZ` en el script). Compara el primer partido con ESPN tras la primera
  corrida.
- **Duración:** se asignan 2 h por partido (`MATCH_DURATION`). ESPN no publica fin.
- **Inactividad:** GitHub desactiva los workflows programados tras 60 días sin
  actividad en el repo. Mientras haya partidos, el bot hace commits y se mantiene
  activo; en la pausa entre torneos, vuelve a activarlo en la pestaña Actions.
- Uso personal: respeta los términos de uso de ESPN y no aumentes la frecuencia
  más de lo necesario.

## Desarrollo

```bash
pip install -r requirements.txt
python -m unittest discover -s tests          # pruebas
python scripts/update_calendar.py --dry-run   # ver qué extrae sin escribir
python scripts/update_calendar.py --from-file tests/fixtures/calendar.html
```
