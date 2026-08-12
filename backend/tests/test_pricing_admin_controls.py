"""Pricing closure follow-up: Super-Admin currency controls in /control/plans.

Drives the SAME endpoints the Control Center UI uses:
  - POST /admin/control/pricing/resolve   (live draft preview)
  - POST /admin/control/pricing/publish   (persist)
  - GET  /commercial/pricing              (public resolver used by landing/register/checkout)
Snapshots + restores commercial_config.
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


def check(n, c, e=""):
    results.append((n, c, e)); print(("PASS" if c else "FAIL"), "-", n, e)


def tok():
    return requests.post(f"{API}/api/auth/login", json=ADMIN, timeout=30).json()["token"]


def pricing(m=None):
    return requests.get(f"{API}/api/commercial/pricing{('?market='+m) if m else ''}", timeout=30).json()


def publish(hdr, patch, reason):
    return requests.post(f"{API}/api/admin/control/pricing/publish", headers=hdr, timeout=30,
                         json={"patch": patch, "apply_to": "new_only", "reason": reason})


def resolve(hdr, patch):
    return requests.post(f"{API}/api/admin/control/pricing/resolve", headers=hdr, timeout=30,
                         json={"patch": patch}).json()


async def snap():
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    doc = await db.commercial_config.find_one({"id": "global"})
    vers = {v["id"] for v in await db.commercial_config_versions.find({}, {"id": 1}).to_list(1000)}
    return doc, vers


async def restore(doc, vers):
    db = AsyncIOMotorClient(MONGO_URL)[DB_NAME]
    if doc:
        doc.pop("_id", None)
        await db.commercial_config.replace_one({"id": "global"}, doc, upsert=True)
    now = {v["id"] for v in await db.commercial_config_versions.find({}, {"id": 1}).to_list(1000)}
    extra = now - vers
    if extra:
        await db.commercial_config_versions.delete_many({"id": {"$in": list(extra)}})


USD = {"symbol": "$", "pro_month": 9.99, "pro_year": 89.99, "team_seat_month": 8.99, "team_seat_year": 79.99}


def main():
    loop = asyncio.get_event_loop()
    doc, vers = loop.run_until_complete(snap())
    hdr = {"Authorization": f"Bearer {tok()}"}
    try:
        d0 = pricing(); fx0 = d0["fx_rates"]

        # A. USD change -> AUTO currencies recompute (persisted)
        publish(hdr, {"regional_pricing": {"USD": USD}, "manual_price_markets": []}, "usd-base")
        aed = pricing("AED")["pricing"]; sar = pricing("SAR")["pricing"]
        check("A. USD change -> AUTO AED recomputes",
              aed["pricing_source"] == "auto" and abs(aed["pro_year"] - round(89.99 * fx0["AED"], 2)) < 0.01)

        # B. Edit AED FX (resolve preview) -> AED recomputes ONLY
        newfx = round(fx0["AED"] + 0.5, 4)
        rv = resolve(hdr, {"fx_rates": {"AED": newfx}})
        ra = rv["resolved_all"]
        check("B1. AED FX edit -> AED pro_year uses new rate",
              abs(ra["AED"]["pro_year"] - round(89.99 * newfx, 2)) < 0.01)
        check("B2. SAR/EUR/GBP unchanged by AED FX edit",
              ra["SAR"]["pro_year"] == sar["pro_year"]
              and abs(ra["EUR"]["pro_year"] - round(89.99 * fx0["EUR"], 2)) < 0.01
              and abs(ra["GBP"]["pro_year"] - round(89.99 * fx0["GBP"], 2)) < 0.01)

        # C. Switch AED -> MANUAL, manual values win
        publish(hdr, {"manual_price_markets": ["AED"],
                      "regional_pricing": {"AED": {"symbol": "AED ", "pro_month": 36.99, "pro_year": 369.99,
                                                   "team_seat_month": 18.0, "team_seat_year": 180.0}}}, "aed-manual")
        aed = pricing("AED")["pricing"]
        check("C. AED MANUAL override wins",
              aed["pricing_source"] == "manual" and aed["pro_year"] == 369.99)

        # D. Change USD while AED MANUAL -> AED unchanged, others recompute
        USD2 = {**USD, "pro_year": 99.99}
        publish(hdr, {"regional_pricing": {"USD": USD2}}, "usd-2")
        aed = pricing("AED")["pricing"]; sar = pricing("SAR")["pricing"]
        check("D1. manual AED stays 369.99 after USD change", aed["pro_year"] == 369.99)
        check("D2. AUTO SAR recomputes from new USD",
              abs(sar["pro_year"] - round(99.99 * fx0["SAR"], 2)) < 0.01)

        # E. Switch AED back to AUTO -> recomputes from USD base + FX
        publish(hdr, {"manual_price_markets": []}, "aed-auto")
        aed = pricing("AED")["pricing"]
        check("E. AED back to AUTO recomputes",
              aed["pricing_source"] == "auto" and abs(aed["pro_year"] - round(99.99 * fx0["AED"], 2)) < 0.01)

        # F. EUR/SAR/GBP continue independently (each == usd*own fx)
        allp = pricing()["resolved_all"]
        okF = all(abs(allp[m]["pro_year"] - round(99.99 * fx0[m], 2)) < 0.01 for m in ["EUR", "SAR", "GBP"])
        check("F. EUR/SAR/GBP independent auto conversion", okF)

        # G. Savings mathematically correct for each currency
        def sv(p, mo, yr):
            return max(0, round((1 - (p[yr] / (p[mo] * 12))) * 100))
        okG = all(sv(allp[m], "pro_month", "pro_year") == allp[m]["pro_annual_savings_pct"]
                  and sv(allp[m], "team_seat_month", "team_seat_year") == allp[m]["team_annual_savings_pct"]
                  for m in ["USD", "AED", "SAR", "EUR", "GBP"])
        check("G. savings match shown prices for every currency", okG)

        # H. Persist after refresh (fresh GET reflects last publish)
        check("H. changes persist after refresh", pricing("SAR")["pricing"]["pro_year"] == round(99.99 * fx0["SAR"], 2))

        # I. Landing/registration/checkout resolver agree (all use resolve_market_pricing)
        reg = pricing()["pricing"]  # registration default market
        land = pricing(reg["market"])["pricing"]  # landing ?market
        rslv = resolve(hdr, {})["resolved_all"][reg["market"]]  # checkout/admin resolver
        check("I. landing == registration == resolver",
              reg["pro_year"] == land["pro_year"] == rslv["pro_year"])

        # J. Production config not overwritten by seed/default: published USD persists (not DEFAULT 99.99? here we set 99.99 intentionally; assert it's our value, not reseeded team 50)
        check("J. seed/default does not overwrite published config",
              pricing("USD")["pricing"]["team_seat_year"] == 79.99)
    finally:
        loop.run_until_complete(restore(doc, vers))

    failed = [n for n, c, _ in results if not c]
    print("\n==== SUMMARY ====")
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", failed); sys.exit(1)


if __name__ == "__main__":
    main()
