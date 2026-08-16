import json, io
BASE = "/app/frontend/src/i18n/locales"
DATA = {
  "en": {"resume": "Resume subscription", "resumed": "Subscription resumed",
         "nextBilling": "Next billing date", "remainsActiveUntil": "Your {{plan}} plan remains active until",
         "billingCycle": "Billing cycle"},
  "ar": {"resume": "استئناف الاشتراك", "resumed": "تم استئناف الاشتراك",
         "nextBilling": "تاريخ الفوترة القادم", "remainsActiveUntil": "تظل خطة {{plan}} نشطة حتى",
         "billingCycle": "دورة الفوترة"},
  "es": {"resume": "Reanudar suscripción", "resumed": "Suscripción reanudada",
         "nextBilling": "Próxima fecha de facturación", "remainsActiveUntil": "Tu plan {{plan}} permanece activo hasta",
         "billingCycle": "Ciclo de facturación"},
}
for lang, keys in DATA.items():
    p = f"{BASE}/{lang}.json"
    d = json.load(io.open(p, encoding="utf-8"))
    d.setdefault("billing", {}).update(keys)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2); f.write("\n")
    print("updated", p)
