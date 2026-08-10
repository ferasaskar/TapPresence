import json, os
BASE = "/app/frontend/src/i18n/locales"

DATA = {
 "en": {
  "legal": {"privacyTitle":"Privacy Policy","termsTitle":"Terms of Service","notFound":"Not found",
    "placeholderBadge":"Placeholder — pending legal review","backHome":"Back to TapPresence",
    "privacyBody":"This is placeholder Privacy Policy content for TapPresence. Final approved legal language will be inserted here before commercial launch. It will describe what data we collect (profile info, leads you receive, analytics events), how it is used, retention periods, and your rights to export or delete your data.",
    "termsBody":"This is placeholder Terms of Service content for TapPresence. Final approved legal language will be inserted here before commercial launch. It will cover acceptable use, subscriptions and billing, NFC hardware, and account termination.",
    "sections":"Sections","dataRights":"Your data rights","dataRightsBody":"You can export or delete your account data at any time from Settings → Data & privacy."},
  "exchange": {"title":"Exchange Contact","detailsShared":"Details shared","willBeInTouch":"will be in touch. Save their contact below.","willBeInTouchGeneric":"They will be in touch. Save their contact below.",
    "saveContact":"Save {{name}}'s contact","saveContactGeneric":"Save contact","shareToConnect":"Share your details to connect.","shareToConnectWith":"Share your details to connect with {{name}}.",
    "fullName":"Your full name","email":"Email","phoneOptional":"Phone (optional)","messageOptional":"Message (optional)","cta":"Exchange Contact","required":"Name and email or phone required","failed":"Could not exchange"},
  "qr": {"scanToView":"Scan to view"},
  "share": {"whatsapp":"WhatsApp","email":"Email","shareCard":"Share","native":"Share","emailSubject":"Join me on TapPresence","emailBody":"Create your professional digital identity with TapPresence: {{url}}","cardEmailSubject":"My digital card","cardEmailBody":"Here is my TapPresence digital card: {{url}}","copied":"Link copied","cardShareText":"Check out my TapPresence card"},
  "dataRights": {"section":"Data & privacy","exportTitle":"Export my data","exportDesc":"Download a copy of your account, cards and leads as a JSON file.","exportBtn":"Export data","exporting":"Preparing…","exported":"Your data has been downloaded",
    "deleteTitle":"Delete my account","deleteDesc":"Permanently delete your account and the workspaces you own, including their cards, leads, analytics and notifications. Shared team data owned by others is preserved. This cannot be undone.",
    "deleteBtn":"Delete account","confirmTitle":"Delete your account?","confirmBody":"This permanently deletes your account and everything in the workspaces you own — cards, leads, analytics, meetings and notifications. Team data owned by other members is kept. This action cannot be undone.",
    "confirmPrompt":"Type DELETE to confirm","confirmWord":"DELETE","cancel":"Cancel","confirmBtn":"Delete permanently","deleting":"Deleting…","deleted":"Your account has been deleted","deleteFailed":"Could not delete account"}
 },
 "ar": {
  "legal": {"privacyTitle":"سياسة الخصوصية","termsTitle":"شروط الخدمة","notFound":"غير موجود",
    "placeholderBadge":"محتوى مؤقت — بانتظار المراجعة القانونية","backHome":"العودة إلى TapPresence",
    "privacyBody":"هذا محتوى مؤقت لسياسة الخصوصية الخاصة بـ TapPresence. سيتم إدراج الصياغة القانونية النهائية المعتمدة هنا قبل الإطلاق التجاري. وستوضح البيانات التي نجمعها (معلومات الملف، العملاء المحتملون، أحداث التحليلات)، وكيفية استخدامها، ومدد الاحتفاظ بها، وحقوقك في تصدير بياناتك أو حذفها.",
    "termsBody":"هذا محتوى مؤقت لشروط الخدمة الخاصة بـ TapPresence. سيتم إدراج الصياغة القانونية النهائية المعتمدة هنا قبل الإطلاق التجاري. وستغطي الاستخدام المقبول والاشتراكات والفوترة وأجهزة NFC وإنهاء الحساب.",
    "sections":"الأقسام","dataRights":"حقوقك في البيانات","dataRightsBody":"يمكنك تصدير أو حذف بيانات حسابك في أي وقت من الإعدادات ← البيانات والخصوصية."},
  "exchange": {"title":"تبادل جهة الاتصال","detailsShared":"تمت مشاركة التفاصيل","willBeInTouch":"سيتواصل معك. احفظ جهة الاتصال أدناه.","willBeInTouchGeneric":"سيتواصلون معك. احفظ جهة الاتصال أدناه.",
    "saveContact":"احفظ جهة اتصال {{name}}","saveContactGeneric":"حفظ جهة الاتصال","shareToConnect":"شارك بياناتك للتواصل.","shareToConnectWith":"شارك بياناتك للتواصل مع {{name}}.",
    "fullName":"اسمك الكامل","email":"البريد الإلكتروني","phoneOptional":"الهاتف (اختياري)","messageOptional":"رسالة (اختياري)","cta":"تبادل جهة الاتصال","required":"الاسم والبريد أو الهاتف مطلوب","failed":"تعذّر التبادل"},
  "qr": {"scanToView":"امسح للعرض"},
  "share": {"whatsapp":"واتساب","email":"البريد","shareCard":"مشاركة","native":"مشاركة","emailSubject":"انضم إليّ على TapPresence","emailBody":"أنشئ هويتك المهنية الرقمية مع TapPresence: {{url}}","cardEmailSubject":"بطاقتي الرقمية","cardEmailBody":"إليك بطاقتي الرقمية على TapPresence: {{url}}","copied":"تم نسخ الرابط","cardShareText":"اطّلع على بطاقتي على TapPresence"},
  "dataRights": {"section":"البيانات والخصوصية","exportTitle":"تصدير بياناتي","exportDesc":"نزّل نسخة من حسابك وبطاقاتك وعملائك المحتملين كملف JSON.","exportBtn":"تصدير البيانات","exporting":"جارٍ التحضير…","exported":"تم تنزيل بياناتك",
    "deleteTitle":"حذف حسابي","deleteDesc":"احذف حسابك ومساحات العمل التي تملكها نهائياً، بما في ذلك بطاقاتها وعملاؤها المحتملون وتحليلاتها وإشعاراتها. تُحفظ بيانات الفريق المملوكة للآخرين. لا يمكن التراجع عن هذا.",
    "deleteBtn":"حذف الحساب","confirmTitle":"حذف حسابك؟","confirmBody":"سيؤدي هذا إلى حذف حسابك نهائياً وكل ما في مساحات العمل التي تملكها — البطاقات والعملاء والتحليلات والاجتماعات والإشعارات. تُحفظ بيانات الفريق المملوكة لأعضاء آخرين. لا يمكن التراجع عن هذا الإجراء.",
    "confirmPrompt":"اكتب DELETE للتأكيد","confirmWord":"DELETE","cancel":"إلغاء","confirmBtn":"حذف نهائي","deleting":"جارٍ الحذف…","deleted":"تم حذف حسابك","deleteFailed":"تعذّر حذف الحساب"}
 },
 "es": {
  "legal": {"privacyTitle":"Política de privacidad","termsTitle":"Términos del servicio","notFound":"No encontrado",
    "placeholderBadge":"Contenido provisional — pendiente de revisión legal","backHome":"Volver a TapPresence",
    "privacyBody":"Este es contenido provisional de la Política de privacidad de TapPresence. El texto legal final aprobado se insertará aquí antes del lanzamiento comercial. Describirá qué datos recopilamos (información de perfil, contactos que recibes, eventos de analítica), cómo se usan, los plazos de retención y tus derechos a exportar o eliminar tus datos.",
    "termsBody":"Este es contenido provisional de los Términos del servicio de TapPresence. El texto legal final aprobado se insertará aquí antes del lanzamiento comercial. Cubrirá el uso aceptable, las suscripciones y facturación, el hardware NFC y la cancelación de la cuenta.",
    "sections":"Secciones","dataRights":"Tus derechos sobre los datos","dataRightsBody":"Puedes exportar o eliminar los datos de tu cuenta en cualquier momento desde Ajustes → Datos y privacidad."},
  "exchange": {"title":"Intercambiar contacto","detailsShared":"Datos compartidos","willBeInTouch":"se pondrá en contacto. Guarda su contacto abajo.","willBeInTouchGeneric":"Se pondrán en contacto. Guarda su contacto abajo.",
    "saveContact":"Guardar contacto de {{name}}","saveContactGeneric":"Guardar contacto","shareToConnect":"Comparte tus datos para conectar.","shareToConnectWith":"Comparte tus datos para conectar con {{name}}.",
    "fullName":"Tu nombre completo","email":"Correo","phoneOptional":"Teléfono (opcional)","messageOptional":"Mensaje (opcional)","cta":"Intercambiar contacto","required":"Se requiere nombre y correo o teléfono","failed":"No se pudo intercambiar"},
  "qr": {"scanToView":"Escanear para ver"},
  "share": {"whatsapp":"WhatsApp","email":"Correo","shareCard":"Compartir","native":"Compartir","emailSubject":"Únete a mí en TapPresence","emailBody":"Crea tu identidad profesional digital con TapPresence: {{url}}","cardEmailSubject":"Mi tarjeta digital","cardEmailBody":"Aquí está mi tarjeta digital de TapPresence: {{url}}","copied":"Enlace copiado","cardShareText":"Mira mi tarjeta de TapPresence"},
  "dataRights": {"section":"Datos y privacidad","exportTitle":"Exportar mis datos","exportDesc":"Descarga una copia de tu cuenta, tarjetas y contactos como archivo JSON.","exportBtn":"Exportar datos","exporting":"Preparando…","exported":"Tus datos se han descargado",
    "deleteTitle":"Eliminar mi cuenta","deleteDesc":"Elimina permanentemente tu cuenta y los espacios de trabajo que posees, incluidas sus tarjetas, contactos, analítica y notificaciones. Los datos de equipo de otros se conservan. Esto no se puede deshacer.",
    "deleteBtn":"Eliminar cuenta","confirmTitle":"¿Eliminar tu cuenta?","confirmBody":"Esto elimina permanentemente tu cuenta y todo lo que hay en los espacios que posees: tarjetas, contactos, analítica, reuniones y notificaciones. Se conservan los datos de equipo de otros miembros. Esta acción no se puede deshacer.",
    "confirmPrompt":"Escribe DELETE para confirmar","confirmWord":"DELETE","cancel":"Cancelar","confirmBtn":"Eliminar permanentemente","deleting":"Eliminando…","deleted":"Tu cuenta ha sido eliminada","deleteFailed":"No se pudo eliminar la cuenta"}
 }
}

for lang in ["en","ar","es"]:
    p = os.path.join(BASE, f"{lang}.json")
    d = json.load(open(p, encoding="utf-8"))
    for k, v in DATA[lang].items():
        d.setdefault(k, {})
        d[k].update(v)
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(p, "a").write("\n")
    print(lang, "ok")
