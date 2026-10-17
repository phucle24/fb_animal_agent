"""
Google Drive OAuth Helper
Helps generate a fresh GOOGLE_REFRESH_TOKEN for fb_animal_agent.
"""

import http.server
import os
import socketserver
import sys
import urllib.parse
import webbrowser
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

PORT = 8080
REDIRECT_URI = f"http://localhost:{PORT}/"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <html>
            <body style="font-family:sans-serif; text-align:center; padding:50px; background:#f0f9ff;">
                <h1 style="color:#0369a1;">Xác thực Google Drive thành công!</h1>
                <p style="font-size:18px; color:#334155;">Token đã được ghi nhận. Bạn có thể đóng tab này và quay lại terminal.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        elif "error" in params:
            error = params.get("error", ["Unknown error"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h1>Lỗi xác thực: {error}</h1>".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Quiet down HTTP request logs
        return


def get_auth_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_code_for_token(code: str) -> dict:
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }
    resp = requests.post(url, data=data, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Lỗi đổi mã token ({resp.status_code}): {resp.text}")
    return resp.json()


def update_env_file(refresh_token: str, env_path: Path):
    if not env_path.exists():
        return
    content = env_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("GOOGLE_REFRESH_TOKEN="):
            new_lines.append(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Đã cập nhật GOOGLE_REFRESH_TOKEN vào {env_path}")


if __name__ == "__main__":
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("Lỗi: Chưa cấu hình GOOGLE_CLIENT_ID hoặc GOOGLE_CLIENT_SECRET trong .env")
        sys.exit(1)

    auth_url = get_auth_url()
    print("=" * 60)
    print("XÁC THỰC GOOGLE DRIVE OAUTH CHO FB_ANIMAL_AGENT")
    print("=" * 60)
    print("\n1. Mở liên kết sau trong trình duyệt để cấp quyền:")
    print(auth_url)
    print("\n2. Đang chờ phản hồi tại http://localhost:8080/ ...")

    # Try to open in browser automatically
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    with socketserver.TCPServer(("", PORT), OAuthCallbackHandler) as httpd:
        httpd.timeout = 180  # 3 minutes timeout
        while not OAuthCallbackHandler.auth_code:
            httpd.handle_request()

    code = OAuthCallbackHandler.auth_code
    if not code:
        print("Không nhận được authorization code hoặc đã hết thời gian chờ.")
        sys.exit(1)

    print("\nĐã nhận Authorization Code. Đang đổi lấy Refresh Token...")
    tokens = exchange_code_for_token(code)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("Cảnh báo: Google không trả về refresh_token mới (có thể do prompt chưa force consent).")
        print("Token payload:", tokens)
        sys.exit(1)

    print("\nTHÀNH CÔNG! Refresh token mới:")
    print(refresh_token)

    local_env = BASE_DIR / ".env"
    update_env_file(refresh_token, local_env)
