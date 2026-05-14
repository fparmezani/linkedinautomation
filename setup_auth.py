"""
Rode este script UMA ÚNICA VEZ para autenticar com o LinkedIn.
Ele abrirá o browser, você autoriza o app dotnet-bot,
e os tokens são salvos automaticamente no .env.
"""

import urllib.parse
import http.server
import webbrowser
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI  = "http://localhost:8000/callback"
SCOPES        = "openid profile w_member_social"


def update_env(key: str, value: str):
    """Atualiza uma variável no arquivo .env sem apagar as outras."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = rf"^{re.escape(key)}=.*$"
    replacement = f"{key}={value}"
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def get_authorization_code() -> str:
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={urllib.parse.quote(SCOPES)}"
    )

    code_holder = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if "code=" in self.path:
                code_holder["code"] = self.path.split("code=")[1].split("&")[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<h2>Autorizado! Pode fechar esta aba.</h2>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<h2>Erro: code nao encontrado.</h2>")

        def log_message(self, *args):
            pass

    print(f"\nAbrindo browser para autorizacao do app 'dotnet-bot'...")
    print(f"Se nao abrir automaticamente, acesse:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", 8000), Handler)
    server.handle_request()

    return code_holder.get("code", "")


def exchange_code_for_tokens(code: str) -> dict:
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  REDIRECT_URI,
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    return resp.json()


def get_user_urn(access_token: str) -> str:
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp.raise_for_status()
    data = resp.json()
    # sub = "urn:li:person:XXXXXXXX" ou só o ID
    sub = data.get("sub", "")
    return f"urn:li:person:{sub}" if not sub.startswith("urn:") else sub


def main():
    if not CLIENT_ID or CLIENT_ID == "COLE_SEU_CLIENT_ID_AQUI":
        print("ERRO: Preencha LINKEDIN_CLIENT_ID no arquivo .env antes de rodar.")
        return
    if not CLIENT_SECRET or CLIENT_SECRET == "COLE_SEU_CLIENT_SECRET_AQUI":
        print("ERRO: Preencha LINKEDIN_CLIENT_SECRET no arquivo .env antes de rodar.")
        return

    code = get_authorization_code()
    if not code:
        print("ERRO: Nao foi possivel obter o authorization code.")
        return

    print("Trocando code por tokens...")
    tokens = exchange_code_for_tokens(code)

    access_token  = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    expires_in    = tokens.get("expires_in", 0)

    print("Buscando URN do seu perfil...")
    author_urn = get_user_urn(access_token)

    update_env("LINKEDIN_ACCESS_TOKEN",  access_token)
    update_env("LINKEDIN_REFRESH_TOKEN", refresh_token)
    update_env("LINKEDIN_AUTHOR_URN",    author_urn)

    print("\n[OK] Autenticacao concluida! .env atualizado com sucesso.")
    print(f"  Author URN : {author_urn}")
    print(f"  Token expira em: {expires_in // 3600}h (~{expires_in // 86400} dias)")
    print(f"  Refresh token: valido por 365 dias (renovado automaticamente)\n")


if __name__ == "__main__":
    main()
