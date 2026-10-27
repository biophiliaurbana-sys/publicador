"""AUTORIZAR GOOGLE · se corre UNA vez en tu PC para sacar el "refresh token" de tu cuenta de Google.
  python autorizar_google.py <CLIENT_ID> <CLIENT_SECRET>            → Drive + Sheets (para la cola)
  python autorizar_google.py <CLIENT_ID> <CLIENT_SECRET> --youtube  → YouTube (una vez por canal)
Se abre el navegador, eliges la cuenta (o el canal) y aceptas. Al final se muestra el refresh token:
cópialo como secreto en GitHub (GOOGLE_REFRESH, o YT_<PÁGINA> para un canal). No lo compartas con nadie."""
import http.server, json, sys, urllib.parse, urllib.request, webbrowser

if len(sys.argv) < 3:
    sys.exit(__doc__)
CLIENTE, SECRETO = sys.argv[1], sys.argv[2]
PUERTO = 8765
REDIRECT = f"http://localhost:{PUERTO}"
ALCANCES = (["https://www.googleapis.com/auth/youtube.upload"] if "--youtube" in sys.argv else
            ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"])
codigo = {}


class Recibir(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        codigo["valor"] = (q.get("code") or [None])[0]
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
http.server.HTTPServer(("localhost", PUERTO), Recibir).handle_request()
if not codigo.get("valor"):
    sys.exit("Google no devolvió el permiso. Vuelve a intentarlo.")
datos = urllib.parse.urlencode({"code": codigo["valor"], "client_id": CLIENTE, "client_secret": SECRETO,
                                "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
r = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=datos)))
print("\nTu refresh token (guárdalo como secreto en GitHub):\n")
print(r.get("refresh_token") or f"Google no lo entregó: {r}")
