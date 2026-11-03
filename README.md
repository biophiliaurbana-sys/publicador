# Publicador

Programa tus videos de la semana y se suben **solos** a **Instagram, Facebook y YouTube** a la hora que digas,
con el computador apagado. No hay que saber programar: todo se maneja desde una **planilla de Google** y una
carpeta de **Google Drive**.

Ejemplo: la encargada de redes de un gimnasio graba 5 videos el lunes, los sube a Drive, llena 5 filas en la
planilla (día, hora y texto de cada uno) y se olvida. Cada video sale a su hora en todas las redes.

## Cómo funciona (en simple)

```
  Tú: video en Drive + una fila en la planilla
                │
  cron-job.org (gratis) despierta a GitHub cada 15 minutos
                │
  GitHub (gratis) lee la planilla → ¿a algún video ya le tocó? → lo sube a cada red
                │
  La planilla se marca sola: 🕒 en cola · ⏳ subiendo/reintentando · ✅ publicado · ⚠️ problema
```

- **Por qué GitHub:** corre el programa en la nube, gratis (este repo es público, así que los minutos son ilimitados).
  En el código **no hay nada tuyo**: tus páginas, videos y planilla están en tu Google, y las llaves en los
  *secrets* de GitHub, que nadie puede ver.
- **Por qué cron-job.org:** el reloj propio de GitHub a veces se atrasa horas. cron-job.org lo despierta puntual.
- **Instagram y Facebook:** usa la API oficial de Meta con la llave de tu página, así que no tienes que programar
  cada Reel a mano en Meta Business Suite. Lo mismo con YouTube (API oficial de Google).
- Si una red falla, las otras salen igual y la que falló se reintenta sola cada vez. Si a las 24 h no pudo, te
  llega un aviso a la app de GitHub.
- Cuando un video ya salió en todas sus redes, se manda a la **papelera** de Drive para no llenarla.

## La planilla

Una planilla de Google con 2 pestañas (o 3 si usas las avanzadas):

### Pestaña `cola`: una fila por video

| A página | B fecha | C hora | D video | E texto | F portada | G estado | H detalle |
|---|---|---|---|---|---|---|---|
| mi-gimnasio | 2026-11-10 | 19:00 | link del video en Drive | texto de la publicación | (opcional) link de una imagen | *lo llena el sistema* | *lo llena el sistema* |

- **fecha:** `2026-11-10` o `10/11/2026`. **hora:** `19:00`, hora local.
- **texto:** lo que va en la publicación (con hashtags). La primera línea es también el título en YouTube.
- **G y H no se tocan.** Para **frenar** un video que aún no sale, escribe `⛔` en su columna G.

### Pestaña `paginas`: una fila por página o cuenta

| A página | B nombre | C redes | D llave Meta | E llave YouTube |
|---|---|---|---|---|
| mi-gimnasio | Gimnasio Ejemplo | instagram, facebook, youtube | META_MI_GIMNASIO | YT_MI_GIMNASIO |

- **página:** un nombre corto, sin espacios. Es lo que escribes en la columna A de la cola.
- **llave Meta / llave YouTube:** el **nombre** del secreto donde guardaste esa llave (ver más abajo), no la llave.
- Columnas avanzadas (opcionales), para páginas que **arman sus videos solas con código** en un repo privado:
  **F por día** (cuántos videos se esperan al día; si faltan, llega un aviso), **G repo** (repo privado donde
  deja sus videos como *releases*), **H armar con** (el workflow que los arma; si faltan videos, se relanza solo),
  **I armar desde** (desde qué hora relanzarlo) y **J datos** (inputs del workflow en JSON). Ver `config.py`.

### Pestaña `otros` (opcional, avanzada)

Páginas que publican desde su propio repo y dejan un aviso diario. El publicador no las sube, solo las incluye en
el resumen del día y las relanza si no se armaron. Columnas: nombre · repo · horas · armar con · armar desde · datos.

## Instalarlo (una sola vez, ~1 hora)

1. **Tu copia:** en GitHub, botón **Fork** (o *Use this template*). Déjala **pública**: así los minutos son gratis
   e ilimitados, y en el código no queda nada tuyo.
2. **La planilla:** crea una planilla de Google con las pestañas `cola` y `paginas` (con los títulos de arriba).
   Copia su ID (lo que va entre `/d/` y `/edit` en el link) y guárdalo en tu repo en
   *Settings → Secrets and variables → Actions → Variables* como **`HOJA_COLA`**.
3. **Google (Drive, planilla y YouTube):** crea un cliente OAuth en Google Cloud (tipo "App de escritorio") y deja la
   app en modo **"En producción"** (en modo "Prueba" las llaves vencen cada 7 días). En tu PC, al lado del JSON
   del cliente, corre `python autorizar_google.py` y guarda lo que entrega en los *secrets* `GOOGLE_CLIENT_ID`,
   `GOOGLE_CLIENT_SECRET` y `GOOGLE_REFRESH`. Para cada canal de YouTube: `python autorizar_google.py --youtube`
   (eliges el canal) y lo guardas en un secreto `YT_...` (el nombre que pusiste en la pestaña paginas).
4. **Instagram y Facebook:** la página de Facebook tiene que estar unida a la cuenta de Instagram (profesional).
   Saca una llave de página que no venza (Explorador de la API Graph de Meta) y guárdala en un secreto `META_...`.
   La misma llave sirve para Facebook y su Instagram.
5. **El despertador:** en GitHub, *Settings → Developer settings → Fine-grained tokens*, crea una llave solo para
   tu repo con permiso **Actions: Read and write**. En **cron-job.org** crea una tarea cada 15 minutos:
   - URL: `https://api.github.com/repos/<tu-usuario>/<tu-repo>/actions/workflows/publicar.yml/dispatches`
   - Método **POST**, cuerpo `{"ref":"main"}`
   - Encabezados: `Authorization: Bearer <tu llave>` y `Accept: application/vnd.github+json`
6. **Probar:** en tu repo, *Actions → Publicar → Run workflow* con **"Solo probar"** marcado. Muestra la cola,
   si cada llave funciona y las vistas de tus últimos videos. No publica nada.

> **YouTube:** mientras tu proyecto de Google no pase la revisión de YouTube (es gratis pedirla), los videos que
> sube la API pueden quedar **privados**.

## El día a día

1. Sube los videos de la semana a tu carpeta de Drive.
2. Por cada video, una fila en la pestaña `cola`: página, fecha, hora, link del video y texto.
3. Listo. Mira la columna G para ver cómo va cada uno.

**Desde el PC o con una IA** (Claude, ChatGPT/Codex, Gemini…): `encolar.py` sube el video a Drive y agrega la fila:

```
python encolar.py --pagina mi-gimnasio --video video.mp4 --hora "2026-11-10 19:00" --texto "Nueva ruta 🧗"
```

Las llaves para esto van en un archivo `.env` al lado del script (nunca se sube a GitHub): `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH`, `HOJA_COLA` y `CARPETA_VIDEOS` (ID de la carpeta de Drive).

## Extras

- **Días de pausa:** una fecha por línea en `pausa.txt` (`2026-12-25`) y ese día no sale nada.
- **Avisos en el celular** (app de GitHub, etiqueta `resumen`): a las 9:30 si faltan videos de hoy, y a las 22:30 un
  resumen de qué salió en cada red y qué falló.
- **Estadísticas:** "Solo probar" también muestra, por video, vistas, segundos promedio que lo miran, % visto
  (YouTube), me gusta y comentarios.
- **Zona horaria:** por defecto `America/Santiago`. Para otra, cambia `ZONA` en `publicar.py`.
- **¿Edita videos?** No: este repo **solo publica**. Los videos pueden venir editados a mano, de una app, o de otro
  repo que los arme con código y los deje como *releases* (columnas avanzadas de la pestaña paginas).

Instrucciones para una IA que te ayude a usarlo o arreglarlo: `AGENTS.md`.
