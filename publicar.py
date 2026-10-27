"""PUBLICADOR · revisa la cola y sube a su hora lo que toca (lo corre .github/workflows/publicar.yml cada hora).
  python publicar.py            → publica lo que ya le tocó
  python publicar.py --prueba   → muestra la cola y revisa las claves, sin publicar nada

La cola son los "releases" de este repo marcados como pre-release (los crea encolar.py o se crean a mano):
  · título:  "<página> | AAAA-MM-DD HH:MM"   (hora de Chile; <página> = un archivo de paginas/)
  · texto:   el texto de la publicación (la primera línea es también el título en YouTube)
  · adjuntos: el video (.mp4) y, si quieres, portada.jpg
Cada red se marca apenas sale, así un reintento nunca la repite. Si una red falla, las otras salen igual y la
que falló se reintenta cada hora con una versión más liviana; si no sale en 24 h, se deja y se abre un aviso.
Las claves vienen todas juntas en la variable SECRETOS (JSON); cada página dice en su archivo cuál usa."""
import datetime, json, os, re, sys, urllib.request
from zoneinfo import ZoneInfo
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from redes import meta, youtube

CHILE = ZoneInfo("America/Santiago")
VENCE_HORAS = 24
REPO = os.environ.get("GITHUB_REPOSITORY", "biophiliaurbana-sys/publicador")
TOKEN_GH = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
SECRETOS = json.loads(os.environ.get("SECRETOS") or "{}")
PRUEBA = "--prueba" in sys.argv
MARCA = re.compile(r"\n*<!-- estado: (\{.*?\}) -->\s*$", re.S)
TITULO = re.compile(r"^\s*(?:✅\s*|⚠️\s*)?([\w-]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s+(\d{1,2}):(\d{2})\s*$")


def gh(metodo, ruta, datos=None):
    r = urllib.request.Request(f"https://api.github.com/repos/{REPO}{ruta}", method=metodo,
                               data=json.dumps(datos).encode() if datos is not None else None,
                               headers={"Authorization": f"Bearer {TOKEN_GH}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        cuerpo = resp.read()
    return json.loads(cuerpo) if cuerpo else None


def pagina(nombre):
    ruta = os.path.join(AQUI, "paginas", f"{nombre}.json")
    return json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else None


def bajar(asset, carpeta):
    destino = os.path.join(carpeta, asset["name"])
    if not os.path.exists(destino):
        # el repo es público: el adjunto se baja por su link directo (sin clave, que el servidor de archivos rechaza)
        with urllib.request.urlopen(asset["browser_download_url"], timeout=600) as resp, open(destino, "wb") as f:
            f.write(resp.read())
    return destino


def avisar(titulo, texto):
    """Un aviso (issue) en este repo: llega al celular por la app de GitHub."""
    if not PRUEBA:
        gh("POST", "/issues", {"title": titulo, "body": texto})


def publicar_en(red, pag, video, texto, portada, ligero):
    if red in ("facebook", "instagram"):
        token = SECRETOS.get(pag["meta"])
        if not token:
            raise RuntimeError(f"Falta la clave {pag['meta']} en los secretos del repo.")
        if red == "facebook":
            return meta.facebook(token, video, texto, portada)
        return meta.instagram(token, video, texto, ligero)
    if red == "youtube":
        refresh = SECRETOS.get(pag["youtube"])
        if not refresh or not SECRETOS.get("YT_CLIENT_ID"):
            raise RuntimeError(f"Falta conectar YouTube (YT_CLIENT_ID, YT_CLIENT_SECRET y {pag['youtube']}).")
        acceso = youtube.token_de_acceso(SECRETOS["YT_CLIENT_ID"], SECRETOS["YT_CLIENT_SECRET"], refresh)
        titulo = texto.strip().splitlines()[0] if texto.strip() else pag["nombre"]
        return youtube.subir(acceso, video, titulo, texto, pag.get("youtube_privacidad", "public"))
    raise RuntimeError(f"No conozco la red '{red}'.")


def revisar(rel, ahora):
    m = TITULO.match(rel["name"] or "")
    if not m:
        print(f"· '{rel['name']}': el título no sigue el formato '<página> | AAAA-MM-DD HH:MM'; lo salto")
        return
    nombre, dia, hh, mm = m.groups()
    hora = datetime.datetime.fromisoformat(f"{dia}T{int(hh):02d}:{mm}").replace(tzinfo=CHILE)
    pag = pagina(nombre)
    cuerpo = rel["body"] or ""
    e = MARCA.search(cuerpo)
    estado = json.loads(e.group(1)) if e else {}
    texto = MARCA.sub("", cuerpo).strip()
    hechas = set(estado.get("hechas", []))
    print(f"· {nombre} {dia} {hh}:{mm} · ya salió en: {', '.join(sorted(hechas)) or 'nada'}")
    if not pag:
        print(f"  no existe paginas/{nombre}.json; lo salto")
        return
    faltan = [r for r in pag["redes"] if r not in hechas]
    if ahora < hora:
        print(f"  todavía no es la hora (faltan {hora - ahora})")
        return
    if ahora > hora + datetime.timedelta(hours=VENCE_HORAS):
        if not estado.get("vencido"):
            estado["vencido"] = True
            avisar(f"⚠️ {pag['nombre']}: no salió en {', '.join(faltan)}",
                   f"El video de las {hh}:{mm} del {dia} no se pudo subir a {', '.join(faltan)} en 24 horas; ya no lo intento.\n\n"
                   f"Último error: `{estado.get('error', 'sin detalle')}`\n\n{rel['html_url']}")
            guardar(rel, texto, estado, nombre_final=f"⚠️ {rel['name']}")
        return
    video = next((a for a in rel["assets"] if a["name"].lower().endswith((".mp4", ".mov"))), None)
    if not video:
        print("  no tiene video adjunto")
        return
    if PRUEBA:
        print(f"  (prueba) ahora se publicaría en: {', '.join(faltan)}")
        return
    carpeta = os.path.join(AQUI, "bajados", str(rel["id"]))
    os.makedirs(carpeta, exist_ok=True)
    archivo = bajar(video, carpeta)
    portada = next((bajar(a, carpeta) for a in rel["assets"] if a["name"].lower() == "portada.jpg"), None)
    for red in faltan:
        try:
            ident = publicar_en(red, pag, archivo, texto, portada, ligero=estado.get("intentos", 0) > 0)
            hechas.add(red)
            print(f"  ✅ {red}: publicado ({ident})")
        except Exception as ex:
            estado["error"] = f"{red}: {' '.join(str(ex).split())[:300]}"
            print(f"  ⏳ {red}: {estado['error']}")
        estado["hechas"] = sorted(hechas)
        guardar(rel, texto, estado)   # se guarda red por red: si algo se corta, lo que ya salió no se repite
    if set(pag["redes"]) <= hechas:
        guardar(rel, texto, estado, nombre_final=f"✅ {rel['name']}", listo=True)
    else:
        estado["intentos"] = estado.get("intentos", 0) + 1
        if estado["intentos"] == 3:
            avisar(f"⏳ {pag['nombre']}: problemas para subir el video de las {hh}:{mm}",
                   f"Lo sigo intentando solo cada hora; no tienes que hacer nada.\n\nError: `{estado.get('error')}`\n\n{rel['html_url']}")
        guardar(rel, texto, estado)


def guardar(rel, texto, estado, nombre_final=None, listo=False):
    datos = {"body": f"{texto}\n\n<!-- estado: {json.dumps(estado, ensure_ascii=False)} -->"}
    if nombre_final:
        datos["name"] = nombre_final
    if listo or nombre_final:
        datos["prerelease"] = False   # sale de la cola
    rel.update(gh("PATCH", f"/releases/{rel['id']}", datos))


def main():
    ahora = datetime.datetime.now(CHILE)
    print(f"Hora de Chile: {ahora:%Y-%m-%d %H:%M}")
    cola = [r for r in gh("GET", "/releases?per_page=100") if r["prerelease"] and not r["draft"]]
    if not cola:
        print("La cola está vacía.")
    for rel in sorted(cola, key=lambda r: r["name"] or ""):
        revisar(rel, ahora)
    if PRUEBA:
        for nombre in sorted(f[:-5] for f in os.listdir(os.path.join(AQUI, "paginas")) if f.endswith(".json")):
            pag = pagina(nombre)
            token = SECRETOS.get(pag.get("meta", ""))
            if token and {"facebook", "instagram"} & set(pag["redes"]):
                try:
                    yo = meta.cuenta(token)
                    ig = (yo.get("instagram_business_account") or {}).get("username", "sin Instagram")
                    print(f"clave de {nombre}: OK · Facebook '{yo['name']}' · Instagram @{ig}")
                except Exception as ex:
                    print(f"clave de {nombre}: NO funciona ({ex})")
            elif {"facebook", "instagram"} & set(pag["redes"]):
                print(f"clave de {nombre}: falta el secreto {pag.get('meta')}")


if __name__ == "__main__":
    main()
