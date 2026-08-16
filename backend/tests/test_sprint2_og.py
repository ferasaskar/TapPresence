"""Sprint 2 — per-card social/SEO metadata tests.

Proves crawler-visible per-card OG/Twitter metadata at the real shareable URL,
publication rules, safe fallbacks, escaping, PUBLIC_APP_URL canonical, and that
the human SPA + existing public endpoints are unchanged.
"""
import asyncio
import os
import sys
import uuid

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
PUBLIC_APP_URL = os.environ["PUBLIC_APP_URL"].rstrip('"').rstrip("/")

with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL"):
            API = line.split("=", 1)[1].strip().strip('"').rstrip("/")

CRAWLER = {"User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"}
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"}

results = []


def check(name, cond, extra=""):
    results.append((name, cond, extra))
    print(("PASS" if cond else "FAIL"), "-", name, extra)


async def seed():
    c = AsyncIOMotorClient(MONGO_URL)
    db = c[DB_NAME]
    edrina = await db.digital_cards.find_one({"slug": "edrina-cepele"}, {"_id": 0, "workspace_id": 1})
    wsid = edrina["workspace_id"]
    ids = {
        "min": f"og-test-min-{uuid.uuid4().hex[:8]}",
        "esc": f"og-test-esc-{uuid.uuid4().hex[:8]}",
        "draft": f"og-test-draft-{uuid.uuid4().hex[:8]}",
    }
    await db.digital_cards.insert_one({
        "id": str(uuid.uuid4()), "slug": ids["min"], "status": "published", "workspace_id": wsid,
        "identity": {"fullName": "Sam Solo"},  # no job/company/bio/photo -> fallbacks
    })
    await db.digital_cards.insert_one({
        "id": str(uuid.uuid4()), "slug": ids["esc"], "status": "published", "workspace_id": wsid,
        "identity": {"fullName": 'A&B <x> "Q" Zoë محمد', "jobTitle": "R&D <lead>", "company": "Z & Co"},
    })
    await db.digital_cards.insert_one({
        "id": str(uuid.uuid4()), "slug": ids["draft"], "status": "draft", "workspace_id": wsid,
        "identity": {"fullName": "Hidden Draft"},
    })
    return ids


async def teardown(ids):
    c = AsyncIOMotorClient(MONGO_URL)
    db = c[DB_NAME]
    await db.digital_cards.delete_many({"slug": {"$in": list(ids.values())}})


def og(slug, headers=CRAWLER):
    return requests.get(f"{API}/{slug}", headers=headers, timeout=30)


def main():
    ids = asyncio.get_event_loop().run_until_complete(seed())
    try:
        # 1. Published card has crawler-visible per-card OG at the shareable /{slug}
        r = og("edrina-cepele")
        b = r.text
        check("published card /{slug} crawler -> per-card OG",
              r.status_code == 200 and 'property="og:title"' in b and "Edrina Cepele" in b, f"({r.status_code})")

        # 2. Two different cards produce different metadata
        b2 = og("feras-askar").text
        t1 = b[b.find('og:title'):b.find('og:title') + 120]
        t2 = b2[b2.find('og:title'):b2.find('og:title') + 120]
        check("two cards -> different og:title", t1 != t2 and "Feras Askar" in b2, "")

        # 3. Draft card not exposed
        r = og(ids["draft"])
        check("draft card -> not prerendered (SPA/no card OG)",
              "Hidden Draft" not in r.text, f"({r.status_code})")
        r_api = requests.get(f"{API}/api/og/{ids['draft']}", headers=CRAWLER, timeout=30)
        check("draft card /api/og -> 404", r_api.status_code == 404, f"({r_api.status_code})")

        # 4. Missing optional fields -> safe fallback
        bm = og(ids["min"]).text
        check("missing fields -> title is just the name",
              'og:title" content="Sam Solo"' in bm, "")
        check("missing bio -> fallback description present",
              "powered by TapPresence" in bm, "")

        # 5. Missing image -> TapPresence brand fallback
        check("missing photo -> logo512 fallback image",
              f'og:image" content="{PUBLIC_APP_URL}/logo512.png"' in bm, "")

        # 6. Canonical uses PUBLIC_APP_URL (env-derived, not hardcoded)
        check("canonical/og:url uses PUBLIC_APP_URL",
              f'og:url" content="{PUBLIC_APP_URL}/edrina-cepele"' in b
              and f'canonical" href="{PUBLIC_APP_URL}/edrina-cepele"' in b, "")

        # 7. Human browser still gets the SPA (generic index), not per-card OG
        hb = og("edrina-cepele", headers=BROWSER).text
        check("human UA -> SPA index (generic OG, no prerender)",
              "Your Presence. One Tap Away." in hb and "Edrina Cepele" not in hb.split("</head>")[0], "")

        # 8. Escaping / i18n: special chars escaped, no raw injected tags, UTF-8 preserved
        be = og(ids["esc"]).text
        check("escaping: & and <> escaped in og:title",
              "A&amp;B &lt;x&gt;" in be and "&quot;Q&quot;" in be, "")
        check("escaping: no raw <x> tag injected", "<x>" not in be, "")
        check("i18n: arabic/unicode preserved", "Zoë" in be and "محمد" in be, "")

        # 9. Regression: existing public endpoints unchanged
        check("regression: GET /api/cards/edrina-cepele 200",
              requests.get(f"{API}/api/cards/edrina-cepele", timeout=30).status_code == 200)
        check("regression: vcard 200",
              requests.get(f"{API}/api/cards/edrina-cepele/vcard", timeout=30).status_code == 200)
        check("regression: qr 200",
              requests.get(f"{API}/api/cards/edrina-cepele/qr", timeout=30).status_code == 200)
        check("regression: owner wallet still auth-protected (401 logged-out)",
              requests.get(f"{API}/api/cards/edrina-cepele/wallet/google", timeout=30).status_code == 401)
    finally:
        asyncio.get_event_loop().run_until_complete(teardown(ids))

    failed = [n for n, c, _ in results if not c]
    print("\n==== SUMMARY ====")
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
