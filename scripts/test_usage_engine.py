"""Focused engine test for Usage & Cost Control (no LLM cost).
Validates: metering + cost calc, atomic concurrency reservation, per-user/workspace/event scope,
override precedence, failed-op release, plan limit resolution, period key. Cleans up after itself."""
import asyncio, sys
sys.path.insert(0, "/app/backend")
import platform_v1 as P

TEST_FEATURE = "business_card_scan"
U = "test-usage-user-1"
WS = "test-usage-ws-1"
EV = "test-usage-event-1"


async def reset_feature():
    cfg = await P.get_usage_config()
    feats = cfg["features"]
    feats[TEST_FEATURE] = P._default_feature_config(P._USAGE_FEATURE_MAP[TEST_FEATURE])
    await P.db.usage_config.update_one({"id": "global"}, {"$set": {"features": feats}}, upsert=True)


async def cleanup():
    await P.db.usage_events.delete_many({"user_id": U})
    await P.db.usage_events.delete_many({"workspace_id": WS})
    await P.db.usage_meters.delete_many({"scope_id": {"$in": [U, WS, EV]}})
    await P.db.usage_overrides.delete_many({"scope_id": {"$in": [U, WS, EV]}})
    await reset_feature()


async def set_feature(**patch):
    cfg = await P.get_usage_config()
    feats = cfg["features"]
    feats[TEST_FEATURE].update(patch)
    await P.db.usage_config.update_one({"id": "global"}, {"$set": {"features": feats}}, upsert=True)


async def main():
    ok = []
    await cleanup()

    # 1. Cost calc: unit_cost 0.02 * 3 = 0.06
    for _ in range(3):
        await P.meter_usage(TEST_FEATURE, user_id=U, workspace_id=WS, quantity=1, result="success", paid=True)
    rows = await P.db.usage_events.find({"user_id": U, "result": "success"}).to_list(100)
    total = round(sum(r["cost"] for r in rows), 4)
    ok.append(("cost_calc 3x0.02=0.06", total == 0.06, total))

    # 2. Failed op → cost 0 (does not consume paid cost)
    await P.meter_usage(TEST_FEATURE, user_id=U, workspace_id=WS, quantity=1, result="failed", paid=False)
    failed = await P.db.usage_events.find_one({"user_id": U, "result": "failed"})
    ok.append(("failed_op cost 0", failed["cost"] == 0.0, failed["cost"]))

    # 3. Atomic concurrency: limit=5, fire 20 concurrent reservations → exactly 5 succeed
    period = "2026-06"
    res = await asyncio.gather(*[P._reserve_usage(TEST_FEATURE, "workspace", WS, period, 5) for _ in range(20)])
    granted = sum(1 for r in res if r)
    ok.append(("concurrency 20req limit5 => 5 granted", granted == 5, granted))

    # 4. Release restores capacity → one more can be granted
    await P._release_usage(TEST_FEATURE, "workspace", WS, period)
    again = await P._reserve_usage(TEST_FEATURE, "workspace", WS, period, 5)
    ok.append(("release frees 1 slot", again is True, again))

    # 5. Unlimited (limit=None) always grants
    g = await P._reserve_usage(TEST_FEATURE, "user", U, period, None)
    ok.append(("unlimited grants", g is True, g))

    # 6. Disabled (limit=0) never grants
    g0 = await P._reserve_usage(TEST_FEATURE, "event", EV, period, 0)
    ok.append(("disabled(limit0) blocks", g0 is False, g0))

    # 7. Override precedence: plan says unlimited, override user=1 monthly
    await set_feature(enforcement_enabled=True, scope="per_user", hard_behavior="block",
                      plan_limits={p: {"mode": "unlimited", "limit": None} for p in P.USAGE_PLANS})
    await P.db.usage_overrides.update_one(
        {"feature": TEST_FEATURE, "scope_type": "user", "scope_id": U},
        {"$set": {"id": "ov-test", "feature": TEST_FEATURE, "scope_type": "user", "scope_id": U,
                  "mode": "monthly", "limit": 1, "note": "", "created_at": P.now_iso()}}, upsert=True)
    fc = dict((await P.get_usage_config())["features"][TEST_FEATURE]); fc["_key"] = TEST_FEATURE
    lim, mode, isov = await P._resolve_feature_limit(fc, "pro", "user", U)
    ok.append(("override wins (limit1 monthly, is_override)", (lim == 1 and mode == "monthly" and isov), (lim, mode, isov)))

    # 8. Plan limit resolution when no override (different user)
    lim2, mode2, isov2 = await P._resolve_feature_limit(fc, "pro", "user", "other-user")
    ok.append(("plan unlimited no override", (lim2 is None and isov2 is False), (lim2, mode2, isov2)))

    # 9. Period key: stripe cycle vs calendar
    cal = P._calendar_period()
    ok.append(("calendar period YYYY-MM", len(cal) == 7 and cal[4] == "-", cal))

    await cleanup()
    print("\n==== USAGE ENGINE TEST RESULTS ====")
    allok = True
    for name, passed, val in ok:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}  -> {val}")
        allok = allok and passed
    print("==== " + ("ALL PASS" if allok else "SOME FAILED") + " ====")


asyncio.run(main())
