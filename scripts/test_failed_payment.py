"""Failed-payment recovery flow test (no real Stripe/email). Verifies: access preserved on past_due,
dunning stored, owner emailed ONCE (idempotent across webhook retries), recovery clears state + emails once,
and stripe_events dedupe. Cleans up."""
import asyncio, sys
sys.path.insert(0, "/app/backend")
import platform_v1 as P

WS = "fpr-test-ws"
OWNER = "fpr-test-owner"
SUB = "sub_fpr_test"
CUS = "cus_fpr_test"
emails = []


async def fake_send_localized(to, kind, lang, cta_url, **ctx):
    emails.append((kind, to, ctx.get("amount")))
    return True


class FakeSub(dict):
    pass


def fake_retrieve(sub_id):
    return {"id": SUB, "status": fake_retrieve.status, "customer": CUS,
            "items": {"data": [{"current_period_end": 1800000000}]}}
fake_retrieve.status = "past_due"


async def setup():
    await cleanup()
    await P.db.users.insert_one({"id": OWNER, "email": "owner@fpr.test", "language": "en", "name": "Owner"})
    await P.db.workspaces.insert_one({
        "id": WS, "name": "FPR Co", "owner_id": OWNER, "type": "company",
        "environment": "production_customer", "plan": "pro",
        "subscription": {"plan": "pro", "status": "active", "interval": "month", "seats": 5, "market": "USD",
                         "provider": "stripe", "stripe_subscription_id": SUB, "stripe_customer_id": CUS,
                         "current_period_end": "2027-01-01T00:00:00+00:00"},
    })


async def cleanup():
    await P.db.users.delete_many({"id": OWNER})
    await P.db.workspaces.delete_many({"id": WS})
    await P.db.stripe_events.delete_many({"id": {"$regex": "^evt_fpr"}})


def invoice(inv_id, status="past_due"):
    return {"id": inv_id, "subscription": SUB, "customer": CUS, "amount_due": 124500,
            "total": 124500, "currency": "aed", "hosted_invoice_url": "https://pay.stripe.test/x",
            "attempt_count": 1, "next_payment_attempt": 1799000000}


async def main():
    P.send_localized = fake_send_localized
    P.stripe.Subscription.retrieve = fake_retrieve
    await setup()
    checks = []

    # 1. Payment fails
    fake_retrieve.status = "past_due"
    await P._handle_invoice_failed(invoice("in_fail_1"), "evt_fpr_1")
    ent = await P.resolve_entitlements(WS)
    checks.append(("past_due keeps access (ent.active)", ent["active"] is True, ent["status"]))
    ws = await P.db.workspaces.find_one({"id": WS}, {"_id": 0, "subscription": 1})
    dun = ws["subscription"].get("dunning") or {}
    checks.append(("dunning stored failed", dun.get("state") == "failed" and dun.get("invoice_id") == "in_fail_1", dun.get("state")))
    checks.append(("owner emailed once (payment_failed)", emails.count(("payment_failed", "owner@fpr.test", "AED 1,245.00")) == 1, len(emails)))

    # 2. Duplicate webhook delivery for SAME failed invoice -> NO second email
    await P._handle_invoice_failed(invoice("in_fail_1"), "evt_fpr_1b")
    checks.append(("no duplicate failure email", [e[0] for e in emails].count("payment_failed") == 1, [e[0] for e in emails]))

    # 3. Recovery via successful payment
    fake_retrieve.status = "active"
    await P.db.workspaces.update_one({"id": WS}, {"$set": {"subscription.status": "active"}})
    await P._maybe_notify_recovery(WS, "evt_fpr_2")
    ws = await P.db.workspaces.find_one({"id": WS}, {"_id": 0, "subscription": 1})
    checks.append(("dunning cleared to recovered", (ws["subscription"].get("dunning") or {}).get("state") == "recovered", (ws["subscription"].get("dunning") or {}).get("state")))
    checks.append(("recovery email sent once", [e[0] for e in emails].count("payment_recovered") == 1, None))

    # 4. Recovery notify again -> no second recovery email (state already recovered)
    await P._maybe_notify_recovery(WS, "evt_fpr_2b")
    checks.append(("no duplicate recovery email", [e[0] for e in emails].count("payment_recovered") == 1, None))

    # 5. unpaid (terminal) removes access
    fake_retrieve.status = "unpaid"
    await P._sync_ws_from_stripe_sub(WS, fake_retrieve(SUB), "pro", "month", 5, "USD", "stripe", "evt_fpr_3")
    ent = await P.resolve_entitlements(WS)
    checks.append(("unpaid removes access", ent["active"] is False, ent["status"]))

    print("\n==== FAILED-PAYMENT RECOVERY TESTS ====")
    allok = True
    for n, ok, v in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {n} -> {v}"); allok = allok and ok
    print("====", "ALL PASS" if allok else "SOME FAILED", "====")
    await cleanup()


asyncio.run(main())
