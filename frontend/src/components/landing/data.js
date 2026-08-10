import { Nfc, QrCode, Wallet, Users, BrainCircuit, LineChart, User, Globe, Link2, Activity } from "lucide-react";

export const ASSETS = {
  heroPortrait: "https://images.unsplash.com/photo-1770452603217-89b4f03e8271?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
  tplExecutive: "https://images.unsplash.com/photo-1764546899196-b53061b1b609?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
  tplBeige: "https://images.unsplash.com/photo-1604904612715-47bf9d9bc670?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
  tplFuture: "https://images.unsplash.com/photo-1767175620484-1ed37931a0d1?crop=entropy&cs=srgb&fm=jpg&q=85&w=600",
  avSarah: "https://images.unsplash.com/photo-1585240975858-7264fd020798?crop=entropy&cs=srgb&fm=jpg&q=85&w=200",
  avMichael: "https://images.unsplash.com/photo-1707068869917-6e5493b27932?crop=entropy&cs=srgb&fm=jpg&q=85&w=200",
  avEmma: "https://images.unsplash.com/photo-1616065297556-f05bc00c9a3e?crop=entropy&cs=srgb&fm=jpg&q=85&w=200",
  heroAmbient: "https://static.prod-images.emergentagent.com/jobs/b7cf9ea3-4027-4bce-9aa9-3953ffa20ee3/images/0e48d113ed564795ab7813ed3f5d9717b05dcac3136799779eb2a33381edd891.jpeg",
  goldWave: "https://static.prod-images.emergentagent.com/jobs/b7cf9ea3-4027-4bce-9aa9-3953ffa20ee3/images/c2d49071a63e17c592412093f1ad11619cd8a39544d0c3b3cff7c392e35c37d5.jpeg",
};

export const NAV_LINKS = [
  { label: "Product", to: "#connect" },
  { label: "Templates", to: "#templates" },
  { label: "Solutions", to: "#teams" },
  { label: "Resources", to: "#footer" },
  { label: "Pricing", to: "#pricing" },
  { label: "About", to: "#footer" },
];

export const STATS = [
  { icon: User, value: "50K+", label: "Professionals" },
  { icon: Globe, value: "150+", label: "Countries" },
  { icon: Link2, value: "1M+", label: "Connections" },
  { icon: Activity, value: "99.9%", label: "Uptime" },
];

export const FEATURES = [
  { icon: Nfc, title: "NFC Technology", desc: "Tap and share instantly with a single touch.", tint: "#F0CD84" },
  { icon: QrCode, title: "QR Code", desc: "Share your profile anytime, anywhere.", tint: "#D6A653" },
  { icon: Wallet, title: "Apple & Google Wallet", desc: "Add your card to wallet and stay connected.", tint: "#D6A653" },
  { icon: Users, title: "Smart Contact Exchange", desc: "Exchange contacts seamlessly and digitally.", tint: "#D6A653" },
  { icon: BrainCircuit, title: "AI Follow-Up", desc: "AI writes follow-ups. You close the deal.", tint: "#9C7BFF" },
  { icon: LineChart, title: "Analytics", desc: "Track views, saves and engagement.", tint: "#5FB4FF" },
];

export const JOURNEY = [
  { n: 1, title: "Tap", desc: "They tap your NFC card or scan QR.", kind: "card" },
  { n: 2, title: "Your Profile", desc: "They see your digital identity instantly.", kind: "profile" },
  { n: 3, title: "Exchange", desc: "They save your contact in one tap.", kind: "contacts" },
  { n: 4, title: "AI Follow-Up", desc: "AI suggests the perfect follow-up message.", kind: "ai" },
  { n: 5, title: "Stronger Relationships", desc: "You build stronger relationships and grow your network.", kind: "chart" },
];

export const TEMPLATES = [
  { name: "Executive Black Gold", person: "Alex Morgan", role: "CEO & Founder", img: ASSETS.tplExecutive,
    theme: { bg: "linear-gradient(180deg,#111112,#000)", accent: "#D6A653", text: "#F5EFE3", border: "rgba(214,166,83,0.4)" } },
  { name: "Beige Luxury", person: "Sophia Bennett", role: "Marketing Director", img: ASSETS.tplBeige,
    theme: { bg: "linear-gradient(180deg,#efe7da,#e6dcc9)", accent: "#B08A4A", text: "#4a3f2f", border: "rgba(176,138,74,0.4)" } },
  { name: "Future Professional", person: "Daniel Quinn", role: "Product Designer", img: ASSETS.tplFuture,
    theme: { bg: "linear-gradient(180deg,#0b1830,#0a0f1f)", accent: "#6EA8FF", text: "#dbe6f7", border: "rgba(110,168,255,0.4)" } },
];

export const TESTIMONIALS = [
  { quote: "TapPresence has completely changed how we network. It's professional, modern and incredibly powerful.",
    name: "Sarah Johnson", role: "Marketing Director", company: "Google", img: ASSETS.avSarah },
  { quote: "The NFC card quality is amazing and the AI follow-up saves us hours every week.",
    name: "Michael Chen", role: "CEO", company: "TechFlow", img: ASSETS.avMichael },
  { quote: "Finally, a digital business card that looks stunning and actually drives results.",
    name: "Emma Rodriguez", role: "Founder", company: "Edge Consulting", img: ASSETS.avEmma },
];

export const FOOTER_GROUPS = [
  { title: "Product", links: ["Features", "Templates", "Pricing", "Updates"] },
  { title: "Solutions", links: ["For Individuals", "For Teams", "For Enterprise", "Industries"] },
  { title: "Resources", links: ["Blog", "Help Center", "Guides", "API Docs"] },
  { title: "Company", links: ["About Us", "Careers", "Contact", "Privacy Policy"] },
];
