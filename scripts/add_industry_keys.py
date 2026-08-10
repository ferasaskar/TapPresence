import json, os
BASE = "/app/frontend/src/i18n/locales"
# id: (label, role) per locale — company kept as brand proper-noun; person names kept as-is
IND = {
 "real_estate": {"en":["Real Estate","Real Estate Consultant"],"ar":["العقارات","مستشار عقاري"],"es":["Bienes raíces","Consultor inmobiliario"]},
 "business": {"en":["Business & Consulting","Business Consultant"],"ar":["الأعمال والاستشارات","مستشار أعمال"],"es":["Negocios y consultoría","Consultor de negocios"]},
 "sales": {"en":["Sales & Marketing","Marketing Strategist"],"ar":["المبيعات والتسويق","خبير استراتيجيات تسويق"],"es":["Ventas y marketing","Estratega de marketing"]},
 "technology": {"en":["Technology & AI","AI Solutions Architect"],"ar":["التقنية والذكاء الاصطناعي","مهندس حلول ذكاء اصطناعي"],"es":["Tecnología e IA","Arquitecto de soluciones de IA"]},
 "healthcare": {"en":["Healthcare","General Practitioner"],"ar":["الرعاية الصحية","طبيب عام"],"es":["Salud","Médico general"]},
 "legal": {"en":["Legal Services","Senior Attorney"],"ar":["الخدمات القانونية","محامٍ أول"],"es":["Servicios legales","Abogado sénior"]},
 "education": {"en":["Education & Training","Learning & Development Lead"],"ar":["التعليم والتدريب","مسؤول التعلم والتطوير"],"es":["Educación y formación","Líder de aprendizaje y desarrollo"]},
 "hospitality": {"en":["Hospitality","Hotel Manager"],"ar":["الضيافة","مدير فندق"],"es":["Hostelería","Gerente de hotel"]},
 "automotive": {"en":["Automotive","Automotive Specialist"],"ar":["السيارات","أخصائي سيارات"],"es":["Automoción","Especialista automotriz"]},
 "beauty": {"en":["Beauty & Wellness","Wellness Coach"],"ar":["الجمال والعافية","مدرب عافية"],"es":["Belleza y bienestar","Coach de bienestar"]},
 "finance": {"en":["Finance","Financial Advisor"],"ar":["التمويل","مستشار مالي"],"es":["Finanzas","Asesor financiero"]},
 "custom": {"en":["Custom Industry","Your Title"],"ar":["مجال مخصّص","مسمّاك الوظيفي"],"es":["Sector personalizado","Tu cargo"]},
}
for lang in ["en","ar","es"]:
    p = os.path.join(BASE, f"{lang}.json")
    d = json.load(open(p, encoding="utf-8"))
    d["industries"] = {iid: {"label": v[lang][0], "role": v[lang][1]} for iid, v in IND.items()}
    json.dump(d, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2); open(p,"a").write("\n")
    print(lang,"ok")
