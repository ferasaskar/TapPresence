import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Eye, QrCode, MousePointerClick, Inbox, Loader2 } from "lucide-react";

const Stat = ({ icon: Icon, label, value, testId }) => (
  <div className="rounded-lg border border-neutral-200 p-4" data-testid={testId}>
    <Icon className="w-5 h-5 text-neutral-400 mb-3" />
    <p className="text-2xl font-semibold text-neutral-900">{value}</p>
    <p className="text-xs uppercase tracking-wide text-neutral-500">{label}</p>
  </div>
);

const KEY_LABELS = { call: "Call", whatsapp: "WhatsApp", email: "Email", meet: "Meet", message: "Message", book: "Book", save: "Save Contact", other: "Other" };

export default function AnalyticsDialog({ card, open, onOpenChange }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (open && card) {
      setData(null);
      api.get(`/admin/cards/${card.id}/analytics`).then((res) => setData(res.data));
    }
  }, [open, card]);

  const maxTap = data ? Math.max(1, ...Object.values(data.tapsByKey || {})) : 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="analytics-dialog">
        <DialogHeader>
          <DialogTitle>Analytics · {card?.identity?.fullName || card?.slug}</DialogTitle>
        </DialogHeader>
        {!data ? (
          <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div>
        ) : (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3">
              <Stat icon={Eye} label="Profile views" value={data.views} testId="stat-views" />
              <Stat icon={QrCode} label="QR scans" value={data.scans} testId="stat-scans" />
              <Stat icon={MousePointerClick} label="Action taps" value={data.taps} testId="stat-taps" />
              <Stat icon={Inbox} label="Inquiries" value={data.leads} testId="stat-leads" />
            </div>
            {Object.keys(data.tapsByKey || {}).length > 0 && (
              <div>
                <p className="mb-2 text-xs uppercase tracking-wide text-neutral-500">Taps by action</p>
                <div className="space-y-2">
                  {Object.entries(data.tapsByKey).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-3" data-testid={`tapkey-${k}`}>
                      <span className="w-24 text-sm text-neutral-600">{KEY_LABELS[k] || k}</span>
                      <div className="h-2 flex-1 rounded-full bg-neutral-100">
                        <div className="h-2 rounded-full bg-neutral-900" style={{ width: `${(v / maxTap) * 100}%` }} />
                      </div>
                      <span className="w-8 text-right text-sm text-neutral-500">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {data.views + data.scans === 0 ? (
              <p className="text-center text-sm text-neutral-400">No activity recorded yet. Share the profile to start collecting data.</p>
            ) : null}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
