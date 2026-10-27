"""PUBLICADOR · revisa la cola y sube a su hora lo que toca (lo corre .github/workflows/publicar.yml cada hora).
  python publicar.py            → publica lo que ya le tocó
  python publicar.py --prueba   → muestra la cola y revisa las claves, sin publicar nada

La cola es una planilla de Google tuya (variable HOJA_COLA), pestaña "cola", una fila por video:
  A página · B fecha · C hora (de Chile) · D video (link de Drive) · E texto · F portada (link, opcional)
  G estado y H detalle → los escribe el sistema; no los toques.
<página> es un archivo de paginas/. Los videos quedan privados en tu Drive: nadie más los ve.
Además revisa los *releases* de los repos privados de marca (repos.json, secreto LLAVE_REPOS): las páginas que
arman su contenido solas dejan ahí su video, sin pasar por Drive (ver redes/github.py).
Cada red se marca apenas sale, así un reintento nunca la repite. Si una red falla, las otras salen igual y la
que falló se reintenta cada hora con una versión más liviana; a la 3.ª vuelta llega un aviso y a las 24 h se deja.
Las claves vienen todas juntas en la variable SECRETOS (JSON); cada página dice en su archivo cuál usa."""
import datetime, json, os, re, sys, urllib.request
from zoneinfo import ZoneInfo
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from redes import google, meta, youtube
from redes import github as gh_repos

CHILE = ZoneInfo("America/Santiago")
VENCE_HORAS = 24
REPO = os.environ.get("GITHUB_REPOSITORY", "biophiliaurbana-sys/publicador")
TOKEN_GH = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
SECRETOS = {k: v.strip() if isinstance(v, str) else v for k, v in json.loads(os.environ.get("SECRETOS") or "{}").items()}  # sin espacios pegados por error
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


class Fila:
    """Un video de la planilla (cola hecha a mano: Biophilia, tiendas…). n = número de fila (la 1 son los títulos)."""
    def __init__(self, token, n, fila):
        fila = (fila + [""] * 8)[:8]
        self.token, self.n = token, n
        self.nombre, self.fecha, self.hora, self.video, self.texto, self.portada, self.resumen, self.detalle = fila
        self.etiqueta = f"fila {n}"
        self.vacia = not self.nombre.strip() or not self.video.strip()
        self.estado = json.loads(self.detalle) if self.detalle.strip().startswith("{") else {}

    def guardar(self, resumen):
        nuevo = json.dumps(self.estado, ensure_ascii=False)
        if (resumen, nuevo) != (self.resumen, self.detalle or "{}"):   # solo si cambió algo
            google.escribir(self.token, HOJA, f"{COLA}!G{self.n}:H{self.n}", [[resumen, nuevo]])
            self.resumen, self.detalle = resumen, nuevo

    def bajar(self, carpeta):
        archivo = os.path.join(carpeta, "video.mp4")
        if not os.path.exists(archivo):
            google.bajar(self.token, google.id_drive(self.video), archivo)
        portada = None
        if self.portada.strip():
            portada = google.bajar(self.token, google.id_drive(self.portada), os.path.join(carpeta, "portada.jpg"))
        return archivo, portada

    def limpiar(self):
        # ya salió en todas sus redes: el video (y su portada) van a la papelera de Drive para no llenarlo (Danko 27-oct)
        for link in (self.video, self.portada):
            if link.strip():
                google.a_papelera(self.token, google.id_drive(link))


class Lanzamiento:
    """Un video guardado como release en el repo privado de una marca (contenido que se arma solo; sin Drive)."""
    def __init__(self, llave, repo, rel):
        self.llave, self.repo, self.id = llave, repo, rel["id"]
        self.marca, self.texto = gh_repos.leer_marca(rel.get("body"))
        self.vacia = self.marca is None or rel.get("draft")
        m = self.marca or {}
        self.nombre, self.fecha, self.hora = m.get("pagina", ""), m.get("fecha", ""), m.get("hora", "")
        self.estado = m.get("estado") or {}
        self.resumen = rel.get("name") or ""
        self.titulo = m.get("titulo") or f"{self.nombre} · {self.fecha} {self.hora}"
        self.etiqueta = f"{repo.split('/')[-1]} {rel.get('tag_name')}"
        self.archivos = rel.get("assets") or []
        self.cuerpo = rel.get("body") or ""

    def guardar(self, resumen):
        nombre = f"{resumen} · {self.titulo}"[:250]
        cuerpo = gh_repos.poner_marca(self.texto, {**self.marca, "estado": self.estado})
        if (nombre, cuerpo) != (self.resumen, self.cuerpo):   # solo si cambió algo
            gh_repos.editar(self.llave, self.repo, self.id, name=nombre, body=cuerpo)
            self.resumen, self.cuerpo = nombre, cuerpo

    def _archivo(self, *extensiones):
        return next((a for a in self.archivos if a["name"].lower().endswith(extensiones)), None)

    def bajar(self, carpeta):
        video = self._archivo(".mp4", ".mov")
        if not video:
            raise RuntimeError("el release no tiene video (.mp4)")
        archivo = os.path.join(carpeta, "video.mp4")
        if not os.path.exists(archivo):
            gh_repos.bajar(self.llave, self.repo, video["id"], archivo)
        portada = self._archivo(".jpg", ".jpeg", ".png")
        if portada:
            portada = gh_repos.bajar(self.llave, self.repo, portada["id"], os.path.join(carpeta, "portada.jpg"))
        return archivo, portada

    def limpiar(self):
        # ya salió: se borra el video adjunto para no llenar GitHub (el release queda como registro, con su texto)
        for a in self.archivos:
            gh_repos.borrar_archivo(self.llave, self.repo, a["id"])


def revisar(item, ahora):
    """Un video de la cola (Fila o Lanzamiento): lo publica si ya le tocó y anota cómo le fue."""
    if item.vacia or item.estado.get("listo") or item.estado.get("vencido"):
        return
    if item.resumen.strip().startswith("⛔"):   # frenado (a mano o con "frenar" en el aviso): no se publica
        print(f"· {item.etiqueta}: frenado, no se publica")
        return
    estado = item.estado
    guardar = (lambda resumen: None) if PRUEBA else item.guardar

    pag = pagina(item.nombre)
    try:
        momento = cuando(item.fecha, item.hora)
    except ValueError as e:
        print(f"· {item.etiqueta}: {e}")
        guardar(f"⚠️ {e}")
        return
    if not pag:
        print(f"· {item.etiqueta}: no existe la página '{item.nombre}'")
        guardar(f"⚠️ no existe la página '{item.nombre}'")
        return
    hechas = set(estado.get("hechas", []))
    faltan = [r for r in pag["redes"] if r not in hechas]
    print(f"· {item.etiqueta}: {item.nombre} {momento:%d/%m %H:%M} · falta: {', '.join(faltan)}")
    if ahora < momento:
        guardar(f"🕒 en cola para el {momento:%d/%m} a las {momento:%H:%M}")
        return
    if ahora > momento + datetime.timedelta(hours=VENCE_HORAS):
        estado["vencido"] = True
        avisar(f"⚠️ {pag['nombre']}: no salió en {', '.join(faltan)}",
               f"El video ({item.etiqueta}, {momento:%d/%m %H:%M}) no se pudo subir a {', '.join(faltan)} en 24 horas; "
               f"ya no lo intento.\n\nÚltimo error: `{estado.get('error', 'sin detalle')}`")
        guardar(f"⚠️ no salió en {', '.join(faltan)}" + (f" (sí en {', '.join(sorted(hechas))})" if hechas else ""))
        return
    if PRUEBA:
        print(f"  (prueba) ahora se publicaría en: {', '.join(faltan)}")
        return
    carpeta = os.path.join(AQUI, "bajados", re.sub(r"[^\w.-]", "_", item.etiqueta))
    os.makedirs(carpeta, exist_ok=True)
    archivo, portada_archivo = item.bajar(carpeta)
    for red in faltan:
        try:
            ident = publicar_en(red, pag, archivo, item.texto, portada_archivo, ligero=estado.get("intentos", 0) > 0)
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
        try:
            item.limpiar()
        except Exception as ex:
            print(f"  (no se pudo borrar el video ya publicado: {' '.join(str(ex).split())[:150]})")
    else:
        estado["intentos"] = estado.get("intentos", 0) + 1
        if estado["intentos"] == 3:
            avisar(f"⏳ {pag['nombre']}: problemas para subir un video ({item.etiqueta})",
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


def repos_de_marca():
    try:
        return json.load(open(os.path.join(AQUI, "repos.json"), encoding="utf-8")).get("repos", [])
    except OSError:
        return []


def main():
    ahora = datetime.datetime.now(CHILE)
    print(f"Hora de Chile: {ahora:%Y-%m-%d %H:%M}")
    if PRUEBA:
        probar_claves()
    items = []
    if HOJA:   # 1) la planilla (videos hechos a mano, en Drive)
        token = acceso_google()
        items += [Fila(token, i, f) for i, f in enumerate(google.leer(token, HOJA, f"{COLA}!A2:H"), start=2)]
    else:
        print("(sin planilla: falta la variable HOJA_COLA)")
    llave = SECRETOS.get("LLAVE_REPOS")
    for repo in repos_de_marca():   # 2) los releases de los repos privados de marca (videos que se arman solos)
        if not llave:
            print(f"{repo}: falta el secreto LLAVE_REPOS (llave de GitHub para leer los repos privados)")
            break
        try:
            items += [Lanzamiento(llave, repo, r) for r in gh_repos.releases(llave, repo)]
            if PRUEBA:
                print(f"{repo}: llave de GitHub OK")
        except Exception as ex:
            print(f"{repo}: no pude leer sus videos ({ex})")
    for item in items:
        try:
            revisar(item, ahora)
        except Exception as ex:   # un video malo no frena a los demás
            print(f"· {item.etiqueta}: error inesperado: {ex}")


if __name__ == "__main__":
    main()
