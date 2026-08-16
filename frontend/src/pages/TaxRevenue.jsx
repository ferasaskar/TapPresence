import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DateFilter, buildRange } from "@/components/admin/DateFilter";
import { Landmark, Loader2, Globe } from "lucide-react";

const tget = (params) => api.get("/admin/control/tax/overview", { params }).then((r) => r.data);
const money = (minor, cur) => {
  const v = (Number(minor || 0) / 100);
  try { return new Intl.NumberFormat(undefined, { style: "currency", currency: (cur || "USD").toUpperCase() }).format(v); }
  catch { return `${(cur || "").toUpperCase()} ${v.toFixed(2)}`; }
};
const STATUS_LABEL = {
  calculated: "Tax calculated", no_tax_due: "No tax due", location_required: "Location required",
  calculation_failed: "Calculation failed", unavailable: "Tax info unavailable",
};
const STATUS_STYLE = {
  calculated: "bg-emerald-500/12 text-emerald-300", no_tax_due: "bg-sky-500/12 text-sky-300",
  location_required: "bg-amber-500/12 text-amber-300", calculation_failed: "bg-red-500/12 text-red-300",
  unavailable: "bg-white/10 text-white/50",
};

const Panel = ({ title, children, testId, actions }) => (
  <div className="rounded-2xl border border-white/10 bg-[#0B0D12] p-5" data-testid={testId}>
    {(title || actions) && <div className="mb-4 flex items-center justify-between gap-2">{title ? <h3 className="text-sm font-medium text-white">{title}</h3> : <span />}{actions}</div>}
    {children}
  </div>
);
const Kpi = ({ label, value, sub, testId }) => (
  <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3" data-testid={testId}>
    <p className="text-[10px] uppercase tracking-wider text-white/40">{label}</p>
    <p className="mt-0.5 text-lg font-light tabular-nums text-white">{value}</p>
    {sub ? <p className="mt-0.5 text-[10px] text-white/40">{sub}</p> : null}
  </div>
);
const Pill = ({ s }) => <span className={`rounded-full px-2 py-0.5 text-[10px] ${STATUS_STYLE[s] || STATUS_STYLE.unavailable}`}>{STATUS_LABEL[s] || s}</span>;

export default function TaxRevenue() {
  const [range, setRange] = useState(() => buildRange("month"));
  const [d, setD] = useState(null);
  useEffect(() => { setD(null); tget({ start: range.start, end: range.end }).then(setD).catch(() => setD(null)); }, [range]);

  return (
    <div className="space-y-5" data-testid="ctrl-tax">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-light text-white"><Landmark className="h-5 w-5 text-[#D6A653]" /> Tax &amp; Global Revenue</h2>
          <p className="text-[11px] text-white/40">Stripe-authoritative. Collected tax is shown separately and is <span className="text-[#D6A653]/80">not</span> counted as TapPresence revenue. No cross-currency conversion.</p>
        </div>
        <DateFilter value={range} onChange={setRange} testId="tax-range" />
      </div>

      {!d ? <div className="flex justify-center py-16"><Loader2 className="h-5 w-5 animate-spin text-[#D6A653]" /></div> : (
        <>
          <Panel title="Overview" testId="tax-overview">
            <div className="mb-3 grid grid-cols-2 gap-2.5 lg:grid-cols-4">
              <Kpi label="Paying Customers" value={d.paying_customers} testId="tax-kpi-customers" />
              <Kpi label="Countries" value={d.country_count} sub={(d.countries || []).slice(0, 6).join(", ")} testId="tax-kpi-countries" />
              <Kpi label="Currencies" value={Object.keys(d.totals_by_currency || {}).length || 0} testId="tax-kpi-currencies" />
              <Kpi label="Transactions" value={(d.transactions || []).length} testId="tax-kpi-tx" />
            </div>
            {Object.keys(d.totals_by_currency || {}).length === 0 ? (
              <p className="py-6 text-center text-xs text-white/40" data-testid="tax-empty">No paid transactions in this period yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider text-white/40"><tr className="border-b border-white/8">
                    <th className="py-2 pr-3">Currency</th><th className="pr-3 text-right">Gross Subscription</th><th className="pr-3 text-right">Discounts</th>
                    <th className="pr-3 text-right">Net Subscription</th><th className="pr-3 text-right">Tax Collected</th><th className="pr-3 text-right">Total Charged</th>
                  </tr></thead>
                  <tbody className="text-white/80">
                    {Object.entries(d.totals_by_currency).map(([cur, v]) => (
                      <tr key={cur} className="border-b border-white/5" data-testid={`tax-cur-${cur}`}>
                        <td className="py-2 pr-3 text-white">{cur}</td>
                        <td className="pr-3 text-right tabular-nums">{money(v.base_subscription, cur)}</td>
                        <td className="pr-3 text-right tabular-nums text-white/50">−{money(v.discount, cur)}</td>
                        <td className="pr-3 text-right tabular-nums">{money(v.net_subscription, cur)}</td>
                        <td className="pr-3 text-right tabular-nums text-[#D6A653]">{money(v.tax_collected, cur)}</td>
                        <td className="pr-3 text-right tabular-nums">{money(v.total_charged, cur)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {Object.keys(d.tax_status_breakdown || {}).length ? (
              <div className="mt-3 flex flex-wrap gap-2" data-testid="tax-status-breakdown">
                {Object.entries(d.tax_status_breakdown).map(([s, n]) => (
                  <span key={s} className="flex items-center gap-1.5 text-[10px] text-white/50"><Pill s={s} /> × {n}</span>
                ))}
              </div>
            ) : null}
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Revenue by country" testId="tax-by-country">
              {(d.by_country || []).length === 0 ? <p className="py-6 text-center text-xs text-white/40">No data.</p> : (
                <div className="overflow-x-auto"><table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider text-white/40"><tr className="border-b border-white/8">
                    <th className="py-2 pr-3">Country</th><th className="pr-3 text-right">Customers</th><th className="pr-3 text-right">Net Rev</th><th className="pr-3 text-right">Tax</th>
                  </tr></thead>
                  <tbody className="text-white/80">{d.by_country.map((c, i) => (
                    <tr key={i} className="border-b border-white/5" data-testid={`tax-country-${c.country}`}>
                      <td className="py-2 pr-3 text-white"><Globe className="mr-1 inline h-3 w-3 text-white/30" />{c.country} <span className="text-white/40">{c.currency}</span></td>
                      <td className="pr-3 text-right tabular-nums">{c.customers}</td>
                      <td className="pr-3 text-right tabular-nums">{money(c.net_subscription, c.currency)}</td>
                      <td className="pr-3 text-right tabular-nums text-[#D6A653]">{money(c.tax_collected, c.currency)}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
              )}
            </Panel>
            <Panel title="US — by state" testId="tax-by-state">
              {(d.by_state_us || []).length === 0 ? <p className="py-6 text-center text-xs text-white/40" data-testid="tax-state-empty">No US state-level transactions in this period.</p> : (
                <div className="overflow-x-auto"><table className="w-full text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wider text-white/40"><tr className="border-b border-white/8">
                    <th className="py-2 pr-3">State</th><th className="pr-3 text-right">Total Charged</th><th className="pr-3 text-right">Tax Collected</th>
                  </tr></thead>
                  <tbody className="text-white/80">{d.by_state_us.map((s, i) => (
                    <tr key={i} className="border-b border-white/5" data-testid={`tax-state-${s.state}`}>
                      <td className="py-2 pr-3 text-white">{s.state} <span className="text-white/40">{s.currency}</span></td>
                      <td className="pr-3 text-right tabular-nums">{money(s.total_charged, s.currency)}</td>
                      <td className="pr-3 text-right tabular-nums text-[#D6A653]">{money(s.tax_collected, s.currency)}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
              )}
            </Panel>
          </div>

          <Panel title="Transactions" testId="tax-transactions">
            {(d.transactions || []).length === 0 ? <p className="py-6 text-center text-xs text-white/40">No transactions.</p> : (
              <div className="overflow-x-auto"><table className="w-full text-left text-xs">
                <thead className="text-[10px] uppercase tracking-wider text-white/40"><tr className="border-b border-white/8">
                  <th className="py-2 pr-3">Date</th><th className="pr-3">Country</th><th className="pr-3">Cur</th><th className="pr-3 text-right">Base</th>
                  <th className="pr-3 text-right">Disc</th><th className="pr-3 text-right">Tax</th><th className="pr-3 text-right">Total</th><th className="pr-3">Tax ID</th><th className="pr-3">Status</th>
                </tr></thead>
                <tbody className="text-white/80">{d.transactions.map((t, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td className="py-2 pr-3 text-white/60">{(t.created_at || "").slice(0, 10)}</td>
                    <td className="pr-3">{t.country || "—"}{t.state ? `/${t.state}` : ""}</td>
                    <td className="pr-3 text-white/50">{t.currency}</td>
                    <td className="pr-3 text-right tabular-nums">{money(t.base_amount, t.currency)}</td>
                    <td className="pr-3 text-right tabular-nums text-white/50">{money(t.discount_amount, t.currency)}</td>
                    <td className="pr-3 text-right tabular-nums text-[#D6A653]">{money(t.tax_amount, t.currency)}</td>
                    <td className="pr-3 text-right tabular-nums">{money(t.total_amount, t.currency)}</td>
                    <td className="pr-3 text-white/50">{t.tax_id_masked ? `${t.tax_id_type || ""} ${t.tax_id_masked}` : "—"}</td>
                    <td className="pr-3"><Pill s={t.tax_status} /></td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
