"""Videos guardados en GitHub: cada video es un *release* de un repo privado de marca (con video.mp4 adjunto).
Lo usan las páginas que arman su contenido solas (Entrenando Mentes, Buscadores…), para no pasar por Drive.
El release lleva en su texto una marca oculta con la página, la fecha, la hora y el estado:
  <!-- publicador {"pagina": "entrenando-mentes", "fecha": "2026-10-28", "hora": "13:00", "estado": {}} -->
El título del release muestra el estado (🕒 ⏳ ✅ ⚠️). Si empieza con ⛔, está frenado y no sale."""
import base64, json, re, urllib.error, urllib.request

API = "https://api.github.com"
MARCA = re.compile(r"<!--\s*publicador\s*(\{.*?\})\s*-->", re.S)


class ErrorGitHub(Exception):
    pass


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def pedir(llave, metodo, url, datos=None, cabeceras=None, crudo=False, cuerpo=None):
    h = {"Authorization": f"Bearer {llave}", "Accept": "application/vnd.github+json", **(cabeceras or {})}
    r = urllib.request.Request(url if url.startswith("http") else API + url, method=metodo, headers=h,
                               data=json.dumps(datos).encode() if datos is not None else cuerpo)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            cuerpo = resp.read()
            return cuerpo if crudo else json.loads(cuerpo or b"null")
    except urllib.error.HTTPError as e:
        raise ErrorGitHub(f"GitHub respondió error {e.code}: {e.read()[:300].decode(errors='replace')}")


def releases(llave, repo, cuantos=100):   # los más nuevos primero; los ya ✅ se saltan rápido
    return pedir(llave, "GET", f"/repos/{repo}/releases?per_page={cuantos}")


def leer_marca(cuerpo):
    m = MARCA.search(cuerpo or "")
    if not m:
        return None, (cuerpo or "").strip()
    return json.loads(m.group(1)), MARCA.sub("", cuerpo).strip()


def poner_marca(texto, marca):
    return f"{texto.strip()}\n\n<!-- publicador {json.dumps(marca, ensure_ascii=False)} -->\n"


def editar(llave, repo, release_id, **campos):
    pedir(llave, "PATCH", f"/repos/{repo}/releases/{release_id}", campos)


def bajar(llave, repo, asset_id, destino):
    """El archivo de un release privado: GitHub redirige a un link temporal que se baja SIN la llave."""
    r = urllib.request.Request(f"{API}/repos/{repo}/releases/assets/{asset_id}",
                               headers={"Authorization": f"Bearer {llave}", "Accept": "application/octet-stream"})
    try:
        with urllib.request.build_opener(_SinRedireccion).open(r, timeout=120) as resp:   # (si no redirige, viene aquí)
            datos = resp.read()
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise ErrorGitHub(f"GitHub no entregó el video (error {e.code})")
        with urllib.request.urlopen(e.headers["Location"], timeout=900) as resp:
            datos = resp.read()
    with open(destino, "wb") as f:
        f.write(datos)
    return destino


def borrar_archivo(llave, repo, asset_id):
    pedir(llave, "DELETE", f"/repos/{repo}/releases/assets/{asset_id}", crudo=True)


def leer_archivo(llave, repo, ruta):
    """Un archivo del repo (rama principal): (contenido en bytes, sha) o (None, None) si no existe."""
    try:
        info = pedir(llave, "GET", f"/repos/{repo}/contents/{ruta}")
    except ErrorGitHub as e:
        if "error 404" in str(e):
            return None, None
        raise
    if not info.get("content"):   # más de 1 MB: la API no lo trae en base64, se pide crudo
        return pedir(llave, "GET", f"/repos/{repo}/contents/{ruta}", cabeceras={"Accept": "application/vnd.github.raw"},
                     crudo=True), info["sha"]
    return base64.b64decode(info["content"]), info["sha"]


def escribir_archivo(llave, repo, ruta, contenido, sha, mensaje):
    pedir(llave, "PUT", f"/repos/{repo}/contents/{ruta}",
          {"message": mensaje, "content": base64.b64encode(contenido).decode(), "sha": sha})


def subir_archivo(llave, repo, release_id, nombre, archivo, tipo):
    pedir(llave, "POST", f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={nombre}",
          cabeceras={"Content-Type": tipo}, crudo=True, cuerpo=open(archivo, "rb").read())
