"""Sprint 1 launch-closure targeted tests: /upload hardening, export whitelist, admin-seed safety."""
import base64
import io
import os
import sys

import requests

API = os.environ.get("TEST_API_URL")
if not API:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                API = line.split("=", 1)[1].strip().strip('"')
API = API.rstrip("/")
ADMIN_EMAIL = "admin@ariadni.id"
ADMIN_PASSWORD = "Ariadni@2026"

PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)
JPEG_MIN = b"\xff\xd8\xff\xe0" + b"\x00" * 64  # valid JPEG magic bytes

results = []


def check(name, cond, extra=""):
    results.append((name, cond, extra))
    print(("PASS" if cond else "FAIL"), "-", name, extra)


def login():
    r = requests.post(f"{API}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def up(token, filename, data, content_type):
    return requests.post(
        f"{API}/api/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, io.BytesIO(data), content_type)},
        timeout=60,
    )


def main():
    token = login()

    # 1. Valid PNG
    r = up(token, "avatar.png", PNG_1x1, "image/png")
    check("valid PNG upload -> 200 with url", r.status_code == 200 and "url" in r.json(), f"({r.status_code})")

    # 1b. Existing normal flow: valid JPG
    r = up(token, "logo.jpg", JPEG_MIN, "image/jpeg")
    check("valid JPG upload -> 200", r.status_code == 200, f"({r.status_code})")

    # 2. Oversized image (6 MB)
    big = PNG_1x1 + b"\x00" * (6 * 1024 * 1024)
    r = up(token, "big.png", big, "image/png")
    check("oversized upload -> 413", r.status_code == 413, f"({r.status_code})")

    # 3. Invalid extension
    r = up(token, "notes.txt", b"hello world", "text/plain")
    check("invalid extension -> 400", r.status_code == 400, f"({r.status_code})")

    # 4. Invalid MIME (png ext but text/plain content type)
    r = up(token, "avatar.png", PNG_1x1, "text/plain")
    check("invalid MIME -> 400", r.status_code == 400, f"({r.status_code})")

    # 5. Non-image payload with image extension + image MIME (magic-byte sniff rejects)
    r = up(token, "fake.png", b"this is definitely not an image payload", "image/png")
    check("non-image payload -> 400", r.status_code == 400, f"({r.status_code})")

    # 5b. Extension/content mismatch (png bytes uploaded as .gif)
    r = up(token, "mismatch.gif", PNG_1x1, "image/gif")
    check("content/extension mismatch -> 400", r.status_code == 400, f"({r.status_code})")

    # 6. Unauthenticated upload rejected
    r = requests.post(f"{API}/api/upload", files={"file": ("a.png", io.BytesIO(PNG_1x1), "image/png")}, timeout=30)
    check("unauthenticated upload -> 401/403", r.status_code in (401, 403), f"({r.status_code})")

    # ---- Task 4: export whitelist ----
    r = requests.get(f"{API}/api/account/export", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    check("export -> 200", r.status_code == 200, f"({r.status_code})")
    user = r.json().get("user", {})
    banned = ["password_hash", "google_id", "auth_provider", "refresh", "sessions", "_id"]
    present_banned = [k for k in banned if k in user]
    check("export user has NO sensitive/internal fields", not present_banned, f"leaked={present_banned}")
    allowed = {"id", "email", "name", "created_at", "language", "locale", "timezone", "account_type", "email_verified"}
    extra = [k for k in user if k not in allowed]
    check("export user only whitelisted fields", not extra, f"unexpected={extra}")
    check("export still returns cards+leads keys", "cards" in r.json() and "leads" in r.json())

    # ---- Task 3: no unsafe fallback admin ----
    r = requests.post(f"{API}/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}, timeout=30)
    check("fallback admin admin@example.com/admin123 CANNOT log in", r.status_code >= 400, f"({r.status_code})")
    r = requests.post(f"{API}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    check("configured admin (env) CAN log in", r.status_code == 200, f"({r.status_code})")

    failed = [n for n, c, _ in results if not c]
    print("\n==== SUMMARY ====")
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
