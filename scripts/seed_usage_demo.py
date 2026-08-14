"""Seed a few realistic usage_events across real workspaces/users so the Super Admin
Usage & Cost Control dashboard shows populated data in Preview. Idempotent-ish (tagged source)."""
import asyncio, sys, random
sys.path.insert(0, "/app/backend")
import platform_v1 as P


async def main():
    # clear prior demo seeds
    await P.db.usage_events.delete_many({"source": "seed-demo"})
    ws = await P.db.workspaces.find({}, {"_id": 0, "id": 1, "name": 1, "subscription": 1, "plan": 1}).to_list(20)
    feats = ["business_card_scan", "event_badge_scan", "ai_followup"]
    n = 0
    for w in ws[:6]:
        m = await P.db.memberships.find_one({"workspace_id": w["id"]}, {"_id": 0, "user_id": 1})
        uid = (m or {}).get("user_id")
        plan = (w.get("subscription") or {}).get("plan") or w.get("plan") or "trial"
        for f in feats:
            cnt = random.randint(3, 40)
            for _ in range(cnt):
                await P.meter_usage(f, user_id=uid, workspace_id=w["id"], plan=plan,
                                    quantity=1, result="success", source="seed-demo", paid=True)
                n += 1
    print(f"seeded {n} usage_events across {min(len(ws),6)} workspaces")


asyncio.run(main())
