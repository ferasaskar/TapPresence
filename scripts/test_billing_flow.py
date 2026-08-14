import os, sys, json, time, subprocess, urllib.request
import stripe
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
API = subprocess.check_output("grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2", shell=True).decode().strip()
MONGO = os.environ["MONGO_URL"]; DB = os.environ["DB_NAME"]


def curl(method, path, token=None, body=None):
    cmd = ["curl", "-s", "-X", method, f"{API}/api{path}", "-H", "Content-Type: application/json"]
    if token: cmd += ["-H", f"Authorization: Bearer {token}"]
    if body is not None: cmd += ["-d", json.dumps(body)]
    return json.loads(subprocess.check_output(cmd).decode() or "{}")


def make_stripe_sub(interval):
    prod = stripe.Product.create(name=f"TP Test {interval}")
    price = stripe.Price.create(product=prod.id, unit_amount=1500, currency="usd", recurring={"interval": interval})
    pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
    cust = stripe.Customer.create(email=f"tptest_{interval}@example.com")
    stripe.PaymentMethod.attach(pm.id, customer=cust.id)
    stripe.Customer.modify(cust.id, invoice_settings={"default_payment_method": pm.id})
    sub = stripe.Subscription.create(customer=cust.id, items=[{"price": price.id}], expand=["latest_invoice.payment_intent"])
    return sub, cust.id, prod.id, price.id


async def run():
    db = AsyncIOMotorClient(MONGO)[DB]
    results = []
    for interval in ("month", "year"):
        email = f"billtest_{interval}_{int(time.time())}@example.com"
        # 1) register (gets trial + workspace) -> token
        reg = curl("POST", "/auth/register", body={"email": email, "name": "Bill Test", "password": "TestPass@2026", "account_type": "individual"})
        token = reg.get("token"); assert token, f"register failed: {reg}"
        me = curl("GET", "/billing", token)
        ws_id = None
        u = await db.users.find_one({"email": email}, {"_id": 0, "id": 1})
        ms = await db.memberships.find_one({"user_id": u["id"]}, {"_id": 0, "workspace_id": 1})
        ws_id = ms["workspace_id"]
        # 2) create a real Stripe TEST subscription and wire it to this workspace
        sub, cust_id, prod_id, price_id = make_stripe_sub(interval)
        cpe = sub.get("current_period_end") or (sub["items"]["data"][0].get("current_period_end"))
        from datetime import datetime, timezone
        await db.workspaces.update_one({"id": ws_id}, {"$set": {"plan": "pro", "subscription": {
            "plan": "pro", "status": "active", "interval": interval, "seats": 1, "market": "USD",
            "provider": "stripe", "stripe_subscription_id": sub["id"], "stripe_customer_id": cust_id,
            "current_period_end": datetime.fromtimestamp(cpe, timezone.utc).isoformat(),
            "trial_started_at": "2020-01-01T00:00:00+00:00",  # simulate trial already consumed
            "updated_at": datetime.now(timezone.utc).isoformat()}}})
        # 3) GET /billing -> new fields
        b = curl("GET", "/billing", token)
        r = {"interval_reported": b.get("interval"), "trial_eligible": b.get("trial_eligible"),
             "cancel_flag": b.get("cancel_at_period_end"), "status": b.get("status"),
             "period_end": b.get("current_period_end")}
        # 4) CANCEL -> Stripe should have cancel_at_period_end True
        curl("POST", "/billing/cancel", token)
        s_after_cancel = stripe.Subscription.retrieve(sub["id"])
        b2 = curl("GET", "/billing", token)
        r["after_cancel_stripe_flag"] = s_after_cancel["cancel_at_period_end"]
        r["after_cancel_status"] = b2.get("status")
        r["after_cancel_ui_flag"] = b2.get("cancel_at_period_end")
        # 5) RESUME -> Stripe cancel_at_period_end back to False, status active
        rz = curl("POST", "/billing/resume", token)
        s_after_resume = stripe.Subscription.retrieve(sub["id"])
        b3 = curl("GET", "/billing", token)
        r["after_resume_stripe_flag"] = s_after_resume["cancel_at_period_end"]
        r["after_resume_status"] = b3.get("status")
        r["after_resume_period_end"] = b3.get("current_period_end")
        # 6) cancel again -> stays synced
        curl("POST", "/billing/cancel", token)
        s_again = stripe.Subscription.retrieve(sub["id"])
        r["cancel_again_stripe_flag"] = s_again["cancel_at_period_end"]
        results.append((interval, r))
        # cleanup stripe + db
        try: stripe.Subscription.cancel(sub["id"])
        except Exception: pass
        await db.memberships.delete_many({"user_id": u["id"]})
        await db.workspaces.delete_one({"id": ws_id})
        await db.users.delete_one({"id": u["id"]})
        await db.email_verifications.delete_many({"user_id": u["id"]})
    print(json.dumps(results, indent=2))

asyncio.run(run())
