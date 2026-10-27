# Instrucciones para el agente (DeepSeek Harness, Antigravity, Claude Code u otro)

Este repo publica videos en Facebook, Instagram y YouTube a su hora. Lee README.md.

- "Sube el video X a la página Y a tal hora" → `python encolar.py --pagina Y --video X --hora "AAAA-MM-DD HH:MM" --texto "..."`.
  La hora es de Chile. Las páginas válidas son los archivos de `paginas/` (sin `.json`).
- "¿Qué hay en la cola?" → `gh release list --repo biophiliaurbana-sys/publicador` (los *Pre-release* esperan su hora).
- "Saca/cambia un video de la cola" → borra o edita ese release (`gh release delete <tag>` / `gh release edit <tag>`),
  solo si todavía es *Pre-release*. Nunca toques los que tienen ✅ (ya publicados).
- "¿Por qué no salió?" → revisa los avisos (issues) y la última corrida de *Actions → Publicar*.

Reglas:
- Nunca publiques al instante: todo va a la cola con hora. Nunca escribas claves en archivos ni en mensajes.
- No borres nada definitivamente fuera de la cola; pregunta antes.
- Pide confirmación antes de encolar si la página, la hora o el texto no están claros.
