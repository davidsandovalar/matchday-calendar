# ⚽ Matchday para Apple Calendar

Este proyecto reúne **Premier League**, **Champions League** y **21 equipos** en un archivo ICS. Deduplicación conservadora por equipos y fecha/hora. Publicación automática aproximadamente cada seis horas (sujeta a ejecución GitHub y a refresco de Apple).

## Instalación desde Mac

1. Crea una cuenta en https://github.com si no tienes.
2. Crea un repositorio público llamado `matchday-calendar` y elige **Add a README file**.
3. En la página del repositorio: **Add file → Upload files**. **Importante:** GitHub web puede no conservar archivos ocultos al arrastrar carpetas; usa GitHub Desktop para subir la carpeta entera, incluida `.github/workflows/matchday.yml`, o crea el workflow en la interfaz web manualmente.
4. Sube `main.py`, `sources.json`, `requirements.txt` y el contenido de `.github/workflows/matchday.yml` siguiendo la ruta exacta.
5. Abre **Settings → Pages → Build and deployment → Source → GitHub Actions**.
6. Abre **Actions → Actualizar Matchday → Run workflow → Run workflow**.
7. Verifica ejecución verde y abre `https://USUARIO.github.io/matchday-calendar/status.json` para comprobar 23 fuentes y un número positivo de eventos.
8. Suscríbete a `https://USUARIO.github.io/matchday-calendar/matchday.ics` desde Apple Calendar → Calendars → Add Calendar → Add Subscription Calendar. Sustituye USUARIO por tu nombre de usuario de GitHub.
9. **Solo cuando funcione**, elimina las tres suscripciones anteriores (Premier League, Champions League y Real Madrid) para evitar duplicados.

## Importante

- La extracción del enlace Apple iCal desde Fixtur.es es exploratoria y **no pudo probarse contra la web real desde el entorno de creación**. Si los enlaces están escritos mediante JavaScript o tienen una ruta protegida, el primer workflow fallará y habrá que sustituirlos por las 23 URLs ICS reales.
- El programa falla cuando una fuente no está disponible, para no publicar un calendario incompleto. Se conserva la última versión publicada.
- La comparación elimina duplicados obvios; no garantiza el 100 % si hay alias desconocidos o cambios de horario superiores a 30 minutos entre fuentes.
- El calendario Apple puede tardar en recoger cambios según sus intervalos de actualización.
- Los trabajos programados de GitHub Actions pueden desactivarse por inactividad prolongada del repositorio público.
