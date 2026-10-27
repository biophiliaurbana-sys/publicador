# Publicador

Sube videos a **Facebook, Instagram y YouTube** a la hora que digas, solo, con el PC apagado.
Sirve para cualquier página: las tuyas o las de un cliente. No guarda recetas, motores ni videos: los videos
quedan **privados en tu Google Drive**, la cola es una **planilla tuya** y las claves van en los *secrets* del repo.

## Cómo funciona

1. Un video entra a la **cola**: una fila en la planilla (pestaña `cola`) con el link del video en tu Drive.
2. Cada hora, GitHub revisa la planilla y sube lo que ya le tocó (`publicar.py`).
3. Cada red se marca apenas sale. Si una falla, las demás salen igual, y la que falló se reintenta cada hora con
   una versión más liviana. Si a la tercera vuelta sigue fallando, te llega un aviso (issue); a las 24 horas se deja.
4. En la columna **estado** ves qué pasó con cada video: 🕒 en cola, ⏳ reintentando, ✅ publicado, ⚠️ problema.

## La planilla (pestaña `cola`)

| A página | B fecha | C hora | D video | E texto | F portada | G estado | H detalle |
|---|---|---|---|---|---|---|---|
| entrenando-mentes | 2026-10-28 | 20:00 | link de Drive | texto de la publicación | (opcional) | *lo llena el sistema* | *lo llena el sistema* |

- **página**: el nombre de un archivo de `paginas/` (sin `.json`).
- **fecha y hora**: de Chile. La fecha puede ir como `2026-10-28` o `28/10/2026`.
- **texto**: lo que va en la publicación. La primera línea también es el título en YouTube.
- **G y H no se tocan**: ahí el sistema anota lo que ya salió.

## Dejar un video en la cola

**Desde el celular:** sube el video a tu carpeta de Drive, copia su link y agrega una fila en la planilla.

**Desde el PC o un agente (DeepSeek Harness, Antigravity, etc.):**

```
python encolar.py --pagina entrenando-mentes --video video.mp4 --hora "2026-10-28 20:00" --texto "Encuentra el diferente 🧠"
```

Sube el video a tu Drive y agrega la fila solo. Lee las claves de un archivo `.env` al lado del script
(nunca se sube a GitHub):

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH=...
HOJA_COLA=...        (ID de la planilla: lo que va entre /d/ y /edit en su link)
CARPETA_VIDEOS=...   (ID de la carpeta de Drive: lo que va después de /folders/ en su link)
```

**Desde el repo privado de una marca (GitHub Actions):** las mismas claves como *secrets* de ese repo, y al final
del armado: `python encolar.py --pagina ... --video ... --hora ... --texto-archivo texto.txt`.

## Conectar (una sola vez)

1. **Google** (Drive, planilla y YouTube): un cliente OAuth en Google Cloud. Con él se corre en el PC
   `python autorizar_google.py` (al lado del JSON del cliente), que entrega el *refresh token*.
   En el repo: secretos `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH` y variable `HOJA_COLA`.
2. **Cada página**: un archivo `paginas/<nombre>.json`:
   ```json
   { "nombre": "Mi Tienda", "redes": ["facebook", "instagram", "youtube"],
     "meta": "META_MI_TIENDA", "youtube": "YT_MI_TIENDA" }
   ```
   y los secretos con esos nombres: `META_...` = token de la página de Facebook (sirve también para su Instagram);
   `YT_...` = refresh token del canal (`python autorizar_google.py --youtube`, eligiendo el canal).
3. **Probar**: *Actions → Publicar → Run workflow* con "Solo probar" marcado. Muestra la cola y si cada clave funciona.

> **Google Cloud:** deja la app OAuth en modo **"En producción"** (aunque no esté verificada); en modo "Prueba" el
> refresh token deja de servir a los 7 días.
> **YouTube:** mientras el proyecto de Google no pase la revisión de YouTube, los videos que sube la API quedan
> **privados**. Para publicarlos públicos hay que pedir esa revisión (es gratis).

## Por qué el repo es público

Los repos públicos tienen minutos de GitHub Actions ilimitados. Aquí no hay nada privado: el código solo sabe
publicar; los videos y la planilla están en tu Google y las claves en *secrets*, que nadie puede ver.
