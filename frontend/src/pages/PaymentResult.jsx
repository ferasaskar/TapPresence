import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Loader2, CheckCircle2, XCircle, ArrowRight } from "lucide-react";

const Shell = ({ children }) => (
  <div className="aria-dark relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050607] px-6 py-16" style={{ fontFamily: "'Outfit', sans-serif" }}>
    <div className="grain-overlay" style={{ opacity: 0.05 }} />
    <div className="aria-gold-radial pointer-events-none absolute inset-0" />
    <div className="relative w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.04] p-8 text-center backdrop-blur-xl shadow-[0_30px_80px_rgba(0,0,0,0.6)]">
      <Link to="/" className="mb-6 flex items-center justify-center gap-2.5">
        <img src="/tp-mark.png" alt="TapPresence" className="h-9 w-9 object-contain" />
        <span className="text-lg font-semibold tracking-tight text-white">TapPresence</span>
      </Link>
      {children}
    </div>
  </div>
);

const POLL_MAX = 15;

export function PaymentSuccess() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refreshSession } = useAuth();
  const sessionId = params.get("session_id");
  const [state, setState] = useState("polling"); // polling | paid | pending | error
  const [plan, setPlan] = useState("");
  const tries = useRef(0);

  useEffect(() => {
    if (!sessionId) { setState("error"); return; }
    let stop = false;
    const poll = async () => {
      try {
        const { data } = await api.get(`/payments/status/${sessionId}`);
        if (stop) return;
        setPlan(data.plan || "");
        if (data.payment_status === "paid" || data.status === "completed") {
          setState("paid");
          await refreshSession();
          return;
        }
      } catch { /* keep polling */ }
      tries.current += 1;
      if (tries.current >= POLL_MAX) { setState("pending"); return; }
      if (!stop) setTimeout(poll, 2000);
    };
    poll();
    return () => { stop = true; };
    // eslint-disable-next-line
  }, [sessionId]);

  if (state === "error") {
    return (
      <Shell>
        <XCircle className="mx-auto h-12 w-12 text-red-400" data-testid="payment-error-icon" />
        <h1 className="mt-4 text-xl font-medium text-white">Something went wrong</h1>
        <p className="mt-2 text-sm text-white/55">We couldn't find your checkout session.</p>
        <button onClick={() => navigate("/billing")} data-testid="payment-back-billing" className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">Back to Billing <ArrowRight className="h-4 w-4" /></button>
      </Shell>
    );
  }

  if (state === "paid") {
    return (
      <Shell>
        <CheckCircle2 className="mx-auto h-12 w-12 text-[#D6A653]" data-testid="payment-success-icon" />
        <h1 className="mt-4 text-xl font-medium text-white" data-testid="payment-success-title">You're all set{plan ? ` on ${plan.charAt(0).toUpperCase() + plan.slice(1)}` : ""}</h1>
        <p className="mt-2 text-sm text-white/55">Your subscription is active. Thank you for choosing TapPresence.</p>
        <div className="mt-6 flex flex-col gap-2">
          <button onClick={() => navigate("/dashboard")} data-testid="payment-go-dashboard" className="inline-flex items-center justify-center gap-2 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">Go to dashboard <ArrowRight className="h-4 w-4" /></button>
          <button onClick={() => navigate("/billing")} data-testid="payment-view-billing" className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-white/80 hover:border-[#D6A653]/50">View billing</button>
        </div>
      </Shell>
    );
  }

  if (state === "pending") {
    return (
      <Shell>
        <Loader2 className="mx-auto h-10 w-10 animate-spin text-[#D6A653]" />
        <h1 className="mt-4 text-xl font-medium text-white">Finalising your subscription</h1>
        <p className="mt-2 text-sm text-white/55">Payment received — your plan will activate momentarily. You can safely head to your dashboard.</p>
        <button onClick={() => navigate("/dashboard")} data-testid="payment-go-dashboard" className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">Go to dashboard <ArrowRight className="h-4 w-4" /></button>
      </Shell>
    );
  }

  return (
    <Shell>
      <Loader2 className="mx-auto h-10 w-10 animate-spin text-[#D6A653]" data-testid="payment-polling" />
      <h1 className="mt-4 text-xl font-medium text-white">Confirming your payment…</h1>
      <p className="mt-2 text-sm text-white/55">This only takes a moment.</p>
    </Shell>
  );
}

export function PaymentCancel() {
  const navigate = useNavigate();
  return (
    <Shell>
      <XCircle className="mx-auto h-12 w-12 text-white/50" data-testid="payment-cancel-icon" />
      <h1 className="mt-4 text-xl font-medium text-white">Checkout cancelled</h1>
      <p className="mt-2 text-sm text-white/55">No charge was made. Your free trial is still active — you can upgrade anytime.</p>
      <div className="mt-6 flex flex-col gap-2">
        <button onClick={() => navigate("/billing")} data-testid="payment-retry" className="inline-flex items-center justify-center gap-2 rounded-full bg-[#D6A653] px-5 py-2.5 text-sm font-medium text-[#050607] hover:bg-[#E8B764]">Back to plans <ArrowRight className="h-4 w-4" /></button>
        <button onClick={() => navigate("/dashboard")} data-testid="payment-cancel-dashboard" className="rounded-full border border-white/15 px-5 py-2.5 text-sm text-white/80 hover:border-[#D6A653]/50">Go to dashboard</button>
      </div>
    </Shell>
  );
}
