"""Verifies the admin-cancel -> Google Calendar delete sync path.
No real Google calls: httpx.AsyncClient is monkeypatched and the access token is stubbed.
"""
import asyncio, os, sys, uuid, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server


class _FakeResp:
    def __init__(self, status=204):
        self.status_code = status
    def json(self):
        return {}


class _FakeClient:
    """Records HTTP verbs/URLs; returns success."""
    calls = []
    def __init__(self, *a, **k):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def delete(self, url, headers=None):
        _FakeClient.calls.append(("DELETE", url))
        return _FakeResp(204)
    async def patch(self, url, headers=None, json=None):
        _FakeClient.calls.append(("PATCH", url))
        return _FakeResp(200)
    async def post(self, url, headers=None, json=None):
        _FakeClient.calls.append(("POST", url))
        return _FakeResp(200)


async def main():
    db = server.db
    owner_id = f"test-owner-{uuid.uuid4()}"
    meeting_id = str(uuid.uuid4())
    event_id = f"evt_{uuid.uuid4().hex[:12]}"

    # stubs so no real Google traffic / secrets are used
    server._httpx.AsyncClient = _FakeClient
    async def _fake_token(uid):
        return "STUB"
    orig_token = server._gcal_access_token
    orig_cfg = server._gcal_configured
    server._gcal_access_token = _fake_token
    server._gcal_configured = lambda: True

    # a "connected" calendar for the owner + a cancelled meeting that still has an event id
    await db.google_calendar_connections.insert_one({
        "user_id": owner_id, "revoked": False, "refresh_token": "x", "access_token": "y",
    })
    await db.meetings.insert_one({
        "id": meeting_id, "card_id": "card-x", "owner_user_id": owner_id,
        "status": "cancelled", "google_event_id": event_id,
        "start_utc": "2026-08-12T05:00:00+00:00", "end_utc": "2026-08-12T05:30:00+00:00",
        "duration": 30, "meeting_type_title": "Test", "visitor_name": "QA",
    })

    _FakeClient.calls = []
    print("google_event_id present at cancel time:", bool((await db.meetings.find_one({"id": meeting_id}))["google_event_id"]))

    await server.sync_meeting_calendar(meeting_id)

    deletes = [c for c in _FakeClient.calls if c[0] == "DELETE"]
    print("HTTP calls made:", _FakeClient.calls)
    m_after = await db.meetings.find_one({"id": meeting_id})
    cleared = m_after.get("google_event_id") is None
    correct_url = any(event_id in u for _, u in deletes)

    print("RESULT delete_fired:", len(deletes) == 1, "| correct_event_url:", correct_url, "| google_event_id_cleared:", cleared)
    ok = len(deletes) == 1 and correct_url and cleared

    # cleanup
    await db.meetings.delete_one({"id": meeting_id})
    await db.google_calendar_connections.delete_one({"user_id": owner_id})
    server._gcal_access_token = orig_token
    server._gcal_configured = orig_cfg

    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
