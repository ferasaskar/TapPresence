"""One-off migration: enable native TapPresence booking on all PUBLISHED cards.
Idempotent. Pre-seeds default availability + meeting types (Mon-Fri 9-6, 15/30/45 min)
so the public "Book a Meeting" button works and is editable per card.
"""
import asyncio, os, uuid, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

DEFAULT_AVAIL = {"days": [1, 2, 3, 4, 5], "start": "09:00", "end": "18:00",
                 "buffer_before": 0, "buffer_after": 15, "min_notice_hours": 2,
                 "max_days": 60, "slot_interval": 30, "blocked": []}
DEFAULT_MTS = [
    {"title": "15 Min Introduction", "duration": 15},
    {"title": "30 Min Consultation", "duration": 30},
    {"title": "45 Min Meeting", "duration": 45},
]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    cards = await db.digital_cards.find({"status": "published"}, {"_id": 0, "id": 1, "slug": 1, "booking": 1}).to_list(10000)
    print(f"Found {len(cards)} published cards")

    enabled, already, seeded_avail, seeded_mts = 0, 0, 0, 0
    for c in cards:
        cid = c["id"]
        b = c.get("booking") or {}
        if b.get("nativeEnabled"):
            already += 1
        else:
            tz = b.get("timezone") or "Asia/Dubai"
            await db.digital_cards.update_one(
                {"id": cid},
                {"$set": {"booking.nativeEnabled": True, "booking.timezone": tz,
                          "booking.bookingUrl": b.get("bookingUrl", "")}},
            )
            enabled += 1

        # pre-seed availability if missing
        if not await db.availability.find_one({"card_id": cid}):
            await db.availability.insert_one({"card_id": cid, **DEFAULT_AVAIL})
            seeded_avail += 1

        # pre-seed meeting types if none
        if await db.meeting_types.count_documents({"card_id": cid}) == 0:
            for i, d in enumerate(DEFAULT_MTS):
                await db.meeting_types.insert_one({
                    "id": str(uuid.uuid4()), "card_id": cid, "title": d["title"], "description": "",
                    "duration": d["duration"], "location_type": "video", "location_detail": "",
                    "enabled": True, "price": None, "order": i, "confirmation_mode": "auto",
                })
            seeded_mts += 1

    print(f"Enabled native booking on: {enabled}")
    print(f"Already enabled (skipped): {already}")
    print(f"Seeded default availability for: {seeded_avail} cards")
    print(f"Seeded default meeting types for: {seeded_mts} cards")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
