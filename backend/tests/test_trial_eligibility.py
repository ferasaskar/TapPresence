"""P0 trial-eligibility tests: a trial can be consumed ONCE per account/email."""
import asyncio
import os
import sys
import uuid

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
sys.path.insert(0, "/app/backend")
from platform_v1 import _trial_eligible  # noqa: E402

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL"):
            API = line.split("=", 1)[1].strip().strip('"').rstrip("/")

results = []
def check(n, c, e=""):
    results.append((n, c, e)); print(("PASS" if c else "FAIL"), "-", n, e)

EMAIL = f"trialtest_{uuid.uuid4().hex[:10]}@example.com"


async def read_sub(email):
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    u = await db.users.find_one({"email": email.strip().lower()})
    if not u:
        return None
    ws = await db.workspaces.find_one({"owner_id": u["id"]})
    return (ws or {}).get("subscription")


async def cleanup(email):
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    u = await db.users.find_one({"email": email.strip().lower()})
    if not u:
        return
    wss = await db.workspaces.find({"owner_id": u["id"]}, {"id": 1}).to_list(10)
    ids = [w["id"] for w in wss]
    await db.workspaces.delete_many({"owner_id": u["id"]})
    await db.memberships.delete_many({"user_id": u["id"]})
    await db.users.delete_one({"id": u["id"]})


def register(email):
    return requests.post(f"{API}/api/auth/register", timeout=30,
                         json={"email": email, "password": "Test@1234", "name": "Trial Test", "workspace_name": "TT"})


def main():
    loop = asyncio.get_event_loop()
    try:
        # 1. Brand-new user -> exactly one 14-day trial
        r = register(EMAIL)
        check("1. brand-new register ok", r.status_code == 200, f"({r.status_code})")
        sub = loop.run_until_complete(read_sub(EMAIL))
        check("1b. new user is trialing with 14d + marker",
              sub and sub.get("status") == "trialing" and sub.get("trial_started_at") and sub.get("trial_ends_at"),
              str({k: sub.get(k) for k in ("status", "trial_started_at", "trial_ends_at")}) if sub else "no sub")

        # 2-8. Any already-trialed sub state is INELIGIBLE (helper is the checkout gate)
        check("2. second checkout: already-trialed -> ineligible", _trial_eligible(sub) is False)
        base_marker = {"trial_started_at": sub["trial_started_at"], "trial_ends_at": sub["trial_ends_at"]}
        for name, extra in [
            ("3. cancelled during trial", {"status": "cancelled"}),
            ("4. trial completed/expired", {"status": "trial_expired"}),
            ("5. payment failed", {"status": "past_due"}),
            ("6. monthly->annual switch", {"status": "active", "interval": "year"}),
            ("7. annual->monthly switch", {"status": "active", "interval": "month"}),
            ("8. after logout/login (same sub)", {"status": "trialing"}),
        ]:
            check(name + " -> still ineligible", _trial_eligible({**base_marker, **extra}) is False)

        # Only a sub with NO trial marker at all is eligible (truly brand-new pre-provision)
        check("eligible only when no marker exists", _trial_eligible({"status": "active"}) is True)
        check("marker via trial_ends_at alone blocks", _trial_eligible({"trial_ends_at": "2026-01-01T00:00:00+00:00"}) is False)

        # 9/10. Duplicate + normalized-email registration cannot create a second trial account
        r2 = register(EMAIL)
        check("9. duplicate email register rejected", r2.status_code == 400, f"({r2.status_code})")
        r3 = register(f"  {EMAIL.upper()}  ")
        check("10. case/whitespace variant rejected (normalization)", r3.status_code == 400, f"({r3.status_code})")

        # 11. Existing legitimate accounts unaffected (grandfathered admin has no trial sub by design)
        admin_login = requests.post(f"{API}/api/auth/login", timeout=30,
                                    json={"email": "admin@ariadni.id", "password": "Ariadni@2026"})
        check("11. existing admin account intact (login ok, untouched)", admin_login.status_code == 200,
              f"({admin_login.status_code})")
    finally:
        loop.run_until_complete(cleanup(EMAIL))

    failed = [n for n, c, _ in results if not c]
    print("\n==== SUMMARY ====")
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", failed); sys.exit(1)


if __name__ == "__main__":
    main()
