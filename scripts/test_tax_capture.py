"""Verify tax capture helpers (session + invoice), masking, status mapping, and that collected tax
is reported separately from revenue. Uses synthetic Stripe-shaped objects. Cleans up after."""
import asyncio, sys
sys.path.insert(0, "/app/backend")
import platform_v1 as P

WS = "tax-test-ws"


async def main():
    await P.db.billing_tax_records.delete_many({"workspace_id": WS})
    # UAE B2B checkout with TRN, 5% VAT on AED 12450 base (minor units)
    await P._record_tax_from_session({
        "id": "cs_uae_1", "customer": "cus_1", "subscription": "sub_1", "currency": "aed",
        "amount_subtotal": 124500, "amount_total": 130725,
        "total_details": {"amount_tax": 6225, "amount_discount": 0},
        "automatic_tax": {"status": "complete"},
        "customer_details": {"address": {"country": "AE", "state": None, "postal_code": None},
                             "tax_ids": [{"type": "ae_trn", "value": "100123456700003"}]},
    }, WS, "e1")
    # US CA sales tax
    await P._record_tax_from_session({
        "id": "cs_us_1", "customer": "cus_2", "subscription": "sub_2", "currency": "usd",
        "amount_subtotal": 9999, "amount_total": 10874,
        "total_details": {"amount_tax": 875, "amount_discount": 0},
        "automatic_tax": {"status": "complete"},
        "customer_details": {"address": {"country": "US", "state": "CA", "postal_code": "94107"}, "tax_ids": []},
    }, WS, "e2")
    # EU with discount, VAT ID present
    await P._record_tax_from_invoice({
        "id": "in_eu_1", "customer": "cus_3", "subscription": "sub_3", "currency": "eur",
        "subtotal": 9999, "total": 11039, "tax": 2040,
        "total_discount_amounts": [{"amount": 2000}],
        "automatic_tax": {"status": "complete"},
        "customer_address": {"country": "DE"}, "customer_tax_ids": [{"type": "eu_vat", "value": "DE123456789"}],
    }, WS, "e3")
    # Location unknown (should NOT show as zero-tax-due)
    await P._record_tax_from_session({
        "id": "cs_unknown", "customer": "cus_4", "subscription": "sub_4", "currency": "usd",
        "amount_subtotal": 9999, "amount_total": 9999,
        "total_details": {"amount_tax": 0, "amount_discount": 0},
        "automatic_tax": {"status": "requires_location_inputs"},
        "customer_details": {"address": {}, "tax_ids": []},
    }, WS, "e4")

    rows = await P.db.billing_tax_records.find({"workspace_id": WS}, {"_id": 0}).to_list(50)
    checks = []
    uae = next(r for r in rows if r["source_id"] == "cs:cs_uae_1")
    checks.append(("UAE tax captured 5% AED 62.25", uae["tax_amount"] == 6225 and uae["currency"] == "AED", uae["tax_amount"]))
    checks.append(("TRN masked (no full id)", uae["tax_id_masked"] == "•••0003" and "100123456700003" not in str(uae), uae["tax_id_masked"]))
    checks.append(("UAE status=calculated", uae["tax_status"] == "calculated", uae["tax_status"]))
    us = next(r for r in rows if r["source_id"] == "cs:cs_us_1")
    checks.append(("US state=CA captured", us["state"] == "CA", us["state"]))
    unk = next(r for r in rows if r["source_id"] == "cs:cs_unknown")
    checks.append(("unknown location != no_tax_due", unk["tax_status"] == "location_required", unk["tax_status"]))
    eu = next(r for r in rows if r["source_id"] == "inv:in_eu_1")
    checks.append(("EU discount captured", eu["discount_amount"] == 2000, eu["discount_amount"]))
    checks.append(("EU net = total-tax excludes tax from revenue", (eu["total_amount"] - eu["tax_amount"]) == 8999, eu["total_amount"] - eu["tax_amount"]))

    print("\n==== TAX CAPTURE TESTS ====")
    allok = True
    for n, ok, v in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {n} -> {v}"); allok = allok and ok
    print("====", "ALL PASS" if allok else "SOME FAILED", "====")
    await P.db.billing_tax_records.delete_many({"workspace_id": WS})
    print("cleaned up synthetic records")


asyncio.run(main())
