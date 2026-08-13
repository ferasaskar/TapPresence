import json, io

BASE = "/app/frontend/src/i18n/locales"

# nested additions per locale: {namespace: {key: value}}
DATA = {
  "en": {
    "leads": {
      "financials": "Deal & Revenue",
      "opportunityValue": "Opportunity Value",
      "currency": "Currency",
      "expectedClose": "Expected Close",
      "actualRevenue": "Actual Revenue",
      "revenueDate": "Revenue Date",
      "recordRevenue": "Record Revenue",
      "attributeTo": "Attribute revenue to",
      "noEventOrganic": "No event / Organic",
      "organic": "Organic",
      "other": "Other",
      "saveFinancials": "Save",
      "financialsSaved": "Financials saved",
      "clearValue": "Clear",
      "finNotSet": "Not set",
      "finAdminOnly": "Only owners and admins can edit financials.",
      "ev_opportunity_value_updated": "Opportunity value updated",
      "ev_opportunity_value_cleared": "Opportunity value cleared",
      "ev_revenue_recorded": "Revenue recorded",
      "ev_revenue_updated": "Revenue updated",
      "ev_revenue_cleared": "Revenue cleared",
      "ev_revenue_attribution_changed": "Revenue attribution changed"
    },
    "eventDash": {
      "pipelineValue": "Pipeline Value",
      "pipelineValueByStage": "Pipeline value by stage",
      "topOpportunities": "Top Opportunities",
      "revenueMultiple": "{{x}}x",
      "associatedNote": "Associated — a deal can appear in every event it touched. Revenue is attributed to one event only.",
      "openOpps": "{{count}} open",
      "excludedMismatch": "{{count}} excluded (currency mismatch)",
      "colPipeline": "Pipeline",
      "colRevenue": "Revenue",
      "expectedClose": "Expected close",
      "capturedBy": "Captured by",
      "financials": "Financial performance",
      "contact": "Contact",
      "company": "Company",
      "score": "Score",
      "stage": "Stage",
      "value": "Value"
    }
  },
  "ar": {
    "leads": {
      "financials": "الصفقة والإيرادات",
      "opportunityValue": "قيمة الفرصة",
      "currency": "العملة",
      "expectedClose": "الإغلاق المتوقع",
      "actualRevenue": "الإيرادات الفعلية",
      "revenueDate": "تاريخ الإيرادات",
      "recordRevenue": "تسجيل الإيرادات",
      "attributeTo": "نسب الإيرادات إلى",
      "noEventOrganic": "بدون فعالية / عضوي",
      "organic": "عضوي",
      "other": "أخرى",
      "saveFinancials": "حفظ",
      "financialsSaved": "تم حفظ البيانات المالية",
      "clearValue": "مسح",
      "finNotSet": "غير محدد",
      "finAdminOnly": "يمكن للمالكين والمشرفين فقط تعديل البيانات المالية.",
      "ev_opportunity_value_updated": "تم تحديث قيمة الفرصة",
      "ev_opportunity_value_cleared": "تم مسح قيمة الفرصة",
      "ev_revenue_recorded": "تم تسجيل الإيرادات",
      "ev_revenue_updated": "تم تحديث الإيرادات",
      "ev_revenue_cleared": "تم مسح الإيرادات",
      "ev_revenue_attribution_changed": "تم تغيير نسب الإيرادات"
    },
    "eventDash": {
      "pipelineValue": "قيمة الفرص",
      "pipelineValueByStage": "قيمة الفرص حسب المرحلة",
      "topOpportunities": "أهم الفرص",
      "revenueMultiple": "{{x}}x",
      "associatedNote": "منسوبة — قد تظهر الصفقة في كل فعالية شاركت فيها. تُنسب الإيرادات إلى فعالية واحدة فقط.",
      "openOpps": "{{count}} مفتوحة",
      "excludedMismatch": "{{count}} مستبعدة (اختلاف العملة)",
      "colPipeline": "الفرص",
      "colRevenue": "الإيرادات",
      "expectedClose": "الإغلاق المتوقع",
      "capturedBy": "تم الالتقاط بواسطة",
      "financials": "الأداء المالي",
      "contact": "جهة الاتصال",
      "company": "الشركة",
      "score": "النقاط",
      "stage": "المرحلة",
      "value": "القيمة"
    }
  },
  "es": {
    "leads": {
      "financials": "Trato e ingresos",
      "opportunityValue": "Valor de oportunidad",
      "currency": "Moneda",
      "expectedClose": "Cierre previsto",
      "actualRevenue": "Ingresos reales",
      "revenueDate": "Fecha de ingresos",
      "recordRevenue": "Registrar ingresos",
      "attributeTo": "Atribuir ingresos a",
      "noEventOrganic": "Sin evento / Orgánico",
      "organic": "Orgánico",
      "other": "Otro",
      "saveFinancials": "Guardar",
      "financialsSaved": "Finanzas guardadas",
      "clearValue": "Borrar",
      "finNotSet": "Sin definir",
      "finAdminOnly": "Solo propietarios y administradores pueden editar finanzas.",
      "ev_opportunity_value_updated": "Valor de oportunidad actualizado",
      "ev_opportunity_value_cleared": "Valor de oportunidad borrado",
      "ev_revenue_recorded": "Ingresos registrados",
      "ev_revenue_updated": "Ingresos actualizados",
      "ev_revenue_cleared": "Ingresos borrados",
      "ev_revenue_attribution_changed": "Atribución de ingresos cambiada"
    },
    "eventDash": {
      "pipelineValue": "Valor del pipeline",
      "pipelineValueByStage": "Valor del pipeline por etapa",
      "topOpportunities": "Principales oportunidades",
      "revenueMultiple": "{{x}}x",
      "associatedNote": "Asociado — un trato puede aparecer en cada evento que tocó. Los ingresos se atribuyen a un solo evento.",
      "openOpps": "{{count}} abiertas",
      "excludedMismatch": "{{count}} excluidas (moneda distinta)",
      "colPipeline": "Pipeline",
      "colRevenue": "Ingresos",
      "expectedClose": "Cierre previsto",
      "capturedBy": "Capturado por",
      "financials": "Rendimiento financiero",
      "contact": "Contacto",
      "company": "Empresa",
      "score": "Puntuación",
      "stage": "Etapa",
      "value": "Valor"
    }
  },
}

for lang, ns_map in DATA.items():
    path = f"{BASE}/{lang}.json"
    with io.open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    for ns, keys in ns_map.items():
        d.setdefault(ns, {})
        for k, v in keys.items():
            d[ns][k] = v
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"updated {path}")
