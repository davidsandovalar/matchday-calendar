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

Las siglas inglesas de `PREMIER_DISPLAY_NAMES` (ARS, AVL, BOU, BRE, BRI, CHE, CRY, EVE, FUL, LIV, MCI, MUN, NEW, NFO, TOT, COV, HUL, LEE, IPS y SUN) se usan **solo en Premier League**, que se muestra como Premier. En otros torneos se mantienen los nombres ingleses originales. Los demás alias solicitados (Milan, Boca, Talleres, Atlético, Union Berlin, Dortmund, Bayern, Leipzig, Genoa, Roma, Lazio, Sevilla, Belgrano, River, Millos y Slavia sin SK) se aplican en cualquier competición. Las notas de los grupos respetan la misma regla.

Las descargas GET reintentan hasta tres veces los cortes de conexión y las respuestas temporales 429/500/502/503/504, con espera progresiva. Un fallo persistente sigue bloqueando la publicación para conservar el calendario completo anterior; los errores permanentes como 404 no se reintentan.

Alias adicionales: Lazio sin SS, Mineiro, Sassuolo sin U.S., Friburgo sin SC, Lyon y Racing. Manchester United se muestra como Man. Ud fuera de Premier (en Premier sigue MUN); Bournemouth pierde AFC en torneos europeos (en Premier sigue BOU); Deportivo pierde RC solo en LaLiga; Frankfurt pierde Eintracht en Bundesliga y torneos europeos; Betis pierde Real en LaLiga y torneos europeos.

## Selecciones seguidas

Se añaden los partidos de 40 selecciones masculinas absolutas: Turquía, Bélgica, Inglaterra, Croacia, República Checa, España, Italia, Francia, Suiza, Eslovenia, Escocia, Serbia, Alemania, Países Bajos, Grecia, Marruecos, Argentina, Uruguay, Colombia, Chile, Ecuador, Perú, Bolivia, México, Estados Unidos, Canadá, Japón, Brasil, Hungría, Noruega, Gales, Suecia, Bosnia y Herzegovina, Polonia, Austria, República de Irlanda, Irlanda del Norte, Ucrania, Portugal y Dinamarca. Los calendarios individuales incluyen sus competiciones y amistosos publicados; Nations League se usa como referencia para identificar el torneo, sin añadir todos sus encuentros. Marruecos se obtiene filtrando sus partidos en amistosos, eliminatorias y Copa de África, ya que el proveedor no ofrece una página individual válida. Los torneos completos previamente seguidos se conservan. Todos los partidos se deduplican y se agrupan con la misma regla de simultaneidad.

## Códigos de selecciones

Las selecciones se muestran con sus códigos FIFA de tres letras (NED, FRA, GER, SUI, MAR, etc.), en títulos individuales y en notas de grupos, incluidos sus rivales. La tabla y sus fuentes quedan guardadas en `national_team_codes.json`; se contrastó con la [lista actual de códigos FIFA](https://en.wikipedia.org/wiki/List_of_FIFA_country_codes) y la [tabla RSSSF](https://www.rsssf.org/miscellaneous/fifa-codes.html), corrigiendo variantes antiguas como Kosovo, Palestina y Mongolia. Solo se aplica cuando los dos oponentes son nombres completos reconocidos de selecciones, evitando cambiar palabras de países dentro de nombres de clubes. No modifica emparejamientos, fuentes, horarios ni UID.

Betis se muestra sin Real en todas las competiciones; CDA Navalcarnero se muestra como Navalcarnero; Amistoso de selecciones se muestra como Amistoso (incluidos grupos). El nombre antiguo La Equidad se muestra como Internacional de Bogotá, confirmado por el [comunicado oficial del club](https://interbogota.com/noticias/nace-internacional-de-bogota-el-nuevo-club-de-futbol-de-la-capital). Ambos nombres se reconocen como el mismo equipo para conservar deduplicación e identidad cuando el proveedor actualice su denominación.
