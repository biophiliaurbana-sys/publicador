# Publicador

Sube videos a **Facebook, Instagram y YouTube** a la hora que digas, solo, con el PC apagado.
Sirve para cualquier página: las tuyas o las de un cliente. No guarda recetas ni motores: solo recibe el video
terminado y lo publica. Las claves van en los *secrets* del repo, nunca en el código.

## Cómo funciona

1. Un video entra a la **cola**: es un *release* de este repo marcado como *pre-release*.
2. Cada hora, GitHub revisa la cola y sube lo que ya le tocó (`publicar.py`).
3. Cada red se marca apenas sale. Si una falla, las demás salen igual, y la que falló se reintenta cada hora con
   una versión más liviana. Si a la tercera vuelta sigue fallando, te llega un aviso (issue); a las 24 horas se deja.
4. Lo publicado queda con ✅ en el título y sale de la cola. El video queda guardado en el release.

## Dejar un video en la cola

**Desde el celular o el navegador (a mano):**

1. En este repo: **Releases → Draft a new release**.
2. *Choose a tag*: escribe cualquier nombre nuevo (por ejemplo `em-28oct-20h`) y elige *Create new tag*.
3. **Título**, exactamente así: `entrenando-mentes | 2026-10-28 20:00` (página | fecha y hora de Chile).
4. **Texto**: lo que va en la publicación. La primera línea también es el título en YouTube.
5. Adjunta el video (`.mp4`) y, si quieres, `portada.jpg`.
6. Marca **Set as a pre-release** y aprieta **Publish release**.

**Desde el PC o un agente (DeepSeek Harness, Antigravity, etc.):**

```
python encolar.py --pagina entrenando-mentes --video video.mp4 --hora "2026-10-28 20:00" --texto "Encuentra el diferente 🧠"
```

Necesita una clave de GitHub en la variable `GITHUB_TOKEN` (con GitHub CLI: `gh auth token`).

**Desde el repo privado de una marca (GitHub Actions):** guarda en ese repo un secreto `PUBLICADOR_TOKEN`
(clave *fine-grained* con permiso *Contents: write* solo en este repo) y al final del armado:

```
GITHUB_TOKEN=${{ secrets.PUBLICADOR_TOKEN }} python encolar.py --pagina ... --video ... --hora ... --texto-archivo texto.txt
```

## Agregar una página

1. Crea `paginas/<nombre>.json`:
   ```json
   { "nombre": "Mi Tienda", "redes": ["facebook", "instagram", "youtube"],
     "meta": "META_MI_TIENDA", "youtube": "YT_MI_TIENDA" }
   ```
2. En **Settings → Secrets and variables → Actions** agrega los secretos con esos nombres:
   - `META_...`: el token de la página de Facebook. Sirve también para el Instagram conectado a esa página.
   - `YT_...`: el *refresh token* del canal de YouTube, más `YT_CLIENT_ID` y `YT_CLIENT_SECRET` una sola vez.
3. Prueba: **Actions → Publicar → Run workflow** con "Solo probar" marcado. Muestra la cola y si cada clave funciona.

> **YouTube:** mientras el proyecto de Google no pase la revisión de YouTube, los videos que sube la API quedan
> **privados**. Para publicarlos públicos hay que pedir esa revisión (es gratis).

## Por qué es público

Los repos públicos tienen minutos de GitHub Actions ilimitados. Aquí no hay nada privado: el código solo sabe
publicar, y las claves están en *secrets*, que nadie puede ver. Ojo: los videos de la cola sí se pueden ver desde
*Releases* antes de su hora.
