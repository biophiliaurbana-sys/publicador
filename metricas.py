"""Reproducciones de cada página (solo lee, no publica nada). Sale en la corrida "solo probar" del publicador.

Facebook/Instagram: los últimos Reels de la página con la llave de Meta de paginas/*.json.
YouTube: los videos que subió el publicador (ids guardados en la cola), con la llave de cada canal.
Cada fila empieza con "VIDEO" y va separada por tabulaciones (fácil de copiar a una planilla)."""
import json, urllib.error, urllib.parse, urllib.request

API = "https://graph.facebook.com/v26.0"


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"error {e.code}: {e.read()[:200].decode(errors='replace')}")


def _meta(token, ruta, **q):
    q["access_token"] = token
    return _get(f"{API}/{ruta}?{urllib.parse.urlencode(q)}")


def _valor(token, ident, ruta, nombres):
    for n in nombres:
        try:
            d = _meta(token, f"{ident}/{ruta}", metric=n)["data"]
            return d[0]["values"][0]["value"] if d else None
        except Exception:
            continue
    return None


def _fila(*campos):
    print("VIDEO\t" + "\t".join("" if x is None else " ".join(str(x).split()) for x in campos))


def meta(nombre, token):
    yo = _meta(token, "me", fields="id,name,instagram_business_account")
    ig = (yo.get("instagram_business_account") or {}).get("id")
    if ig:
        for m in _meta(token, f"{ig}/media", fields="id,caption,timestamp,like_count,comments_count,permalink",
                       limit=60).get("data", []):
            seg = _valor(token, m["id"], "insights", ["ig_reels_avg_watch_time"])
            _fila(nombre, "IG", m["timestamp"][:16], _valor(token, m["id"], "insights", ["views", "plays", "reach"]),
                  f"{seg / 1000:.1f}" if seg else None, m.get("like_count"), m.get("comments_count"),
                  (m.get("caption") or "").split("\n")[0][:70], m.get("permalink"))
    for v in _meta(token, f"{yo['id']}/video_reels", fields="id,description,created_time,permalink_url",
                   limit=60).get("data", []):
        seg = _valor(token, v["id"], "video_insights", ["post_video_avg_time_watched"])
        _fila(nombre, "FB", v["created_time"][:16],
              _valor(token, v["id"], "video_insights", ["blue_reels_play_count", "fb_reels_total_plays"]),
              f"{seg / 1000:.1f}" if seg else None, None, None,
              (v.get("description") or "").split("\n")[0][:70], v.get("permalink_url"))


def youtube(nombre, acceso, ids):
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"part": "snippet,statistics,status", "id": ",".join(ids[i:i + 50])})
        req = urllib.request.Request(f"https://www.googleapis.com/youtube/v3/videos?{q}",
                                     headers={"Authorization": f"Bearer {acceso}"})
        for v in _get(req).get("items", []):
            s = v.get("statistics", {})
            _fila(nombre, "YT", v["snippet"]["publishedAt"][:16], s.get("viewCount"), None, s.get("likeCount"),
                  s.get("commentCount"), f"[{v['status']['privacyStatus']}] {v['snippet']['title'][:60]}",
                  f"https://youtu.be/{v['id']}")


def mostrar(paginas, secretos, acceso_google, items):
    print("\n==== Reproducciones (columnas: página, red, fecha UTC, vistas, segundos promedio, me gusta, comentarios, texto, link)")
    for clave, pag in paginas.items():
        if not pag:
            continue
        token = secretos.get(pag.get("meta", ""))
        if token and {"facebook", "instagram"} & set(pag["redes"]):
            try:
                meta(pag["nombre"], token)
            except Exception as ex:
                print(f"{pag['nombre']}: no pude leer Facebook/Instagram ({' '.join(str(ex).split())[:200]})")
        ids = [str(it.estado.get("ids", {}).get("youtube")) for it in items
               if (getattr(it, "nombre", "") or "").strip().lower() == clave and it.estado.get("ids", {}).get("youtube")]
        if ids and "youtube" in pag["redes"]:
            try:
                youtube(pag["nombre"], acceso_google(pag["youtube"]), ids)
            except Exception as ex:
                print(f"{pag['nombre']}: no pude leer YouTube ({' '.join(str(ex).split())[:200]})")
