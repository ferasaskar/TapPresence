import json, os
BASE = "/app/frontend/src/i18n/locales"

ANALYTICS = {
    "byChannel":  {"en": "Traffic by channel", "ar": "الزيارات حسب القناة", "es": "Tráfico por canal"},
    "direct":     {"en": "Direct / link",      "ar": "مباشر / رابط",        "es": "Directo / enlace"},
    "qr":         {"en": "QR",                 "ar": "QR",                  "es": "QR"},
    "nfc":        {"en": "NFC",                "ar": "NFC",                 "es": "NFC"},
    "scanner":    {"en": "Scanner leads",      "ar": "عملاء الماسح",        "es": "Leads del escáner"},
    "byCard":     {"en": "By card",            "ar": "حسب البطاقة",         "es": "Por tarjeta"},
    "views":      {"en": "Views",              "ar": "المشاهدات",           "es": "Vistas"},
    "leads":      {"en": "Leads",              "ar": "العملاء",             "es": "Leads"},
    "meetings":   {"en": "Meetings",           "ar": "الاجتماعات",          "es": "Reuniones"},
    "bySource":   {"en": "Leads by source",    "ar": "العملاء حسب المصدر",  "es": "Leads por origen"},
    "byEvent":    {"en": "Leads by event",     "ar": "العملاء حسب الفعالية","es": "Leads por evento"},
    "byCampaign": {"en": "Leads by campaign",  "ar": "العملاء حسب الحملة",  "es": "Leads por campaña"},
    "byMember":   {"en": "Captured by team member", "ar": "تم الالتقاط بواسطة عضو الفريق", "es": "Capturado por miembro del equipo"},
}
LEADS_SRC = {
    "source_inquiry":            {"en": "Inquiry",        "ar": "استفسار",          "es": "Consulta"},
    "source_meeting_booking":    {"en": "Meeting booking","ar": "حجز اجتماع",        "es": "Reserva de reunión"},
    "source_business_card_scan": {"en": "Business card",  "ar": "بطاقة عمل",         "es": "Tarjeta de visita"},
    "source_badge_scan":         {"en": "Event badge",    "ar": "شارة فعالية",       "es": "Credencial de evento"},
    "source_qr_scan":            {"en": "QR code",        "ar": "رمز QR",           "es": "Código QR"},
}
for lang in ("en", "ar", "es"):
    p = os.path.join(BASE, f"{lang}.json")
    d = json.load(open(p, encoding="utf-8"))
    d.setdefault("analytics", {})
    d.setdefault("leads", {})
    for k, v in ANALYTICS.items():
        d["analytics"][k] = v[lang]
    for k, v in LEADS_SRC.items():
        d["leads"][k] = v[lang]
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(lang, "analytics:", len(d["analytics"]), "leads:", len(d["leads"]))
