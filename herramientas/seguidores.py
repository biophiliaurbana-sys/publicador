"""Solo lectura: muestra seguidores de cada página de Facebook y su Instagram.
Nunca imprime las llaves."""
import json, os, urllib.request, urllib.parse

NOMBRES = ["META_ENTRENANDO_MENTES", "META_BUSCADORES", "META_BIOPHILIA", "META_PAGE_TOKEN"]
sec = json.loads(os.environ.get("SECRETOS", "{}"))
for n in NOMBRES:
    tok = sec.get(n)
    if not tok:
        print(f"{n}: no existe en este repo")
        continue
    campos = "name,fan_count,followers_count,instagram_business_account{username,followers_count,media_count}"
    url = "https://graph.facebook.com/v21.0/me?" + urllib.parse.urlencode({"fields": campos, "access_token": tok})
    try:
        d = json.load(urllib.request.urlopen(url, timeout=30))
        ig = d.get("instagram_business_account") or {}
        print(f"{n}: FB '{d.get('name')}' seguidores={d.get('followers_count')} me_gusta={d.get('fan_count')} | IG @{ig.get('username')} seguidores={ig.get('followers_count')} publicaciones={ig.get('media_count')}")
    except Exception as e:
        cuerpo = getattr(e, "read", lambda: b"")().decode()[:300]
        print(f"{n}: error {type(e).__name__} {cuerpo.replace(tok, '***')}")
