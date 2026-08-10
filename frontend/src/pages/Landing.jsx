import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion, useScroll, useMotionValueEvent } from "framer-motion";
import { Sparkles, ArrowRight, Users, Nfc, PlayCircle, Star, BrainCircuit, LineChart, Linkedin, Twitter, Instagram, Apple, Play } from "lucide-react";
import "@/components/landing/landing.css";
import HeroVisual from "@/components/landing/HeroVisual";
import GoldWaveCanvas from "@/components/landing/GoldWaveCanvas";
import PricingSection from "@/components/landing/PricingSection";
import { NAV_LINKS, STATS, FEATURES, JOURNEY, TEMPLATES, TESTIMONIALS, FOOTER_GROUPS, ASSETS } from "@/components/landing/data";
import { useLocale } from "@/i18n/useLocale";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

const reveal = { hidden: { opacity: 0, y: 22 }, show: { opacity: 1, y: 0 } };
const Reveal = ({ children, delay = 0, className = "", ...rest }) => (
  <motion.div className={className} variants={reveal} initial="hidden" whileInView="show"
    viewport={{ once: true, amount: 0.2 }} transition={{ duration: 0.6, delay, ease: "easeOut" }} {...rest}>
    {children}
  </motion.div>
);

const AriadniMark = ({ className = "" }) => (
  <img src="/tp-mark.png" alt="TapPresence" className={`object-contain ${className}`} aria-hidden />
);

const goTo = (hash) => {
  const el = document.querySelector(hash);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
};

const Brand = ({ size = "text-xl" }) => (
  <span className={`flex items-center gap-2 ${size} font-semibold tracking-tight`} data-testid="brand">
    <AriadniMark className="h-6 w-6 text-[#D6A653]" />
    TapPresence
  </span>
);

/* ---------------------------------------------------------------- NAVBAR */
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const { t } = useLocale();
  const navLabels = t("landing.nav", { returnObjects: true });
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return (
    <motion.header initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
      className={`lp-nav sticky top-0 z-50 border-b ${scrolled ? "scrolled" : ""}`}>
      <div className="mx-auto flex h-[80px] max-w-[1320px] items-center justify-between px-5 sm:px-8 lg:px-12">
        <Brand />
        <nav className="hidden items-center gap-8 text-[15px] lg:flex">
          {NAV_LINKS.map((l, i) => (
            <button key={l.label} onClick={() => goTo(l.to)} className="lp-navlink" data-testid={`nav-${l.label.toLowerCase()}`}>{navLabels[i] || l.label}</button>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <Link to="/login" className="lp-navlink text-[15px]" data-testid="nav-login">{t("landing.login")}</Link>
          <Link to="/register" className="lp-btn-gold lp-press lp-sweep rounded-xl px-5 py-2.5 text-[14px]" data-testid="nav-register">{t("landing.createId")}</Link>
        </div>
      </div>
    </motion.header>
  );
}

/* ---------------------------------------------------------------- HERO */
function Hero() {
  const { t } = useLocale();
  return (
    <section className="relative overflow-hidden">
      <div className="mx-auto grid max-w-[1320px] grid-cols-1 items-center gap-10 px-5 pb-8 pt-14 sm:px-8 lg:grid-cols-[44%_56%] lg:gap-4 lg:px-12 lg:pt-20">
        <div className="max-w-[560px]">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }}
            className="inline-flex items-center gap-2 rounded-full border border-[#D6A653]/30 bg-[#0D1014] px-3.5 py-1.5" data-testid="hero-eyebrow">
            <Sparkles className="h-3.5 w-3.5 text-[#F0CD84]" />
            <span className="text-[12px] text-[#E6C787]">{t("landing.hero.badge")}</span>
          </motion.div>

          <motion.h1 initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-6 font-semibold tracking-[-0.03em] text-white"
            style={{ fontSize: "clamp(42px, 6vw, 70px)", lineHeight: 1.0 }} data-testid="hero-title">
            {t("landing.hero.title1")}<br />{t("landing.hero.title2")}<br /><span className="lp-shine">{t("landing.hero.title3")}</span>
          </motion.h1>

          <motion.p initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.32 }}
            className="mt-6 max-w-[540px] text-[18px] leading-relaxed text-[#A2A6AD]">
            {t("landing.hero.subtitle")}
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.42 }}
            className="mt-8 flex flex-wrap gap-3">
            <Link to="/register" className="lp-btn-gold lp-press lp-sweep inline-flex items-center gap-2 rounded-xl px-7 py-3.5 text-[15px]" data-testid="cta-create">
              {t("landing.hero.ctaCreate")} <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/register?intent=team" className="lp-btn-ghost lp-press inline-flex items-center gap-2 rounded-xl px-7 py-3.5 text-[15px]" data-testid="cta-team">
              <Users className="h-4 w-4 text-[#D6A653]" /> {t("landing.hero.ctaTeams")}
            </Link>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.54 }}
            className="mt-10 flex flex-wrap gap-x-10 gap-y-5" data-testid="hero-stats">
            {STATS.map((s, i) => (
              <div key={s.label} className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <s.icon className="h-3.5 w-3.5 text-[#D6A653]" strokeWidth={1.75} />
                  <span className="lp-gold-text text-2xl font-semibold tracking-tight">{s.value}</span>
                </div>
                <span className="mt-0.5 text-[12px] text-[#70757E]">{t("landing.stats", { returnObjects: true })[i] || s.label}</span>
              </div>
            ))}
          </motion.div>
        </div>

        <motion.div initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, delay: 0.5, ease: "easeOut" }}>
          <HeroVisual />
        </motion.div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- FEATURES */
function FeatureCard({ f, title, desc }) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const io = new IntersectionObserver((es) => { if (es[0].isIntersecting) { setInView(true); io.disconnect(); } }, { threshold: 0.4 });
    io.observe(el); return () => io.disconnect();
  }, []);
  const onMove = (e) => {
    const el = ref.current; if (!el || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width, py = (e.clientY - r.top) / r.height;
    el.style.setProperty("--ry", `${(px - 0.5) * 3}deg`);
    el.style.setProperty("--rx", `${(0.5 - py) * 3}deg`);
    el.style.setProperty("--ty", "-4px");
    el.style.setProperty("--mx", `${px * 100}%`);
    el.style.setProperty("--my", `${py * 100}%`);
  };
  const onLeave = () => {
    const el = ref.current; if (!el) return;
    el.style.setProperty("--rx", "0deg"); el.style.setProperty("--ry", "0deg"); el.style.setProperty("--ty", "0px");
  };
  return (
    <div ref={ref} onMouseMove={onMove} onMouseLeave={onLeave}
      className={`lp-card lp-tilt flex h-full min-h-[196px] flex-col items-center rounded-[18px] px-4 py-6 text-center ${inView ? "in-view" : ""}`}
      data-testid={`feature-${f.title.toLowerCase().replace(/\s+/g, "-").replace(/&/g, "and")}`}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10"
        style={{ background: "radial-gradient(120% 120% at 30% 20%, rgba(255,255,255,0.08), rgba(255,255,255,0.01))" }}>
        <f.icon className="h-5 w-5" style={{ color: f.tint, filter: inView ? `drop-shadow(0 0 8px ${f.tint}66)` : "none" }} strokeWidth={1.75} />
      </div>
      <h3 className="text-[15px] font-semibold text-white">{title || f.title}</h3>
      <p className="mt-2 text-[13px] leading-snug text-[#8A8F97]">{desc || f.desc}</p>
    </div>
  );
}

function ConnectionFeatures() {
  const { t } = useLocale();
  const items = t("landing.features", { returnObjects: true }) || [];
  return (
    <section id="connect" className="mx-auto max-w-[1320px] px-5 py-16 sm:px-8 lg:px-12 lg:py-24">
      <Reveal className="text-center">
        <h2 className="font-semibold tracking-tight text-white" style={{ fontSize: "clamp(26px,3.4vw,36px)" }}>
          {t("landing.featuresTitle")}
        </h2>
      </Reveal>
      <div className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6 lg:gap-4">
        {FEATURES.map((f, i) => (
          <Reveal key={f.title} delay={i * 0.05}>
            <FeatureCard f={f} title={items[i]?.title} desc={items[i]?.desc} />
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- JOURNEY */
const JourneyVisual = ({ kind }) => {
  const base = "flex h-full w-full items-center justify-center";
  if (kind === "card")
    return <div className={base}><div className="h-14 w-20 rounded-lg border border-[#D6A653]/40 bg-gradient-to-br from-[#17181b] to-black" style={{ boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.04)" }}><div className="mt-2 ml-2 h-4 w-4"><AriadniMark className="h-4 w-4 text-[#D6A653]" /></div></div></div>;
  if (kind === "profile")
    return <div className={base}><div className="flex flex-col items-center gap-1 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2"><div className="h-6 w-6 rounded-full bg-[#D6A653]/50" /><div className="h-1.5 w-10 rounded bg-white/25" /><div className="h-1 w-8 rounded bg-white/12" /></div></div>;
  if (kind === "contacts")
    return <div className={`${base} flex-col gap-1.5`}>{[0, 1, 2].map((r) => (<div key={r} className="flex items-center gap-2"><div className="h-4 w-4 rounded-full bg-[#D6A653]/45" /><div className="h-1.5 w-12 rounded bg-white/20" /></div>))}</div>;
  if (kind === "ai")
    return <div className={base}><BrainCircuit className="h-10 w-10 text-[#9C7BFF]" strokeWidth={1.4} style={{ filter: "drop-shadow(0 0 14px rgba(122,85,255,0.6))" }} /></div>;
  return <div className={`${base} items-end gap-1 px-3 pb-3`}>{[24, 34, 46, 60].map((h, i) => (<div key={i} className="w-3 rounded-t bg-gradient-to-t from-[#5FB4FF]/40 to-[#5FB4FF]" style={{ height: h }} />))}</div>;
};

function JourneyFlow() {
  const ref = useRef(null);
  const [p, setP] = useState(0);
  const { t } = useLocale();
  const steps = t("landing.journey.steps", { returnObjects: true }) || [];
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 78%", "end 60%"] });
  useMotionValueEvent(scrollYProgress, "change", (v) => setP(Math.min(1, Math.max(0, v))));
  const n = JOURNEY.length;
  const activeIdx = Math.min(n - 1, Math.floor(p * n));
  const stateOf = (i) => (i < activeIdx ? "done" : i === activeIdx ? "active" : "dim");

  return (
    <section ref={ref} className="mx-auto max-w-[1320px] px-5 py-16 sm:px-8 lg:px-12 lg:py-24">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[24%_76%] lg:gap-8">
        <Reveal>
          <p className="lp-eyebrow text-[12px]">{t("landing.journey.eyebrow")}</p>
          <h2 className="mt-3 font-semibold tracking-tight text-white" style={{ fontSize: "clamp(26px,3.2vw,34px)", lineHeight: 1.1 }}>
            {t("landing.journey.title1")}<br />{t("landing.journey.title2")}
          </h2>
          <p className="mt-4 text-[15px] leading-relaxed text-[#8A8F97]">
            {t("landing.journey.desc")}
          </p>
          <button onClick={() => goTo("#templates")} className="lp-btn-ghost lp-press mt-6 inline-flex items-center gap-2 rounded-xl px-5 py-3 text-[14px]" data-testid="journey-cta">
            <PlayCircle className="h-4 w-4 text-[#D6A653]" /> {t("landing.journey.cta")}
          </button>
        </Reveal>

        <div className="relative grid grid-cols-1 gap-9 lg:grid-cols-5 lg:gap-2">
          {/* connecting gold signal — desktop horizontal / mobile vertical */}
          <div className="lp-journey-track absolute left-[10%] right-[10%] top-[15px] hidden h-[2px] lg:block">
            <div className="lp-journey-fill" style={{ transform: `scaleX(${p})` }} />
          </div>
          <div className="lp-journey-track absolute left-[15px] top-4 bottom-4 block w-[2px] lg:hidden">
            <div className="lp-journey-fill" style={{ transformOrigin: "top center", transform: `scaleY(${p})`, background: "linear-gradient(180deg,#D6A653,#F0CD84 55%,#7A9BFF)" }} />
          </div>

          {JOURNEY.map((s, i) => (
            <div key={s.n} className={`lp-step relative z-10 flex items-start gap-4 text-left lg:flex-col lg:items-center lg:text-center ${stateOf(i)} ${s.kind === "ai" ? "ai" : ""}`}>
              <div className={`lp-node mb-0 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-[#050607] text-[13px] font-semibold lg:mb-3 ${s.kind === "ai" ? "border-[#7A55FF]/50 text-[#B9A3FF]" : "border-[#D6A653]/45 text-[#E6C787]"}`}>{s.n}</div>
              <div className="flex flex-col items-start lg:items-center">
                <div className="lp-step-visual lp-card flex h-[118px] w-[118px] items-center justify-center rounded-2xl" data-testid={`journey-step-${s.n}`}>
                  <JourneyVisual kind={s.kind} />
                </div>
                <div className="lp-step-copy">
                  <h3 className="mt-4 text-[15px] font-semibold text-white">{steps[i]?.title || s.title}</h3>
                  <p className="mt-1 max-w-[190px] text-[12.5px] leading-snug text-[#8A8F97] lg:max-w-[150px]">{steps[i]?.desc || s.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- TEMPLATES + APP */
const AppBadge = ({ icon: Icon, top, bottom }) => (
  <div className="lp-btn-ghost inline-flex items-center gap-2.5 rounded-xl px-4 py-2.5">
    <Icon className="h-5 w-5 text-white" />
    <span className="flex flex-col leading-tight text-left">
      <span className="text-[9px] text-[#9aa0a8]">{top}</span>
      <span className="text-[13px] font-semibold text-white">{bottom}</span>
    </span>
  </div>
);

function TemplateShowcase() {
  const { t } = useLocale();
  return (
    <section id="templates" className="mx-auto max-w-[1320px] px-5 py-8 sm:px-8 lg:px-12 lg:py-16">
      <Reveal>
        <div className="rounded-[24px] border border-white/8 bg-[#090B0E] p-6 sm:p-10">
          <div className="grid grid-cols-1 gap-10 lg:grid-cols-[26%_46%_28%] lg:gap-6">
            {/* left copy */}
            <div>
              <p className="lp-eyebrow text-[12px]">{t("landing.templates.eyebrow")}</p>
              <h2 className="mt-3 font-semibold tracking-tight text-white" style={{ fontSize: "clamp(24px,2.8vw,32px)", lineHeight: 1.12 }}>
                {t("landing.templates.title1")}<br />{t("landing.templates.title2")}
              </h2>
              <p className="mt-4 text-[15px] leading-relaxed text-[#8A8F97]">
                {t("landing.templates.desc")}
              </p>
              <Link to="/industries" className="lp-btn-ghost lp-press mt-6 inline-flex items-center gap-2 rounded-xl px-5 py-3 text-[14px]" data-testid="explore-templates">
                {t("landing.templates.cta")} <ArrowRight className="h-4 w-4 text-[#D6A653]" />
              </Link>
            </div>

            {/* center: 3 previews */}
            <div className="flex justify-center gap-3 overflow-x-auto lp-hide-scroll sm:gap-4">
              {TEMPLATES.map((t) => (
                <div key={t.name} className="flex shrink-0 flex-col items-center">
                  <div className="relative h-[300px] w-[158px] overflow-hidden rounded-[20px] border" style={{ background: t.theme.bg, borderColor: t.theme.border }} data-testid={`template-${t.name.toLowerCase().replace(/\s+/g, "-")}`}>
                    <div className="flex flex-col items-center px-3 pt-6">
                      <div className="h-16 w-16 overflow-hidden rounded-full ring-2" style={{ ["--tw-ring-color"]: t.theme.accent, boxShadow: `0 0 0 2px ${t.theme.accent}55` }}>
                        <img src={t.img} alt={t.person} className="h-full w-full object-cover" />
                      </div>
                      <p className="mt-3 text-[12px] font-semibold tracking-wide" style={{ color: t.theme.text }}>{t.person}</p>
                      <p className="text-[9px]" style={{ color: t.theme.accent }}>{t.role}</p>
                      <div className="mt-4 grid grid-cols-4 gap-1.5">
                        {[0, 1, 2, 3].map((k) => (
                          <div key={k} className="flex h-6 w-6 items-center justify-center rounded-full" style={{ background: `${t.theme.accent}22`, border: `1px solid ${t.theme.accent}55` }}>
                            <div className="h-2 w-2 rounded-full" style={{ background: t.theme.accent }} />
                          </div>
                        ))}
                      </div>
                      <div className="mt-4 h-6 w-full rounded-md" style={{ background: `${t.theme.accent}30`, border: `1px solid ${t.theme.accent}55` }} />
                    </div>
                  </div>
                  <span className="mt-3 text-[12px] text-[#9aa0a8]">{t.name}</span>
                </div>
              ))}
            </div>

            {/* right: app promo */}
            <div className="relative overflow-hidden">
              <span className="inline-block rounded-full border border-[#D6A653]/40 bg-[#0D1014] px-2.5 py-0.5 text-[10px] font-semibold tracking-wide text-[#E6C787]">{t("landing.templates.appNew")}</span>
              <h3 className="mt-3 text-[20px] font-semibold text-white">{t("landing.templates.appTitle")}</h3>
              <p className="mt-2 text-[14px] leading-relaxed text-[#8A8F97]">
                {t("landing.templates.appDesc")}
              </p>
              <div className="mt-5 flex flex-wrap gap-2.5">
                <AppBadge icon={Apple} top="Download on the" bottom="App Store" />
                <AppBadge icon={Play} top="GET IT ON" bottom="Google Play" />
              </div>
              <div className="pointer-events-none mt-6 hidden justify-end lg:flex">
                <div className="lp-phone h-[180px] w-[150px] translate-x-8 rounded-t-[28px] p-2">
                  <div className="h-full w-full overflow-hidden rounded-t-[22px] bg-[#0b0c0e] p-3">
                    <p className="text-[10px] text-neutral-400">Dashboard</p>
                    <p className="mt-1 lp-gold-text text-[18px] font-semibold">2,413</p>
                    <p className="text-[8px] text-neutral-500">Profile views</p>
                    <div className="mt-3 flex items-end gap-1">
                      {[16, 24, 20, 34, 28, 42].map((h, i) => <div key={i} className="w-2 rounded-t bg-[#5FB4FF]/70" style={{ height: h }} />)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

/* ---------------------------------------------------------------- TEAMS + TESTIMONIALS */
function TeamsTestimonials() {
  const { t } = useLocale();
  return (
    <section id="teams" className="mx-auto max-w-[1320px] px-5 py-8 sm:px-8 lg:px-12 lg:py-16">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[33%_67%]">
        <Reveal>
          <div className="lp-card flex h-full flex-col rounded-[22px] p-8">
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04]">
              <Users className="h-5 w-5 text-[#D6A653]" strokeWidth={1.6} />
            </div>
            <h3 className="text-[22px] font-semibold text-white">{t("landing.teams.title")}</h3>
            <p className="mt-3 text-[14px] leading-relaxed text-[#8A8F97]">
              {t("landing.teams.desc")}
            </p>
            <Link to="/register?intent=team" className="lp-btn-ghost lp-press mt-6 inline-flex w-fit items-center gap-2 rounded-xl px-5 py-3 text-[14px]" data-testid="teams-learn-more">
              {t("landing.teams.cta")} <ArrowRight className="h-4 w-4 text-[#D6A653]" />
            </Link>
          </div>
        </Reveal>

        <div>
          <Reveal>
            <h3 className="text-[22px] font-semibold text-white">{t("landing.teams.testimonialsTitle")}</h3>
          </Reveal>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {TESTIMONIALS.map((t, i) => (
              <Reveal key={t.name} delay={i * 0.07}>
                <div className="lp-card flex h-full flex-col rounded-[16px] p-5" data-testid={`testimonial-${i}`}>
                  <div className="flex gap-0.5">
                    {[0, 1, 2, 3, 4].map((s) => <Star key={s} className="h-3.5 w-3.5 fill-[#D6A653] text-[#D6A653]" />)}
                  </div>
                  <p className="mt-3 flex-1 text-[13.5px] leading-relaxed text-[#C7C9CD]">"{t.quote}"</p>
                  <div className="mt-4 flex items-center gap-3">
                    <img src={t.img} alt={t.name} className="h-9 w-9 rounded-full object-cover" />
                    <div>
                      <p className="text-[13px] font-semibold text-white">{t.name}</p>
                      <p className="text-[11px] text-[#8A8F97]">{t.role} · {t.company}</p>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- FINAL CTA */
function FinalCTA() {
  const { t } = useLocale();
  return (
    <section id="final-cta" className="relative overflow-hidden py-24">
      {/* beloved wave shape as a calm base, live particles animating on top */}
      <img src={ASSETS.goldWave} alt="" aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-[72%] w-full object-cover opacity-40 mix-blend-screen" style={{ transform: "scaleX(-1)" }} />
      <img src={ASSETS.goldWave} alt="" aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-[72%] w-full object-cover opacity-35 mix-blend-screen" />
      <GoldWaveCanvas variant="cta" className="pointer-events-none absolute inset-0 h-full w-full" />
      <Reveal className="relative z-10 mx-auto max-w-[1320px] px-5 text-center sm:px-8">
        <h2 className="mx-auto max-w-[720px] font-semibold tracking-tight text-white" style={{ fontSize: "clamp(28px,3.6vw,40px)", lineHeight: 1.1 }}>
          {t("landing.finalCta.title")}
        </h2>
        <p className="mx-auto mt-4 max-w-[520px] text-[15px] text-[#A2A6AD]">
          {t("landing.finalCta.subtitle")}
        </p>
        <Link to="/register" className="lp-btn-gold lp-press lp-sweep mt-8 inline-flex items-center gap-2 rounded-xl px-8 py-4 text-[15px]" data-testid="cta-final">
          {t("landing.finalCta.cta")} <ArrowRight className="h-4 w-4" />
        </Link>
      </Reveal>
    </section>
  );
}

/* ---------------------------------------------------------------- FOOTER */
function Footer() {
  const { t } = useLocale();
  const linkTarget = (label) => {
    if (label === "Privacy Policy") return "/legal/privacy";
    if (["For Teams", "For Enterprise", "For Individuals", "Industries"].includes(label)) return "/register?intent=team";
    if (["Features", "Templates", "Pricing", "Updates"].includes(label)) return "/register";
    return "/register";
  };
  return (
    <footer id="footer" className="border-t border-white/8 bg-[#070809] pb-10 pt-16">
      <div className="mx-auto grid max-w-[1320px] grid-cols-2 gap-8 px-5 sm:px-8 lg:grid-cols-6 lg:px-12">
        <div className="col-span-2">
          <Brand />
          <p className="mt-4 max-w-[240px] text-[13px] leading-relaxed text-[#70757E]">
            {t("landing.footer.tagline")}
          </p>
          <p className="mt-6 text-[12px] text-[#5b6068]">© {new Date().getFullYear()} TapPresence. {t("landing.footer.rights")}</p>
          <Link to="/privacy-center" data-testid="footer-privacy-choices" className="mt-2 inline-block text-[12px] text-[#8A8F97] underline underline-offset-2 transition-colors hover:text-white">{t("landing.footer.privacyChoices")}</Link>
        </div>
        {FOOTER_GROUPS.map((g) => (
          <div key={g.title}>
            <h4 className="text-[13px] font-semibold text-white">{g.title}</h4>
            <ul className="mt-4 space-y-2.5">
              {g.links.map((l) => (
                <li key={l}><Link to={linkTarget(l)} className="text-[13px] text-[#8A8F97] transition-colors hover:text-white">{l}</Link></li>
              ))}
            </ul>
          </div>
        ))}
        <div className="col-span-2 lg:col-span-1">
          <h4 className="text-[13px] font-semibold text-white">{t("landing.footer.stayConnected")}</h4>
          <p className="mt-4 text-[12px] text-[#8A8F97]">{t("landing.footer.newsletter")}</p>
          <form className="mt-3 flex items-center gap-2" onSubmit={(e) => e.preventDefault()}>
            <input type="email" placeholder={t("landing.footer.emailPlaceholder")} data-testid="footer-email"
              className="h-10 w-full rounded-lg border border-white/12 bg-[#0D1014] px-3 text-[13px] text-white placeholder:text-[#5b6068] focus:border-[#D6A653]/50 focus:outline-none" />
            <button type="submit" aria-label="Subscribe" className="lp-btn-gold flex h-10 w-11 shrink-0 items-center justify-center rounded-lg" data-testid="footer-subscribe">
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
          <div className="mt-4 flex items-center gap-3">
            {[Linkedin, Twitter, Instagram].map((Icon, i) => (
              <a key={i} href="#" className="flex h-8 w-8 items-center justify-center rounded-full border border-white/12 text-[#8A8F97] transition-colors hover:border-[#D6A653]/40 hover:text-[#D6A653]">
                <Icon className="h-3.5 w-3.5" />
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ---------------------------------------------------------------- PAGE */
export default function Landing() {
  return (
    <div className="lp-root min-h-screen">
      <Navbar />
      <Hero />
      <ConnectionFeatures />
      <JourneyFlow />
      <TemplateShowcase />
      <TeamsTestimonials />
      <PricingSection />
      <FinalCTA />
      <Footer />
    </div>
  );
}
