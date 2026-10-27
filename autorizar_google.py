"""AUTORIZAR GOOGLE · se corre UNA vez en tu PC para sacar el "refresh token" de tu cuenta de Google.
  python autorizar_google.py            → Drive + Sheets (para la cola)
  python autorizar_google.py --youtube  → YouTube (una vez por canal)
Busca solo el archivo client_secret_....json que bajaste de Google Cloud (déjalo en la misma carpeta).
También se puede: python autorizar_google.py <CLIENT_ID> <CLIENT_SECRET> [--youtube]
Se abre el navegador, eliges la cuenta (o el canal) y aceptas. Al final se muestra el refresh token:
cópialo como secreto en GitHub (GOOGLE_REFRESH, o YT_<PÁGINA> para un canal). No lo compartas con nadie."""
import glob, http.server, json, os, sys, urllib.parse, urllib.request, webbrowser

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) >= 2:
    CLIENTE, SECRETO = args[0], args[1]
else:
    carpetas = [os.getcwd(), os.path.dirname(os.path.abspath(__file__)), os.path.expanduser("~/Downloads"),
                os.path.expanduser("~/Descargas")]
    # el de esta carpeta gana; si no hay, el más nuevo de Descargas
    archivos = next((sorted(glob.glob(os.path.join(c, "client_secret*.json")), key=os.path.getmtime)
                     for c in carpetas if glob.glob(os.path.join(c, "client_secret*.json"))), [])
    if not archivos:
        sys.exit("No encuentro el archivo client_secret_....json. Déjalo en la misma carpeta que este script.\n" + __doc__)
    datos_cliente = json.load(open(archivos[-1], encoding="utf-8"))
    datos_cliente = datos_cliente.get("installed") or datos_cliente.get("web") or {}
    CLIENTE, SECRETO = datos_cliente.get("client_id"), datos_cliente.get("client_secret")
    if not (CLIENTE and SECRETO):
        sys.exit(f"El archivo {archivos[-1]} no tiene client_id/client_secret.")
    print("Usando", archivos[-1])
PUERTO = 8765
REDIRECT = f"http://localhost:{PUERTO}"
ALCANCES = (["https://www.googleapis.com/auth/youtube.upload"] if "--youtube" in sys.argv else
            ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"])
codigo = {}


class Recibir(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" not in q and "error" not in q:   # el navegador a veces pide otras cosas (favicon, etc.)
            self.send_response(204)
            self.end_headers()
            return
        codigo["valor"] = (q.get("code") or [None])[0]
        codigo["error"] = (q.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>Listo. Ya puedes cerrar esta pestaña y volver a la terminal.</h2>".encode())

    def log_message(self, *a):
        pass


url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": CLIENTE, "redirect_uri": REDIRECT, "response_type": "code", "scope": " ".join(ALCANCES),
    "access_type": "offline", "prompt": "consent"})
print("Abriendo el navegador… si no se abre, copia este link:\n", url)
webbrowser.open(url)
servidor = http.server.HTTPServer(("localhost", PUERTO), Recibir)
servidor.timeout = 600   # 10 minutos para aceptar en el navegador
servidor.handle_timeout = lambda: codigo.setdefault("valor", None)
while "valor" not in codigo:   # el navegador puede pedir otras cosas antes de volver con el permiso
    servidor.handle_request()
if not codigo.get("valor"):
    sys.exit(f"Google no devolvió el permiso ({codigo.get('error') or 'se acabó el tiempo'}). Vuelve a intentarlo.")
datos = urllib.parse.urlencode({"code": codigo["valor"], "client_id": CLIENTE, "client_secret": SECRETO,
                                "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
r = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=datos)))
if not r.get("refresh_token"):
    sys.exit(f"Google no entregó el refresh token: {r}")
print("\nGuarda estos secretos en GitHub (no los compartas con nadie). Van juntos: si cambias uno, cambia los tres.\n")
if "--youtube" in sys.argv:
    print("YT_<PÁGINA> =", r["refresh_token"])
    print("\n(Si este cliente es de OTRO proyecto que el de Drive, guarda también, una sola vez:)")
    print("YT_CLIENT_ID =", CLIENTE)
    print("\nYT_CLIENT_SECRET =", SECRETO)
else:
    print("GOOGLE_CLIENT_ID =", CLIENTE)
    print("\nGOOGLE_CLIENT_SECRET =", SECRETO)
    print("\nGOOGLE_REFRESH =", r["refresh_token"])
