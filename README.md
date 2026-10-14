# ⚽ Matchday para Apple Calendar

Una sola suscripción ICS en `https://davidsandovalar.github.io/matchday-calendar/matchday.ics`. Se publica al actualizar `main` y aproximadamente cada seis horas. Apple recoge los cambios según su intervalo de actualización; no hace falta volver a suscribirse.

## Calendario

Conserva Premier League y los equipos anteriores. Añade Inter Miami, Selección Colombia masculina, eliminatorias masculinas UEFA y CONMEBOL, Mundial masculino, Copa América masculina, Eurocopa masculina, Libertadores y Sudamericana.

`sources.json` contiene enlaces ICS públicos de Fixtur.es, verificados descargando y analizando su contenido. Las eliminatorias del proveedor incluyen todas las confederaciones: se filtran mediante listas explícitas de selecciones UEFA y CONMEBOL.

El feed `river-plate.ics` mezcla los clubes argentino y uruguayo. Se conservan únicamente los enfrentamientos contra clubes identificados en el calendario de la liga argentina. Los encuentros internacionales de River entran además por las fuentes completas de Libertadores/Sudamericana. Este filtro conservador puede omitir amistosos o partidos de copa contra clubes que no figuran en esa referencia; evita atribuir partidos uruguayos al club argentino.

La Eurocopa disponible del proveedor corresponde a **2024**, sin encuentros dentro de la ventana actual. No es una fuente verificada de Euro 2028: cuando el proveedor publique esa edición habrá que actualizar su URL. Copa América y Mundial también dependen de la cobertura de las ediciones publicadas por el proveedor; un feed ICS válido no garantiza nuevos partidos todavía no anunciados.

## Agrupación

Después de deduplicar, **4 o más partidos de la misma competición con exactamente la misma hora de inicio** se muestran como `⚽ Champions League ×8`, por ejemplo. Las notas contienen todos los enfrentamientos; el evento acaba al terminar el último. Entre 1 y 3 permanecen individuales. Diferentes horas o competiciones se mantienen separadas, incluso si sus partidos se solapan.

La competición se identifica por su fuente, no por `[CL]`, que el proveedor usa tanto para Champions como para Libertadores. Los encuentros procedentes únicamente de un feed de equipo y sin competición verificada permanecen individuales. Los identificadores de los grupos no dependen del número de encuentros, permitiendo actualizar su contenido.

## Validación y publicación

```sh
pip install -r requirements.txt
python -m unittest -v
python main.py
```

El generador escribe `public/matchday.ics`, `public/status.json` y una página con el enlace de suscripción. El estado muestra partidos únicos, eventos visibles, grupos y duplicados eliminados. GitHub Actions ejecuta las pruebas antes de generar y publicar en Pages. La configuración de Pages debe usar GitHub Actions.

Si alguna fuente falla, no se publica un calendario incompleto y se conserva la versión anterior. La deduplicación compara equipos normalizados y horarios con tolerancia de 30 minutos. Puede requerir alias adicionales cuando el proveedor cambie nombres. Solo se incluyen partidos desde 30 días atrás hasta 550 días adelante.

## Nombre del torneo en cada partido

Los eventos individuales muestran `⚽ Sarmiento - River Plate · Liga Argentina` o `⚽ Atlético Mineiro - Torque · Sudamericana`. Los grupos mantienen su título. Las fuentes de `competition_references` sirven únicamente para identificar encuentros ya seguidos, sin añadir todos los partidos de esas ligas o copas. Se cruzan equipos y horario (hasta 30 minutos); no se deduce la competición por el país del club. Si la fuente no permite identificarla o hay resultados contradictorios, se conserva el título original y se indica en las notas que el torneo no está confirmado. Los identificadores individuales no cambian al añadir la etiqueta.

Se excluyen marcadores de fase y partidos sin dos equipos identificados (por ejemplo, `... - ...` o `TBD - River Plate`) antes de deduplicar y agrupar. Cuando la fuente publique los nombres reales, el partido entrará automáticamente.

Los nombres visibles se acortan con las tablas `TEAM_DISPLAY_NAMES` y `COMPETITION_DISPLAY_NAMES` de `main.py`: Champions, FPC, Inter Miami, New York City, LASK, Barcelona, Atlanta United, Strasbourg y PSG. También se aplican en las notas de los grupos. Estas equivalencias solo afectan la presentación; los nombres originales, la deduplicación y los identificadores se conservan.
