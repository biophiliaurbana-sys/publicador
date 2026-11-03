# Instrucciones para cualquier IA (Claude, Codex, Gemini, DeepSeek, una IA local…)

Este repo publica videos en Instagram, Facebook y YouTube a su hora. Lee README.md primero.
El repo es **público**: nunca escribas aquí nombres de páginas, IDs de planillas, correos ni llaves.
Todo lo del dueño vive en su planilla (pestañas `cola`, `paginas`, `otros`) y en los *secrets* del repo.

Pedidos típicos:
- "Sube el video X a la página Y a tal hora" → `python encolar.py --pagina Y --video X --hora "AAAA-MM-DD HH:MM" --texto "..."`.
  Las páginas válidas son las de la columna A de la pestaña `paginas`. Varios videos → un `encolar.py` por video.
- "¿Qué hay en la cola?" → pestaña `cola`; la columna G dice el estado de cada video.
- "Saca/cambia un video" → borra o edita su fila, solo si la columna G no dice ✅.
- "Frena tal video" → `python frenar.py <link de Drive>` (pone ⛔ en la columna G; no borra nada).
- "Agrega una página" → una fila nueva en la pestaña `paginas` + sus secretos `META_...`/`YT_...` (los guarda el dueño).
- Páginas que se arman solas (columna "repo"): su cola son los *releases* de ese repo privado, con una marca oculta
  (ver `redes/github.py`); frenar = poner ⛔ al inicio del título del release. `"redes": ["youtube"]` en la marca
  publica solo en esas redes.
- "¿Por qué no salió?" → columna G de su fila, los avisos (issues con etiqueta `resumen`) y la última corrida de
  *Actions → Publicar*.

Cómo se despierta: una tarea de cron-job.org (cuenta del dueño) lanza *Publicar* cada 15 min con una llave de
GitHub que solo puede correr Actions. Si nada sale en horas, revisa primero esa tarea.

Secretos (solo nombres, nunca valores): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH` (Drive y planilla);
opcional `YT_CLIENT_ID`, `YT_CLIENT_SECRET` (otro proyecto de Google solo para YouTube); uno `META_...` y/o `YT_...` por
página (sus nombres están en la pestaña `paginas`); `LLAVE_REPOS` (lee los repos privados de las páginas que se arman
solas; con permiso Actions para relanzarlas). Variable: `HOJA_COLA` (ID de la planilla).

Reglas:
- Nunca publiques al instante: todo va a la cola con fecha y hora.
- Nunca escribas llaves en archivos que se suban a GitHub ni en mensajes; viven en `.env` (ignorado por git) y en los
  *secrets*. No le pidas llaves al dueño en el chat: dile en qué secreto guardarlas.
- Los videos ya publicados (✅) se borran solos (Drive → papelera; releases → se quita el .mp4). Nada más se borra sin preguntar.
- Pide confirmación antes de encolar si la página, la hora o el texto no están claros.
- Prueba los cambios con *Run workflow* → "Solo probar" antes de darlos por buenos.
- Un cambio hecho por una IA a `.github/workflows/` en un repo público queda "action_required" hasta que el dueño lo
  apruebe en la web: evita tocar los workflows.

Arreglar errores:
- Mira la corrida de *Actions → Publicar* que falló y el aviso (issue) que abrió. "Solo probar" revisa llaves y cola;
  "prueba_youtube" sube un video privado de 3 s a cada canal.
- `invalid_grant` en YouTube = la llave venció (si la app de Google está en modo "Prueba", cada 7 días):
  `python autorizar_google.py --youtube` en el PC y el dueño la pega en su secreto `YT_...`.
- Llave de Meta inválida o vencida: sacar otra de página que no venza (Explorador de la API Graph) y guardarla en su `META_...`.

## Cambiar la portada de un video (páginas que se arman solas)
En el repo de la página, sube la imagen (jpg 1080x1920, menos de 2 MB) y agrega a `portadas.json`
`{"release": "<etiqueta del release>", "imagen": "portadas/<archivo>.jpg"}`. En la siguiente vuelta el publicador:
si el video ya salió, cambia la portada en Facebook y YouTube (Instagram no se puede por API); si aún no sale,
reemplaza la portada del release. Marca la entrada con `"hecho": true` y el resultado.
