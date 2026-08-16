"""Pricing & multi-currency correctness tests.

Snapshots commercial_config, drives the real Super-Admin publish/override APIs,
asserts source-of-truth behaviour, then restores the original config + removes
any versions created during the test.
"""
import asyncio
import os
import sys

import requests
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL"):
            API = line.split("=", 1)[1].strip().strip('"').rstrip("/")

ADMIN = {"email": "admin@ariadni.id", "password": "Ariadni@2026"}
results = []


def check(name, cond, extra=""):
    results.append((name, cond, extra))
    print(("PASS" if cond else "FAIL"), "-", name, extra)


def token():
    r = requests.post(f"{API}/api/auth/login", json=ADMIN, timeout=30)
    r.raise_for_status()
    return r.json()["token"]


def pricing(market=None):
    q = f"?market={market}" if market else ""
    return requests.get(f"{API}/api/commercial/pricing{q}", timeout=30).json()


async def snapshot():
    c = AsyncIOMotorClient(MONGO_URL)
    db = c[DB_NAME]
    doc = await db.commercial_config.find_one({"id": "global"})
    ver_ids = {v["id"] for v in await db.commercial_config_versions.find({}, {"id": 1}).to_list(1000)}
    return doc, ver_ids


async def restore(doc, ver_ids):
    c = AsyncIOMotorClient(MONGO_URL)
    db = c[DB_NAME]
    if doc:
        doc.pop("_id", None)
        await db.commercial_config.replace_one({"id": "global"}, doc, upsert=True)
    now_ids = {v["id"] for v in await db.commercial_config_versions.find({}, {"id": 1}).to_list(1000)}
    created = now_ids - ver_ids
    if created:
        await db.commercial_config_versions.delete_many({"id": {"$in": list(created)}})


def main():
    loop = asyncio.get_event_loop()
    doc, ver_ids = loop.run_until_complete(snapshot())
    tk = token()
    hdr = {"Authorization": f"Bearer {tk}"}
    try:
        d0 = pricing()
        fx = d0["fx_rates"]
        default_market = "USD"

        # 1. Base USD change propagates to auto currencies
        requests.post(f"{API}/api/admin/control/pricing/publish", headers=hdr, timeout=30, json={
            "patch": {"regional_pricing": {"USD": {"symbol": "$", "pro_month": 9.99, "pro_year": 89.99,
                                                    "team_seat_month": 8.99, "team_seat_year": 79.99}}},
            "apply_to": "new_only", "reason": "test-usd-change"})
        aed = pricing("AED")["pricing"]
        exp_pro_year = round(89.99 * fx["AED"], 2)
        check("1. USD change propagates to auto AED",
              aed["pricing_source"] == "auto" and abs(aed["pro_year"] - exp_pro_year) < 0.01,
              f"AED pro_year={aed['pro_year']} exp={exp_pro_year}")

        # 3. Pro and Team use the SAME conversion ratio
        usd = pricing("USD")["pricing"]
        r_pro = aed["pro_year"] / usd["pro_year"]
        r_team = aed["team_seat_year"] / usd["team_seat_year"]
        check("3. Pro & Team share one conversion ratio (== FX)",
              abs(r_pro - fx["AED"]) < 0.01 and abs(r_team - fx["AED"]) < 0.01,
              f"pro_ratio={r_pro:.4f} team_ratio={r_team:.4f} fx={fx['AED']}")

        # 5. Annual saving % matches the displayed prices for each currency
        def savings(m, plan):
            mo = m[f"{plan}_month" if plan == "pro" else "team_seat_month"]
            yr = m[f"{plan}_year" if plan == "pro" else "team_seat_year"]
            return max(0, round((1 - (yr / (mo * 12))) * 100))
        ok5 = all(
            savings(pp := pricing(mk)["pricing"], "pro") == pp["pro_annual_savings_pct"]
            and savings(pp, "team") == pp["team_annual_savings_pct"]
            for mk in ["USD", "AED", "SAR", "EUR", "GBP"]
        )
        check("5. saving% matches shown monthly/annual for every currency", ok5)

        # 5b. savings coherent across auto currencies (same as USD base)
        base_save = usd["pro_annual_savings_pct"]
        coh = all(pricing(mk)["pricing"]["pro_annual_savings_pct"] == base_save for mk in ["AED", "SAR", "EUR", "GBP"])
        check("5b. auto currencies share the USD base saving%", coh, f"base={base_save}%")

        # 4. Monthly & annual belong to the same market/currency
        check("4. resolved market/symbol self-consistent",
              aed["market"] == "AED" and aed["symbol"].strip() == "AED", f"symbol={aed['symbol']!r}")

        # 6/7. Landing (?market) and registration (default) agree with resolved_all
        dd = pricing()
        check("6. landing ?market == resolved_all[market]",
              pricing("SAR")["pricing"]["pro_year"] == dd["resolved_all"]["SAR"]["pro_year"])
        check("7. registration default == resolved_all[default_market]",
              dd["pricing"]["pro_year"] == dd["resolved_all"][default_market]["pro_year"])

        # 8. Team minimum-seat pricing present & coherent
        check("8. team min_seats present and team pricing derived",
              int(dd["plans"]["team"]["min_seats"]) >= 1
              and abs(pricing("AED")["pricing"]["team_seat_year"] - round(79.99 * fx["AED"], 2)) < 0.01)

        # 9. Unknown currency falls back to USD base, never another market's price
        zz = pricing("ZZZ")["pricing"]
        check("9. unknown market -> USD base fallback (no cross-market leak)",
              zz["market"] == "USD" and zz["pro_year"] == usd["pro_year"])

        # 2. Manual override preserved when USD changes
        requests.put(f"{API}/api/admin/commercial", headers=hdr, timeout=30, json={
            "manual_price_markets": ["AED"],
            "regional_pricing": {"AED": {"symbol": "AED ", "pro_month": 36.99, "pro_year": 369.99,
                                         "team_seat_month": 18.0, "team_seat_year": 180.0}}})
        aed_m = pricing("AED")["pricing"]
        check("2a. AED becomes MANUAL override (369.99)",
              aed_m["pricing_source"] == "manual" and aed_m["pro_year"] == 369.99, f"({aed_m['pro_year']})")
        requests.post(f"{API}/api/admin/control/pricing/publish", headers=hdr, timeout=30, json={
            "patch": {"regional_pricing": {"USD": {"symbol": "$", "pro_month": 9.99, "pro_year": 99.99,
                                                    "team_seat_month": 5.0, "team_seat_year": 50.0}}},
            "apply_to": "new_only", "reason": "test-usd-change-2"})
        aed_after = pricing("AED")["pricing"]
        sar_after = pricing("SAR")["pricing"]
        check("2b. manual AED preserved after USD change", aed_after["pro_year"] == 369.99, f"({aed_after['pro_year']})")
        check("2c. auto SAR recomputed from new USD (no stale)",
              abs(sar_after["pro_year"] - round(99.99 * fx["SAR"], 2)) < 0.01, f"({sar_after['pro_year']})")

        # 10. Version/publish behavior intact
        vers = requests.get(f"{API}/api/admin/control/pricing/versions", headers=hdr, timeout=30).json()
        check("10. publish created versioned snapshots", len(vers.get("items", [])) >= 2)
    finally:
        loop.run_until_complete(restore(doc, ver_ids))

    failed = [n for n, c, _ in results if not c]
    print("\n==== SUMMARY ====")
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
