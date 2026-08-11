import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import PublicProfile from "@/pages/PublicProfile";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Admin from "@/pages/Admin";
import Home from "@/pages/Home";
import Settings from "@/pages/Settings";
import Team from "@/pages/Team";
import SuperAdmin from "@/pages/SuperAdmin";
import IndustryStudio from "@/pages/IndustryStudio";
import Signatures from "@/pages/Signatures";
import IntegrationHub from "@/pages/IntegrationHub";
import Leads from "@/pages/Leads";
import Landing from "@/pages/Landing";
import IndustryShowcase from "@/pages/IndustryShowcase";
import CreateCard from "@/pages/CreateCard";
import Billing from "@/pages/Billing";
import CommercialSettings from "@/pages/CommercialSettings";
import Referral from "@/pages/Referral";
import Meetings from "@/pages/Meetings";
import ManageMeeting from "@/pages/ManageMeeting";
import Activate from "@/pages/Activate";
import NfcCards from "@/pages/NfcCards";
import { ForgotPassword, ResetPassword, VerifyEmail } from "@/pages/AuthExtra";import Legal from "@/pages/Legal";
import ControlCenter from "@/pages/ControlCenter";
import { PaymentSuccess, PaymentCancel } from "@/pages/PaymentResult";
import GoogleFinish from "@/pages/GoogleFinish";
import LocaleToast from "@/components/LocaleToast";
import ConsentBanner from "@/components/ConsentBanner";
import PrivacyCenter from "@/pages/PrivacyCenter";
import { Loader2 } from "lucide-react";

function ProtectedRoute({ children }) {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050607]">
        <Loader2 className="w-6 h-6 animate-spin text-[#D6A653]" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

// SUPER_ADMIN-only routes (/control/*). Normal customers are redirected away.
function SuperAdminRoute({ children }) {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#050607]">
        <Loader2 className="w-6 h-6 animate-spin text-[#D6A653]" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "SUPER_ADMIN") return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/forgot" element={<ForgotPassword />} />
            <Route path="/reset" element={<ResetPassword />} />
            <Route path="/verify" element={<VerifyEmail />} />
            <Route path="/register" element={<Register />} />
            <Route path="/activate" element={<Activate />} />
            <Route path="/payment/success" element={<PaymentSuccess />} />
            <Route path="/payment/cancel" element={<PaymentCancel />} />
            <Route path="/auth/google/finish" element={<GoogleFinish />} />
            <Route path="/legal/:doc" element={<Legal />} />
            <Route path="/privacy-center" element={<PrivacyCenter />} />
            <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><Home /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="/nfc" element={<ProtectedRoute><NfcCards /></ProtectedRoute>} />
            <Route path="/team" element={<ProtectedRoute><Team /></ProtectedRoute>} />
            <Route path="/admin/platform" element={<Navigate to="/control" replace />} />
            <Route path="/control" element={<SuperAdminRoute><ControlCenter /></SuperAdminRoute>} />
            <Route path="/control/:section" element={<SuperAdminRoute><ControlCenter /></SuperAdminRoute>} />
            <Route path="/industry-studio" element={<ProtectedRoute><IndustryStudio /></ProtectedRoute>} />
            <Route path="/signatures" element={<ProtectedRoute><Signatures /></ProtectedRoute>} />
            <Route path="/integrations" element={<ProtectedRoute><IntegrationHub /></ProtectedRoute>} />
            <Route path="/leads" element={<ProtectedRoute><Leads /></ProtectedRoute>} />
            <Route path="/templates" element={<ProtectedRoute><CreateCard /></ProtectedRoute>} />
            <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
            <Route path="/referral" element={<ProtectedRoute><Referral /></ProtectedRoute>} />
            <Route path="/admin/commercial" element={<Navigate to="/control/plans" replace />} />
            <Route path="/meetings" element={<ProtectedRoute><Meetings /></ProtectedRoute>} />
            <Route path="/m/:token" element={<ManageMeeting />} />
            <Route path="/industries" element={<IndustryShowcase />} />
            <Route path="/:slug" element={<PublicProfile />} />
          </Routes>
          <ConsentBanner />
        </BrowserRouter>
        <Toaster position="top-center" />
        <LocaleToast />
      </AuthProvider>
    </div>
  );
}

export default App;
