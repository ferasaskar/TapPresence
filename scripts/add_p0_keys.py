import json, os

BASE = "/app/frontend/src/i18n/locales"

LEADS = {
    "stage_meeting":        {"en": "Meeting",        "ar": "اجتماع",          "es": "Reunión"},
    "stage_opportunity":    {"en": "Opportunity",    "ar": "فرصة",            "es": "Oportunidad"},
    "stage_customer":       {"en": "Customer",       "ar": "عميل",            "es": "Cliente"},
    "stage_not_interested": {"en": "Not Interested", "ar": "غير مهتم",         "es": "No interesado"},
    "bookMeeting":          {"en": "Book Meeting",   "ar": "حجز اجتماع",       "es": "Agendar reunión"},
    "remindMe":             {"en": "Remind Me",      "ar": "ذكّرني",           "es": "Recordarme"},
    "contactDetails":       {"en": "Contact details","ar": "تفاصيل جهة الاتصال","es": "Datos de contacto"},
    "company":              {"en": "Company",        "ar": "الشركة",           "es": "Empresa"},
    "jobTitle":             {"en": "Job title",      "ar": "المسمى الوظيفي",    "es": "Cargo"},
    "website":              {"en": "Website",        "ar": "الموقع الإلكتروني", "es": "Sitio web"},
    "event":                {"en": "Event",          "ar": "الفعالية",         "es": "Evento"},
    "eventPlaceholder":     {"en": "e.g. GITEX 2026","ar": "مثال: جيتكس 2026", "es": "p. ej. GITEX 2026"},
    "metAt":                {"en": "Met on",         "ar": "تاريخ اللقاء",      "es": "Conocido el"},
    "tags":                 {"en": "Tags",           "ar": "الوسوم",           "es": "Etiquetas"},
    "tagsPlaceholder":      {"en": "comma separated","ar": "مفصولة بفواصل",     "es": "separadas por comas"},
    "notes":                {"en": "Notes",          "ar": "ملاحظات",          "es": "Notas"},
    "saveDetails":          {"en": "Save details",   "ar": "حفظ التفاصيل",      "es": "Guardar datos"},
    "detailsSaved":         {"en": "Details saved",  "ar": "تم حفظ التفاصيل",   "es": "Datos guardados"},
    "followUpReminder":     {"en": "Follow-up reminder","ar": "تذكير بالمتابعة","es": "Recordatorio de seguimiento"},
    "reminderOn":           {"en": "Reminder set for {{when}}","ar": "تذكير في {{when}}","es": "Recordatorio para {{when}}"},
    "setReminder":          {"en": "Set reminder",   "ar": "ضبط التذكير",       "es": "Crear recordatorio"},
    "clearReminder":        {"en": "Clear",          "ar": "مسح",              "es": "Quitar"},
    "reminderSet":          {"en": "Reminder set",   "ar": "تم ضبط التذكير",    "es": "Recordatorio creado"},
    "reminderCleared":      {"en": "Reminder cleared","ar": "تم مسح التذكير",   "es": "Recordatorio eliminado"},
    "pickReminder":         {"en": "Pick a date and time","ar": "اختر التاريخ والوقت","es": "Elige fecha y hora"},
    "sourceBusinessCard":   {"en": "Business card",  "ar": "بطاقة عمل",         "es": "Tarjeta de visita"},
    "sourceBadge":          {"en": "Event badge",    "ar": "شارة فعالية",       "es": "Credencial de evento"},
    "sourceQr":             {"en": "QR code",        "ar": "رمز QR",           "es": "Código QR"},
}

SCAN = {
    "universalHint":  {"en": "Scan a business card, event badge, or contact QR code — QR codes are read instantly on your device.",
                       "ar": "امسح بطاقة عمل أو شارة فعالية أو رمز QR لجهة اتصال — تُقرأ رموز QR فوراً على جهازك.",
                       "es": "Escanea una tarjeta, credencial de evento o QR de contacto — los QR se leen al instante en tu dispositivo."},
    "qrRead":         {"en": "QR contact read", "ar": "تم قراءة جهة اتصال QR", "es": "Contacto QR leído"},
    "qrReviewIntro":  {"en": "We read this contact from the QR code. Review and edit before saving.",
                       "ar": "قرأنا جهة الاتصال هذه من رمز QR. راجع وعدّل قبل الحفظ.",
                       "es": "Leímos este contacto del código QR. Revisa y edita antes de guardar."},
}

NFC = {
    "title":              {"en": "NFC cards",        "ar": "بطاقات NFC",        "es": "Tarjetas NFC"},
    "subtitle":           {"en": "Choose which profile each tap opens.","ar": "اختر الملف الذي يفتحه كل نقر.","es": "Elige qué perfil abre cada toque."},
    "emptyTitle":         {"en": "No NFC cards yet", "ar": "لا توجد بطاقات NFC بعد","es": "Aún no hay tarjetas NFC"},
    "emptyDesc":          {"en": "When you activate an NFC card it will appear here, and you can change its destination anytime.",
                           "ar": "عند تفعيل بطاقة NFC ستظهر هنا، ويمكنك تغيير وجهتها في أي وقت.",
                           "es": "Cuando actives una tarjeta NFC aparecerá aquí y podrás cambiar su destino cuando quieras."},
    "destinationCard":    {"en": "Destination card", "ar": "بطاقة الوجهة",       "es": "Tarjeta de destino"},
    "chooseCard":         {"en": "Choose a card",    "ar": "اختر بطاقة",         "es": "Elige una tarjeta"},
    "routeHint":          {"en": "Every tap on this card will open the selected profile — no need to re-encode the chip.",
                           "ar": "كل نقرة على هذه البطاقة ستفتح الملف المحدد — دون الحاجة لإعادة برمجة الشريحة.",
                           "es": "Cada toque de esta tarjeta abrirá el perfil seleccionado — sin reprogramar el chip."},
    "destinationUpdated": {"en": "Destination updated","ar": "تم تحديث الوجهة",  "es": "Destino actualizado"},
    "updateFailed":       {"en": "Could not update", "ar": "تعذّر التحديث",      "es": "No se pudo actualizar"},
    "statusUpdated":      {"en": "Status updated",   "ar": "تم تحديث الحالة",    "es": "Estado actualizado"},
    "reactivate":         {"en": "Reactivate",       "ar": "إعادة تفعيل",        "es": "Reactivar"},
    "markLost":           {"en": "Mark as lost",     "ar": "وضع علامة مفقود",    "es": "Marcar como perdida"},
    "st_ACTIVE":          {"en": "Active",           "ar": "نشطة",              "es": "Activa"},
    "st_UNASSIGNED":      {"en": "Unassigned",       "ar": "غير معيّنة",         "es": "Sin asignar"},
    "st_DEACTIVATED":     {"en": "Deactivated",      "ar": "معطّلة",            "es": "Desactivada"},
    "st_LOST":            {"en": "Lost",             "ar": "مفقودة",            "es": "Perdida"},
    "st_REPLACED":        {"en": "Replaced",         "ar": "مستبدلة",           "es": "Reemplazada"},
}

for lang in ("en", "ar", "es"):
    path = os.path.join(BASE, f"{lang}.json")
    d = json.load(open(path, encoding="utf-8"))
    d.setdefault("leads", {})
    d.setdefault("scan", {})
    d.setdefault("nfc", {})
    for k, v in LEADS.items():
        d["leads"][k] = v[lang]
    for k, v in SCAN.items():
        d["scan"][k] = v[lang]
    for k, v in NFC.items():
        d["nfc"][k] = v[lang]
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(lang, "leads:", len(d["leads"]), "scan:", len(d["scan"]), "nfc:", len(d["nfc"]))

# sanity: key parity
counts = {}
for lang in ("en", "ar", "es"):
    d = json.load(open(os.path.join(BASE, f"{lang}.json"), encoding="utf-8"))
    total = sum(len(v) if isinstance(v, dict) else 1 for v in d.values())
    counts[lang] = total
print("total top-level key groups counts:", counts)
