# Control Center — Metric Contract & Reconciliation (verified 2026-08-11, iteration_29)

TapPresence commercial model: **14-day Trial → Paid plans. There is NO Free plan.** The Control Center never displays "free" and never shows legacy "ARIADNI" branding.

## Exclusion mechanism
Explicit `environment` field on **users** and **workspaces**: `production_customer | internal | demo | test`.
- Stamped at registration (`production_customer`).
- Idempotent migration classifies existing records: `SUPER_ADMIN` role or `@ariadni.ai`/`@ariadni.id`/`@tappresence.com` → internal; `@demo.com`/`@example.com` → demo; `test…`/`+test` → test; else production_customer. Workspaces inherit their owner's environment.
- All KPIs DEFAULT to `production_customer` only. Super Admin can flip **"Include internal / test data"** (OFF by default) to reveal everything.

## Metric → definition → source → exclusions → verified result (customers-only, default)

### Users (distinct from customer accounts)
| Metric | Definition | Source | Result |
|---|---|---|---|
| Total Users | all user docs | `users` | 8 |
| Customer Users | environment=production_customer | `users` | 2 |
| Internal Users | total − customers (super admin + @ariadni.* + @demo.com) | `users` | 6 |

### Customer Accounts (workspaces; internal/demo/test excluded) — mutually exclusive, must reconcile
| Metric | Definition | Source | Result |
|---|---|---|---|
| Total Customer Accounts | workspaces environment=production_customer | `workspaces` | 2 |
| Individual | type=individual | `workspaces` | 2 |
| Company | type company/team AND plan≠enterprise | `workspaces` | 0 |
| Enterprise | plan=enterprise (own category) | `workspaces` | 0 |
| **Reconciliation** | total == individual+company+enterprise | | **2 = 2+0+0 ✓** |
| (include_internal=true) | adds internal TapPresence HQ (enterprise) | | total 3 |

### Subscriptions
| Metric | Definition | Source | Result |
|---|---|---|---|
| Active Trials | customer ws effective_status=trialing (trial_ends_at future) | `workspaces.subscription` | 2 (Mohammed & Loiy, trial→Aug 23) |
| Active Paid | real paid: status active/cancel_at_period_end AND paid tier AND has stripe_subscription_id/provider=stripe | `workspaces.subscription` | 0 (no Stripe) |
| Cancellations (period) | customer subs canceled within window | `workspaces` | 0 |

### Money — NOT available until Stripe connected
MRR / ARR / Revenue / Churn / Trial→Paid → source = real billing provider (Stripe) → **not connected → null / "Not available until Stripe is connected"**. Manually-seeded plan/status is NEVER counted as revenue (`is_real_paid()` requires a real Stripe reference).

### Product Usage (period-windowed, attributed to customer-owned cards only)
| Metric | Source (customer cards/ws only) | Customers-only | include_internal |
|---|---|---|---|
| Published Cards | digital_cards status=published | 2 | 3 |
| Card Views | analytics_events type=view | 47 | 225 |
| QR Scans | type=scan | 11 | 19 |
| NFC Taps | type=nfctap | 0 | 4 |
| Leads | leads.workspace_id ∈ customer ws | 0 | 0 |
| Meetings | meetings.card_id ∈ customer cards | 0 | 1 |
| Campaigns / Paid Referrals | campaigns / referrals in customer ws | 0 / 0 | 0 / 0 |

The difference between the two columns proves internal/demo data (feras-askar) is excluded by default.

## Date-filter semantics
- **Current-state metrics** (Customer Accounts total, Team Seats, Active Trials, Paid Subscribers): lifetime/current totals; Customer Accounts shows "+X in period".
- **Period metrics** (New Accounts, Cancellations, Card Views, QR, NFC, Leads, Scanner Uses, Meetings, Referrals): respond to Today/Week/Month/Custom.

## Legacy cleanup performed (idempotent migration)
- Legacy `plan="free"` production customers → migrated to intended 14-day **trial** subscription.
- Any stray `free` label → `trial` (free never surfaces).
- `ARIADNI HQ` → renamed `TapPresence HQ` (internal).
- Orphan/dangling cards (null/non-existent workspace_id, e.g. feras-askar) → attached to internal HQ (kept out of customer KPIs).
- Control Center header shows **"Super Admin"**, not the admin email.

## Backend helpers (platform_v1.py)
`customer_ws_filter(include_internal)`, `is_real_paid(sub)`, `display_plan(ws)`, `ROLE_LABELS`, `PUBLIC_PLANS`, `ENTITLEMENT_PROVIDER`. Endpoints all share the classifier: `/admin/control/overview`, `/subscriptions`, `/customers`, `/workspaces`, `/entitlements` (+ `/entitlements/preview`, PUT publish w/ audit).

## Cross-page reconciliation (verified iteration_30, all from environment=production_customer)
| Page | Source | Result |
|---|---|---|
| Overview → Customer Accounts | `/admin/control/overview` accounts.total | 2 |
| Customers | `/admin/control/customers` (owners of customer workspaces) | 2 (Loiy, Mohammed — role "Owner") |
| Workspaces breakdown | `/admin/control/workspaces` | 0 companies + 2 individuals = 2 |
| Subscriptions | `/admin/control/subscriptions` | trialing 2, active 0 |
| Plan distribution | `/admin/control/overview` | {trial: 2} |

All five reconcile. Customers shows customer ACCOUNTS only (team members appear inside a customer's detail, not as separate rows). Internal (TapPresence HQ, ariadni.ai team, admin) and test (demo.com) are excluded by default and only revealed via the "Include internal/test data" toggle. Product & Entitlements: plans = trial/pro/team/enterprise (no free/white_label), human labels, provider-not-connected badges (wallet & custom_domain unavailable), and a Draft→Preview→Confirm→Publish flow that writes an `admin.entitlements.publish` audit entry. Roles shown as human labels (Owner/Admin/Manager/Member/Super Admin). Mobile uses compact tap-to-open cards instead of desktop tables.
