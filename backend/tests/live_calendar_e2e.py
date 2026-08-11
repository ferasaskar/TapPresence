"""LIVE end-to-end Google Calendar test (NO stubs) against the real connected account.
Flow: Create -> Reschedule -> Cancel on card edrina-cepele (owner has a real Calendar connection).
Verifies TapPresence stored UTC + Google event start/end/timeZone at every step for Asia/Dubai.
Prints NO tokens/secrets. Cleans up the test meeting + any residual event at the end.
"""
import asyncio, os, sys, uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ["MONGO_URL"]; DB_NAME = os.environ["DB_NAME"]
CID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]; CSECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
SLUG = "edrina-cepele"; DUBAI = ZoneInfo("Asia/Dubai")
EMAIL, PW = "work@gmail.com", "mohammed"
GBASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]


def dub(iso):
    return datetime.fromisoformat(iso).astimezone(DUBAI).strftime("%Y-%m-%d %H:%M %Z")


async def gtoken(owner):
    conn = await db.google_calendar_connections.find_one({"user_id": owner}, {"_id": 0})
    async with httpx.AsyncClient(timeout=20) as cx:
        r = await cx.post("https://oauth2.googleapis.com/token", data={
            "client_id": CID, "client_secret": CSECRET,
            "refresh_token": conn["refresh_token"], "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]


async def gget_event(token, eid):
    async with httpx.AsyncClient(timeout=20) as cx:
        r = await cx.get(f"{GBASE}/{eid}", headers={"Authorization": f"Bearer {token}"})
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})


async def pick_slot(mt_id, day_offset):
    # find a bookable slot on the Nth upcoming weekday (Dubai)
    for off in range(day_offset, day_offset + 7):
        d = (datetime.now(DUBAI) + timedelta(days=off))
        if d.weekday() >= 5:
            continue
        ds = d.strftime("%Y-%m-%d")
        async with httpx.AsyncClient(timeout=20) as cx:
            r = await cx.get(f"{API}/cards/{SLUG}/slots", params={"meeting_type_id": mt_id, "date": ds})
        slots = r.json().get("slots", [])
        if slots:
            return ds, slots
    return None, []


async def main():
    print(f"BASE={BASE}\n")
    async with httpx.AsyncClient(timeout=30) as cx:
        tok = (await cx.post(f"{API}/auth/login", json={"email": EMAIL, "password": PW})).json()["token"]
    H = {"Authorization": f"Bearer {tok}"}

    card = await db.digital_cards.find_one({"slug": SLUG}, {"_id": 0, "id": 1, "owner_user_id": 1, "booking": 1})
    owner = card["owner_user_id"]
    print("owner_tz(card.booking.timezone) =", (card.get("booking") or {}).get("timezone"))

    # token scope check (no token printed)
    gt = await gtoken(owner)
    async with httpx.AsyncClient(timeout=20) as cx:
        ti = (await cx.get("https://oauth2.googleapis.com/tokeninfo", params={"access_token": gt})).json()
    print("GOOGLE TOKEN SCOPE =", ti.get("scope"))
    print("  -> calendar.events granted:", "calendar" in (ti.get("scope") or ""), "\n")

    async with httpx.AsyncClient(timeout=30) as cx:
        bc = (await cx.get(f"{API}/cards/{SLUG}/booking")).json()
    mt = bc["meeting_types"][0]
    print(f"owner_timezone(api)={bc['owner_timezone']}  meeting_type='{mt['title']}' {mt['duration']}min\n")

    # ---------- CREATE ----------
    ds, slots = await pick_slot(mt["id"], 1)
    slot = slots[0]
    async with httpx.AsyncClient(timeout=30) as cx:
        book = (await cx.post(f"{API}/cards/{SLUG}/book", json={
            "meeting_type_id": mt["id"], "start": slot, "name": "E2E TZ Test",
            "email": "e2e-tz-test@example.com", "phone": "", "note": "auto e2e",
            "visitor_tz": "Asia/Dubai"})).json()
    mid = book["meeting"]["id"]
    await asyncio.sleep(1.5)
    m = await db.meetings.find_one({"id": mid}, {"_id": 0})
    eid = m.get("google_event_id")
    print("== CREATE ==")
    print("  slot picked (Dubai):", dub(slot))
    print("  TapPresence start_utc:", m["start_utc"], "->", dub(m["start_utc"]))
    print("  google_event_id:", eid)
    if eid:
        sc, ev = await gget_event(gt, eid)
        st = ev.get("start", {})
        print("  GCAL http:", sc, "| start.dateTime:", st.get("dateTime"), "| start.timeZone:", st.get("timeZone"))
        print("  GCAL start (Dubai):", dub(st["dateTime"]) if st.get("dateTime") else None)
        print("  MATCH:", st.get("dateTime") and datetime.fromisoformat(st["dateTime"]) == datetime.fromisoformat(m["start_utc"]))
    print()

    # ---------- RESCHEDULE ----------
    ds2, slots2 = await pick_slot(mt["id"], 2)
    newslot = slots2[min(2, len(slots2) - 1)]
    async with httpx.AsyncClient(timeout=30) as cx:
        rr = await cx.post(f"{API}/admin/meetings/{mid}/reschedule", headers=H, json={"start": newslot})
    await asyncio.sleep(1.5)
    m2 = await db.meetings.find_one({"id": mid}, {"_id": 0})
    print("== RESCHEDULE ==  (http", rr.status_code, ")")
    print("  new slot (Dubai):", dub(newslot))
    print("  TapPresence start_utc:", m2["start_utc"], "->", dub(m2["start_utc"]))
    print("  google_event_id (unchanged):", m2.get("google_event_id"), "== old:", m2.get("google_event_id") == eid)
    if m2.get("google_event_id"):
        sc, ev = await gget_event(gt, m2["google_event_id"])
        st = ev.get("start", {})
        print("  GCAL http:", sc, "| start.dateTime:", st.get("dateTime"), "| start (Dubai):", dub(st["dateTime"]) if st.get("dateTime") else None)
        print("  MATCH:", st.get("dateTime") and datetime.fromisoformat(st["dateTime"]) == datetime.fromisoformat(m2["start_utc"]))
    print()

    # ---------- CANCEL (dashboard endpoint) ----------
    cancel_eid = m2.get("google_event_id")
    async with httpx.AsyncClient(timeout=30) as cx:
        cc = await cx.patch(f"{API}/admin/meetings/{mid}/status", headers=H, json={"status": "cancelled"})
    await asyncio.sleep(1.5)
    m3 = await db.meetings.find_one({"id": mid}, {"_id": 0})
    print("== CANCEL == (dashboard PATCH /admin/meetings/{id}/status http", cc.status_code, ")")
    print("  meeting.status:", m3["status"], "| meeting.google_event_id:", m3.get("google_event_id"))
    if cancel_eid:
        sc, ev = await gget_event(gt, cancel_eid)
        status = ev.get("status")
        print("  GCAL GET event http:", sc, "| event.status:", status)
        deleted = sc == 404 or status == "cancelled"
        print("  EVENT DELETED ON GOOGLE:", deleted)
    print()

    # cleanup
    await db.meetings.delete_one({"id": mid})
    if m.get("lead_id"):
        await db.leads.delete_one({"id": m["lead_id"]})
    # ensure no residual event
    if cancel_eid:
        sc, _ = await gget_event(gt, cancel_eid)
        if sc not in (404,):
            async with httpx.AsyncClient(timeout=20) as cx:
                await cx.delete(f"{GBASE}/{cancel_eid}", headers={"Authorization": f"Bearer {gt}"})
    print("cleanup done (test meeting removed).")


if __name__ == "__main__":
    asyncio.run(main())
