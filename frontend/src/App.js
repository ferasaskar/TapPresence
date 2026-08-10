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
import NfcCards from "@/pages/NfcCards";import Legal from "@/pages/Legal";
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

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/activate" element={<Activate />} />
            <Route path="/legal/:doc" element={<Legal />} />
            <Route path="/privacy-center" element={<PrivacyCenter />} />
            <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><Home /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
            <Route path="/nfc" element={<ProtectedRoute><NfcCards /></ProtectedRoute>} />
            <Route path="/team" element={<ProtectedRoute><Team /></ProtectedRoute>} />
            <Route path="/admin/platform" element={<ProtectedRoute><SuperAdmin /></ProtectedRoute>} />
            <Route path="/industry-studio" element={<ProtectedRoute><IndustryStudio /></ProtectedRoute>} />
            <Route path="/signatures" element={<ProtectedRoute><Signatures /></ProtectedRoute>} />
            <Route path="/integrations" element={<ProtectedRoute><IntegrationHub /></ProtectedRoute>} />
            <Route path="/leads" element={<ProtectedRoute><Leads /></ProtectedRoute>} />
            <Route path="/templates" element={<ProtectedRoute><CreateCard /></ProtectedRoute>} />
            <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
            <Route path="/referral" element={<ProtectedRoute><Referral /></ProtectedRoute>} />
            <Route path="/admin/commercial" element={<ProtectedRoute><CommercialSettings /></ProtectedRoute>} />
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
