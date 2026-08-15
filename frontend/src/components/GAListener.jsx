import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { initGA, trackPageView } from "@/lib/ga";

// Initializes GA4 once and reports SPA page views on every route change.
export default function GAListener() {
  const { pathname } = useLocation();
  useEffect(() => { initGA(); }, []);
  useEffect(() => { trackPageView(pathname); }, [pathname]);
  return null;
}
