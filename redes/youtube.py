"""YouTube (Shorts si el video es vertical y dura menos de 3 minutos) con la API oficial.
Usa el mismo cliente OAuth de Google que Drive y Sheets (ver redes/google.py) y el refresh token de cada canal.
Ojo: mientras el proyecto de Google no pase la revisión de YouTube, los videos subidos por API quedan privados."""
import json, os, urllib.error, urllib.request


class ErrorYouTube(Exception):
    pass


def _pedir(req):
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.headers, r.read()
    except urllib.error.HTTPError as e:
        raise ErrorYouTube(f"YouTube respondió error {e.code}: {e.read()[:400].decode(errors='replace')}")


def subir(acceso, video, titulo, descripcion, privacidad="public"):
    meta = {"snippet": {"title": titulo[:100], "description": descripcion[:5000], "categoryId": "22"},
            "status": {"privacyStatus": privacidad, "selfDeclaredMadeForKids": False}}
    tam = os.path.getsize(video)
    cab, _ = _pedir(urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(), method="POST",
        headers={"Authorization": f"Bearer {acceso}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(tam)}))
    _, cuerpo = _pedir(urllib.request.Request(cab["Location"], data=open(video, "rb").read(), method="PUT",
                                              headers={"Authorization": f"Bearer {acceso}", "Content-Type": "video/mp4"}))
    return json.loads(cuerpo)["id"]


def poner_portada(acceso, video_id, imagen):
    """Miniatura de un video ya subido (máx. 2 MB; el canal debe estar verificado con teléfono)."""
    _pedir(urllib.request.Request(f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
                                  data=open(imagen, "rb").read(), method="POST",
                                  headers={"Authorization": f"Bearer {acceso}", "Content-Type": "image/jpeg"}))
