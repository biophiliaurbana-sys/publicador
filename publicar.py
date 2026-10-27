"""PUBLICADOR · revisa la cola y sube a su hora lo que toca (lo corre .github/workflows/publicar.yml cada hora).
  python publicar.py            → publica lo que ya le tocó
  python publicar.py --prueba   → muestra la cola y revisa las claves, sin publicar nada

La cola es una planilla de Google tuya (variable HOJA_COLA), pestaña "cola", una fila por video:
  A página · B fecha · C hora (de Chile) · D video (link de Drive) · E texto · F portada (link, opcional)
  G estado y H detalle → los escribe el sistema; no los toques.
<página> es un archivo de paginas/. Los videos quedan privados en tu Drive: nadie más los ve.
Cada red se marca apenas sale, así un reintento nunca la repite. Si una red falla, las otras salen igual y la
que falló se reintenta cada hora con una versión más liviana; a la 3.ª vuelta llega un aviso y a las 24 h se deja.
Las claves vienen todas juntas en la variable SECRETOS (JSON); cada página dice en su archivo cuál usa."""
import datetime, json, os, re, sys, urllib.request
from zoneinfo import ZoneInfo
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from redes import google, meta, youtube

CHILE = ZoneInfo("America/Santiago")
VENCE_HORAS = 24
REPO = os.environ.get("GITHUB_REPOSITORY", "biophiliaurbana-sys/publicador")
TOKEN_GH = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
SECRETOS = json.loads(os.environ.get("SECRETOS") or "{}")
HOJA = os.environ.get("HOJA_COLA", "").strip()
PRUEBA = "--prueba" in sys.argv
COLA = "cola"


def gh(metodo, ruta, datos=None):
    r = urllib.request.Request(f"https://api.github.com/repos/{REPO}{ruta}", method=metodo,
                               data=json.dumps(datos).encode() if datos is not None else None,
                               headers={"Authorization": f"Bearer {TOKEN_GH}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read() or b"null")


def avisar(titulo, texto):
    """Un aviso (issue) en este repo: llega al celular por la app de GitHub."""
    if not PRUEBA:
        gh("POST", "/issues", {"title": titulo, "body": texto})


def pagina(nombre):
    ruta = os.path.join(AQUI, "paginas", f"{nombre.strip().lower()}.json")
    return json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else None


def cuando(fecha, hora):
    """Fecha y hora de la planilla → momento en Chile. Acepta 2026-10-28, 28-10-2026, 28/10/2026 o 28/10."""
    f = fecha.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", f)
    if m:
        a, me, d = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", f)
        if not m:
            raise ValueError(f"no entiendo la fecha '{fecha}'")
        d, me = int(m.group(1)), int(m.group(2))
        a = int(m.group(3) or datetime.date.today().year)
        a += 2000 if a < 100 else 0
    h = re.match(r"(\d{1,2})[:.](\d{2})", hora.strip())
    if not h:
        raise ValueError(f"no entiendo la hora '{hora}'")
    return datetime.datetime(a, me, d, int(h.group(1)), int(h.group(2)), tzinfo=CHILE)


def acceso_google(secreto="GOOGLE_REFRESH"):
    if not (SECRETOS.get("GOOGLE_CLIENT_ID") and SECRETOS.get(secreto)):
        raise RuntimeError(f"Falta conectar Google (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y {secreto}).")
    return google.acceso(SECRETOS["GOOGLE_CLIENT_ID"], SECRETOS["GOOGLE_CLIENT_SECRET"], SECRETOS[secreto])


def publicar_en(red, pag, video, texto, portada, ligero):
    if red in ("facebook", "instagram"):
        token = SECRETOS.get(pag["meta"])
        if not token:
            raise RuntimeError(f"Falta la clave {pag['meta']} en los secretos del repo.")
        if red == "facebook":
            return meta.facebook(token, video, texto, portada)
        return meta.instagram(token, video, texto, ligero)
    if red == "youtube":
        titulo = texto.strip().splitlines()[0] if texto.strip() else pag["nombre"]
        return youtube.subir(acceso_google(pag["youtube"]), video, titulo, texto, pag.get("youtube_privacidad", "public"))
    raise RuntimeError(f"No conozco la red '{red}'.")


def revisar(token, n, fila, ahora):
    """n = número de fila en la planilla (la 1 son los títulos)."""
    fila = (fila + [""] * 8)[:8]
    nombre, fecha, hora, video, texto, portada, resumen_actual, detalle = fila
    if not nombre.strip() or not video.strip():
        return
    estado = json.loads(detalle) if detalle.strip().startswith("{") else {}
    if estado.get("listo") or estado.get("vencido"):
        return

    def guardar(resumen):
        nuevo = json.dumps(estado, ensure_ascii=False)
        if not PRUEBA and (resumen, nuevo) != (resumen_actual, detalle or "{}"):   # solo si cambió algo

            google.escribir(token, HOJA, f"{COLA}!G{n}:H{n}", [[resumen, nuevo]])

    pag = pagina(nombre)
    try:
        momento = cuando(fecha, hora)
    except ValueError as e:
        print(f"· fila {n}: {e}")
        guardar(f"⚠️ {e}")
        return
    if not pag:
        print(f"· fila {n}: no existe la página '{nombre}'")
        guardar(f"⚠️ no existe la página '{nombre}'")
        return
    hechas = set(estado.get("hechas", []))
    faltan = [r for r in pag["redes"] if r not in hechas]
    print(f"· fila {n}: {nombre} {momento:%d/%m %H:%M} · falta: {', '.join(faltan)}")
    if ahora < momento:
        guardar(f"🕒 en cola para el {momento:%d/%m} a las {momento:%H:%M}")
        return
    if ahora > momento + datetime.timedelta(hours=VENCE_HORAS):
        estado["vencido"] = True
        avisar(f"⚠️ {pag['nombre']}: no salió en {', '.join(faltan)}",
               f"El video de la fila {n} ({momento:%d/%m %H:%M}) no se pudo subir a {', '.join(faltan)} en 24 horas; "
               f"ya no lo intento.\n\nÚltimo error: `{estado.get('error', 'sin detalle')}`")
        guardar(f"⚠️ no salió en {', '.join(faltan)}" + (f" (sí en {', '.join(sorted(hechas))})" if hechas else ""))
        return
    if PRUEBA:
        print(f"  (prueba) ahora se publicaría en: {', '.join(faltan)}")
        return
    carpeta = os.path.join(AQUI, "bajados", str(n))
    os.makedirs(carpeta, exist_ok=True)
    archivo = os.path.join(carpeta, "video.mp4")
    if not os.path.exists(archivo):
        google.bajar(token, google.id_drive(video), archivo)
    portada_archivo = None
    if portada.strip():
        portada_archivo = google.bajar(token, google.id_drive(portada), os.path.join(carpeta, "portada.jpg"))
    for red in faltan:
        try:
            ident = publicar_en(red, pag, archivo, texto, portada_archivo, ligero=estado.get("intentos", 0) > 0)
            hechas.add(red)
            print(f"  ✅ {red}: publicado ({ident})")
        except Exception as ex:
            estado["error"] = f"{red}: {' '.join(str(ex).split())[:300]}"
            print(f"  ⏳ {estado['error']}")
        estado["hechas"] = sorted(hechas)
        guardar("⏳ subiendo…")   # se guarda red por red: si algo se corta, lo que ya salió no se repite
    if set(pag["redes"]) <= hechas:
        estado["listo"] = True
        guardar(f"✅ publicado en {', '.join(pag['redes'])} ({ahora:%d/%m %H:%M})")
    else:
        estado["intentos"] = estado.get("intentos", 0) + 1
        if estado["intentos"] == 3:
            avisar(f"⏳ {pag['nombre']}: problemas para subir el video de la fila {n}",
                   f"Lo sigo intentando solo cada hora; no tienes que hacer nada.\n\nError: `{estado.get('error')}`")
        guardar(f"⏳ reintento cada hora ({estado.get('error', '')[:80]})"
                + (f" · ya salió en {', '.join(sorted(hechas))}" if hechas else ""))


def probar_claves():
    for nombre in sorted(f[:-5] for f in os.listdir(os.path.join(AQUI, "paginas")) if f.endswith(".json")):
        pag = pagina(nombre)
        if {"facebook", "instagram"} & set(pag["redes"]):
            token = SECRETOS.get(pag.get("meta", ""))
            if not token:
                print(f"{nombre}: falta el secreto {pag.get('meta')}")
                continue
            try:
                yo = meta.cuenta(token)
                ig = (yo.get("instagram_business_account") or {}).get("username", "sin Instagram")
                print(f"{nombre}: clave de Meta OK · Facebook '{yo['name']}' · Instagram @{ig}")
            except Exception as ex:
                print(f"{nombre}: la clave de Meta NO funciona ({ex})")
        if "youtube" in pag["redes"]:
            try:
                acceso_google(pag["youtube"])
                print(f"{nombre}: YouTube OK")
            except Exception as ex:
                print(f"{nombre}: YouTube NO funciona ({ex})")


def main():
    ahora = datetime.datetime.now(CHILE)
    print(f"Hora de Chile: {ahora:%Y-%m-%d %H:%M}")
    if PRUEBA:
        probar_claves()
    if not HOJA:
        sys.exit("Falta la variable HOJA_COLA (el ID de la planilla de la cola).")
    token = acceso_google()
    filas = google.leer(token, HOJA, f"{COLA}!A2:H")
    for i, fila in enumerate(filas, start=2):
        try:
            revisar(token, i, fila, ahora)
        except Exception as ex:   # una fila mala no frena a las demás
            print(f"· fila {i}: error inesperado: {ex}")


if __name__ == "__main__":
    main()
