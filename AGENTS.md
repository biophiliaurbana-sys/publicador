# Instrucciones para el agente (DeepSeek Harness, Antigravity, Claude Code u otro)

Este repo publica videos en Facebook, Instagram y YouTube a su hora. Lee README.md.

- "Sube el video X a la página Y a tal hora" → `python encolar.py --pagina Y --video X --hora "AAAA-MM-DD HH:MM" --texto "..."`.
  La hora es de Chile. Las páginas válidas son los archivos de `paginas/` (sin `.json`).
  Varios videos ("uno al día a las 20:00") → un `encolar.py` por video, cada uno con su fecha.
- "¿Qué hay en la cola?" → la planilla de la cola (pestaña `cola`); la columna G dice el estado de cada video.
- "Saca/cambia un video de la cola" → borra o edita su fila, solo si la columna G no dice ✅.
- "Frena tal video" → `python frenar.py <link de Drive>` (marca ⛔ en la columna G; no borra nada).
- Páginas que se arman solas (repos de `repos.json`): su cola son los *releases* de su repo privado; frenar = poner ⛔ al inicio del título del release.
- "¿Por qué no salió?" → columna G de su fila, los avisos (issues) y la última corrida de *Actions → Publicar*.

Reglas:
- Nunca publiques al instante: todo va a la cola con fecha y hora. Nunca escribas claves en archivos que se suban
  a GitHub ni en mensajes; viven en `.env` (ignorado por git) y en los *secrets* del repo.
- No borres nada definitivamente (ni videos de Drive): pregunta antes.
- Pide confirmación antes de encolar si la página, la hora o el texto no están claros.
