"""PREVIEW-ONLY: enable Stripe Tax on the TEST/sandbox account so automatic_tax can initialize,
allowing tax-safe checkout QA. Idempotent. Never runs against live keys (guards STRIPE_MODE).
Does NOT create tax registrations and does NOT touch prices/secrets."""
import os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import stripe

mode = os.environ.get("STRIPE_MODE", "test")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
if mode != "test":
    print(f"STRIPE_MODE={mode} — refusing to modify non-test account. Aborting."); sys.exit(0)
if not stripe.api_key:
    print("No STRIPE_SECRET_KEY configured."); sys.exit(0)

try:
    s = stripe.tax.Settings.retrieve()
    ho = getattr(s, "head_office", None)
    if ho and getattr(ho, "address", None) and ho.address.get("country"):
        print(f"Stripe Tax head office already set: {ho.address.get('country')} — status={getattr(s,'status',None)}")
    else:
        stripe.tax.Settings.modify(
            head_office={"address": {"country": "AE", "line1": "Business Bay", "city": "Dubai"}},
            defaults={"tax_behavior": "exclusive", "tax_code": "txcd_10103001"},
        )
        s = stripe.tax.Settings.retrieve()
        print(f"Stripe Tax head office set to AE (Dubai). status={getattr(s,'status',None)}")
except Exception as e:
    print(f"Stripe Tax settings error ({type(e).__name__}): {e}")
