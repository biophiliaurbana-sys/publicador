# Instrucciones para cualquier IA (Codex, Gemini, DeepSeek, Antigravity, Claude Code, una IA local…)

Este repo publica videos en Facebook, Instagram y YouTube a su hora. Lee README.md.

- "Sube el video X a la página Y a tal hora" → `python encolar.py --pagina Y --video X --hora "AAAA-MM-DD HH:MM" --texto "..."`.
  La hora es de Chile. Las páginas válidas son los archivos de `paginas/` (sin `.json`).
  Varios videos ("uno al día a las 20:00") → un `encolar.py` por video, cada uno con su fecha.
- "¿Qué hay en la cola?" → la planilla de la cola (pestaña `cola`); la columna G dice el estado de cada video.
- "Saca/cambia un video de la cola" → borra o edita su fila, solo si la columna G no dice ✅.
- "Frena tal video" → `python frenar.py <link de Drive>` (marca ⛔ en la columna G; no borra nada).
- Páginas que se arman solas (repos de `repos.json`): su cola son los *releases* de su repo privado; frenar = poner ⛔ al inicio del título del release.
  En la marca oculta, `"redes": ["youtube"]` publica solo en esas redes (p. ej. videos viejos que ya salieron en Facebook).
- Avisos del día (issues con la etiqueta `resumen`, ver `resumen.py`): a las 9:30 si faltan videos de hoy (cuántos se esperan:
  `"por_dia"` en `paginas/*.json`) y a las 22:30 el resumen (qué se creó, qué salió, errores), incluido El Dato de Fulvio
  si `LLAVE_REPOS` puede leer los issues de `dato-de-fulvio`.
- "¿Por qué no salió?" → columna G de su fila, los avisos (issues) y la última corrida de *Actions → Publicar*.

Qué páginas maneja (archivos de `paginas/`): `entrenando-mentes`, `buscadores-de-la-verdad`, `biophilia-urbana`
(FB + IG + YouTube) y `biophilia-urbana-en` (solo YouTube en inglés). El Dato de Fulvio NO pasa por aquí: publica desde su propio repo.

Cómo se despierta: el cron de GitHub no es confiable, así que cada 15 min una tarea de cron-job.org (cuenta de Danko,
tarea "Publicador") lanza *Publicar* con un token de GitHub que solo puede correr Actions. Si nada sale en horas,
revisar primero esa tarea en cron-job.org.

Secretos (Settings → Secrets and variables → Actions; solo nombres, nunca valores): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`GOOGLE_REFRESH` (Drive y planilla), `YT_CLIENT_ID`, `YT_CLIENT_SECRET` (app de YouTube), uno `META_...` y uno `YT_...` por página
(los nombres exactos están en `paginas/*.json`), `LLAVE_REPOS` (lee los releases de los repos de `repos.json`). Variable: `HOJA_COLA`.

Reglas:
- Nunca publiques al instante: todo va a la cola con fecha y hora. Nunca escribas claves en archivos que se suban
  a GitHub ni en mensajes; viven en `.env` (ignorado por git) y en los *secrets* del repo.
- Los videos ya publicados (✅) se borran solos (Drive → papelera; releases → se quita el .mp4). Nada más se borra sin preguntar.
- Pide confirmación antes de encolar si la página, la hora o el texto no están claros.

Arreglar errores:
- Mira la última corrida de *Actions → Publicar* (paso que falló) y el aviso (issue) que abrió. Prueba sin publicar con
  *Run workflow* → "solo_probar" (revisa llaves y cola) o "prueba_youtube" (sube un video privado de 3 s a cada canal).
- `invalid_grant` en YouTube = la llave venció (app en modo prueba, cada 7 días): en el PC, `python autorizar_google.py --youtube --cliente 758422210366`
  y Danko pega el resultado en el secreto `YT_<PÁGINA>`. Token de Meta inválido: rehacerlo en el Explorador de la API Graph.
- Un cambio de Claude/IA a `.github/workflows/` en este repo público queda "action_required" hasta que Danko lo apruebe en la web.

## Cambiar la portada de un video (repos de marca)
En el repo de la marca, sube la imagen (jpg 1080x1920, menos de 2 MB) y agrega a `portadas.json`
`{"release": "<etiqueta del release>", "imagen": "portadas/<archivo>.jpg"}`. En la siguiente vuelta el publicador:
si el video ya salió, cambia la portada en Facebook y YouTube (Instagram no se puede por API); si aún no sale,
reemplaza la portada del release. Marca la entrada con `"hecho": true` y el resultado.
