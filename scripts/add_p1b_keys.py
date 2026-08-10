import json, os
BASE = "/app/frontend/src/i18n/locales"

HOME = {
    "followUpToday": {"en": "Follow up today", "ar": "متابعة اليوم", "es": "Seguimiento de hoy"},
    "overdue":       {"en": "Overdue",         "ar": "متأخر",        "es": "Atrasado"},
    "dueToday":      {"en": "Due today",       "ar": "مستحق اليوم",  "es": "Para hoy"},
}
SCAN = {
    "eventRequired":       {"en": "Enter an event name or pick a campaign", "ar": "أدخل اسم فعالية أو اختر حملة", "es": "Escribe un evento o elige una campaña"},
    "eventModeOn":         {"en": "Event mode: {{event}} — every scan is tagged", "ar": "وضع الفعالية: {{event}} — كل مسح يُوسم", "es": "Modo evento: {{event}} — cada escaneo se etiqueta"},
    "switch":              {"en": "Switch",     "ar": "تبديل",   "es": "Cambiar"},
    "turnOff":             {"en": "Turn off",   "ar": "إيقاف",   "es": "Desactivar"},
    "eventModeTitle":      {"en": "Event capture mode", "ar": "وضع التقاط الفعالية", "es": "Modo captura de evento"},
    "eventNamePlaceholder":{"en": "Event name, e.g. GITEX 2026", "ar": "اسم الفعالية، مثل جيتكس 2026", "es": "Nombre del evento, p. ej. GITEX 2026"},
    "linkCampaign":        {"en": "Link a campaign (optional)", "ar": "ربط حملة (اختياري)", "es": "Vincular campaña (opcional)"},
    "noCampaign":          {"en": "No campaign", "ar": "بدون حملة", "es": "Sin campaña"},
    "startEventMode":      {"en": "Start",       "ar": "بدء",     "es": "Iniciar"},
    "cancel":              {"en": "Cancel",      "ar": "إلغاء",   "es": "Cancelar"},
    "enableEventMode":     {"en": "Enable event capture mode", "ar": "تفعيل وضع التقاط الفعالية", "es": "Activar modo captura de evento"},
    "willTag":             {"en": "Will be tagged to “{{event}}”", "ar": "سيتم وسمه بـ «{{event}}»", "es": "Se etiquetará como «{{event}}»"},
}
SIG = {"book": {"en": "Book meeting", "ar": "زر حجز اجتماع", "es": "Reservar reunión"}}

for lang in ("en", "ar", "es"):
    p = os.path.join(BASE, f"{lang}.json")
    d = json.load(open(p, encoding="utf-8"))
    d.setdefault("home", {}); d.setdefault("scan", {}); d.setdefault("signatures", {})
    for k, v in HOME.items(): d["home"][k] = v[lang]
    for k, v in SCAN.items(): d["scan"][k] = v[lang]
    for k, v in SIG.items(): d["signatures"][k] = v[lang]
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(lang, "home", len(d["home"]), "scan", len(d["scan"]), "sig", len(d["signatures"]))
