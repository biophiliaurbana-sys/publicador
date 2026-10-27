"""Google con tu propia cuenta (Drive para los videos, Sheets para la cola, YouTube para publicar).
Un solo cliente OAuth (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) y un refresh token por cuenta o canal,
que se saca una vez con autorizar_google.py. Los archivos quedan privados en tu Drive: nadie más los ve."""
import json, os, re, urllib.error, urllib.parse, urllib.request


class ErrorGoogle(Exception):
    pass


def pedir(req, crudo=False):
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            cuerpo = r.read()
            return (r.headers, cuerpo) if crudo else (json.loads(cuerpo) if cuerpo else {})
    except urllib.error.HTTPError as e:
        raise ErrorGoogle(f"Google respondió error {e.code}: {e.read()[:400].decode(errors='replace')}")


def acceso(cliente_id, cliente_secreto, refresh):
    datos = urllib.parse.urlencode({"client_id": cliente_id, "client_secret": cliente_secreto,
                                    "refresh_token": refresh, "grant_type": "refresh_token"}).encode()
    return pedir(urllib.request.Request("https://oauth2.googleapis.com/token", data=datos, method="POST"))["access_token"]


def _req(token, url, metodo="GET", datos=None, cuerpo=None, cabeceras=None):
    h = {"Authorization": f"Bearer {token}", **(cabeceras or {})}
    if datos is not None:
        cuerpo, h["Content-Type"] = json.dumps(datos).encode(), "application/json; charset=UTF-8"
    return urllib.request.Request(url, data=cuerpo, method=metodo, headers=h)


# ---- Sheets (la cola) ----
HOJAS = "https://sheets.googleapis.com/v4/spreadsheets"


def leer(token, hoja, rango):
    url = f"{HOJAS}/{hoja}/values/{urllib.parse.quote(rango)}?valueRenderOption=FORMATTED_VALUE"
    return pedir(_req(token, url)).get("values", [])


def escribir(token, hoja, rango, filas):
    url = f"{HOJAS}/{hoja}/values/{urllib.parse.quote(rango)}?valueInputOption=RAW"
    pedir(_req(token, url, "PUT", {"values": filas}))


def agregar(token, hoja, rango, filas):
    url = f"{HOJAS}/{hoja}/values/{urllib.parse.quote(rango)}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    pedir(_req(token, url, "POST", {"values": filas}))


# ---- Drive (los videos) ----
def id_drive(link):
    """ID de un archivo a partir de su link de Drive (o el ID tal cual)."""
    m = re.search(r"/d/([\w-]{20,})", link or "") or re.search(r"[?&]id=([\w-]{20,})", link or "")
    return m.group(1) if m else (link or "").strip()


def bajar(token, archivo_id, destino):
    _, cuerpo = pedir(_req(token, f"https://www.googleapis.com/drive/v3/files/{archivo_id}?alt=media&supportsAllDrives=true"),
                      crudo=True)
    with open(destino, "wb") as f:
        f.write(cuerpo)
    return destino


def a_papelera(token, archivo_id):
    """Manda un archivo de Drive a la papelera (Google lo borra solo a los 30 días; se puede recuperar antes)."""
    pedir(_req(token, f"https://www.googleapis.com/drive/v3/files/{archivo_id}", "PATCH", datos={"trashed": True}))


def subir(token, ruta, carpeta_id, nombre=None, tipo="video/mp4"):
    """Sube un archivo a una carpeta de tu Drive (queda privado) y devuelve su link."""
    meta = {"name": nombre or os.path.basename(ruta), "parents": [carpeta_id] if carpeta_id else []}
    cab, _ = pedir(_req(token, "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true",
                        "POST", meta, cabeceras={"X-Upload-Content-Type": tipo,
                                                 "X-Upload-Content-Length": str(os.path.getsize(ruta))}), crudo=True)
    _, cuerpo = pedir(_req(token, cab["Location"], "PUT", cuerpo=open(ruta, "rb").read(),
                           cabeceras={"Content-Type": tipo}), crudo=True)
    return f"https://drive.google.com/file/d/{json.loads(cuerpo)['id']}/view"
