"""Facebook e Instagram (Reels) con el token de la página. El token de página no caduca.
Se sube el archivo directo a Meta (subida "resumable"): el video no tiene que estar en una URL pública."""
import json, os, shutil, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://graph.facebook.com/v26.0"


class ErrorMeta(Exception):
    pass


def pedir(metodo, url, datos=None, cabeceras=None, cuerpo=None):
    if datos is not None:
        cuerpo = urllib.parse.urlencode(datos).encode()
    r = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cabeceras or {})
    try:
        return json.load(urllib.request.urlopen(r, timeout=600))
    except urllib.error.HTTPError as e:
        raise ErrorMeta(f"Meta respondió error {e.code}: {e.read()[:400].decode(errors='replace')}")


def cuenta(token):
    """Página e Instagram conectados a este token."""
    return pedir("GET", f"{API}/me?fields=id,name,instagram_business_account{{id,username}}&access_token={token}")


def subir(url, token, video):
    cuerpo = open(video, "rb").read()
    return pedir("POST", url, cuerpo=cuerpo, cabeceras={"Authorization": f"OAuth {token}", "offset": "0",
                                                         "file_size": str(len(cuerpo))})


def version_ligera(video):
    """Copia con menos bitrate (mismo formato) para reintentar en Instagram, que a ratos se atraganta."""
    ligero = video.rsplit(".", 1)[0] + "_ligero.mp4"
    if not os.path.exists(ligero):
        if not shutil.which("ffmpeg"):
            subprocess.run("sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg > /dev/null", shell=True, check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.2",
                        "-pix_fmt", "yuv420p", "-crf", "23", "-maxrate", "5M", "-bufsize", "10M", "-g", "60", "-r", "30",
                        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", ligero], check=True)
    return ligero


def facebook(token, video, texto, portada=None):
    yo = cuenta(token)
    c = pedir("POST", f"{API}/{yo['id']}/video_reels", {"upload_phase": "start", "access_token": token})
    subir(c["upload_url"], token, video)
    r = pedir("POST", f"{API}/{yo['id']}/video_reels", {"upload_phase": "finish", "video_id": c["video_id"],
                                                        "video_state": "PUBLISHED", "description": texto,
                                                        "access_token": token})
    if not r.get("success"):
        raise ErrorMeta(f"Facebook respondió: {r}")
    if portada:
        poner_portada(token, c["video_id"], portada)
    return c["video_id"]


def poner_portada(token, video_id, archivo):
    """Miniatura del reel de Facebook. Si falla, el video ya está arriba: solo se avisa en el registro."""
    limite = "----publicador" + str(int(time.time()))
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"is_preferred\"\r\n\r\ntrue\r\n"
              f"--{limite}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"portada.jpg\"\r\n"
              f"Content-Type: image/jpeg\r\n\r\n").encode() + open(archivo, "rb").read() + f"\r\n--{limite}--\r\n".encode()
    error = ""
    for _ in range(4):   # el reel recién publicado tarda un poco en existir
        time.sleep(30)
        try:
            urllib.request.urlopen(urllib.request.Request(f"{API}/{video_id}/thumbnails?access_token={token}", data=cuerpo,
                                   method="POST", headers={"Content-Type": f"multipart/form-data; boundary={limite}"}), timeout=120)
            return
        except urllib.error.HTTPError as e:
            error = f"{e.code}: {e.read()[:200]}"
    print(f"aviso: Facebook no aceptó la portada ({error})")


def enlace_oculto(token, video):
    """Sube el video a la página de Facebook SIN publicarlo (nadie lo ve) y devuelve su enlace directo al mp4."""
    yo = cuenta(token)
    limite = "----publicador" + str(int(time.time()))
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"published\"\r\n\r\nfalse\r\n"
              f"--{limite}\r\nContent-Disposition: form-data; name=\"source\"; filename=\"video.mp4\"\r\n"
              f"Content-Type: video/mp4\r\n\r\n").encode() + open(video, "rb").read() + f"\r\n--{limite}--\r\n".encode()
    v = pedir("POST", f"https://graph-video.facebook.com/v26.0/{yo['id']}/videos?access_token={token}", cuerpo=cuerpo,
              cabeceras={"Content-Type": f"multipart/form-data; boundary={limite}"})
    for _ in range(30):   # Facebook tarda un poco en dejar listo el enlace
        time.sleep(10)
        fuente = pedir("GET", f"{API}/{v['id']}?fields=source&access_token={token}").get("source")
        if fuente:
            print("aviso: Instagram recibe el video por enlace (plan B)")
            return fuente
    raise ErrorMeta("Facebook no entregó el enlace del video oculto para Instagram.")


def instagram(token, video, texto, ligero=False):
    ig = (cuenta(token).get("instagram_business_account") or {}).get("id")
    if not ig:
        raise ErrorMeta("La página no tiene un Instagram profesional conectado.")
    if ligero:
        video = version_ligera(video)
    for n in range(3):   # a ratos Meta rechaza la subida y minutos después la acepta
        c = pedir("POST", f"{API}/{ig}/media", {"media_type": "REELS", "upload_type": "resumable", "caption": texto,
                                               "share_to_feed": "true", "access_token": token})
        try:
            subir(c["uri"], token, video)
            break
        except ErrorMeta as e:
            print(f"aviso: Instagram rechazó la subida ({e})")
            if n == 2:
                # plan B: el video se sube oculto a la página de Facebook y se le pasa a Instagram ese enlace
                c = pedir("POST", f"{API}/{ig}/media", {"media_type": "REELS", "video_url": enlace_oculto(token, video),
                                                       "caption": texto, "share_to_feed": "true", "access_token": token})
                break
            print("reintento en 2 minutos")
            time.sleep(120)
    for _ in range(60):   # Instagram procesa el video (hasta ~10 min)
        s = pedir("GET", f"{API}/{c['id']}?fields=status_code,status&access_token={token}")
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise ErrorMeta(f"Instagram no pudo procesar el video: {s.get('status')}")
        time.sleep(10)
    else:
        raise ErrorMeta("Instagram tardó demasiado en procesar el video.")
    return pedir("POST", f"{API}/{ig}/media_publish", {"creation_id": c["id"], "access_token": token})["id"]
