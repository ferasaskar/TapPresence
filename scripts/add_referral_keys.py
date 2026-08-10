import json, os
BASE = "/app/frontend/src/i18n/locales"
DATA = {
 "en": {"referralProgram": {
   "tagline": "Invite {{count}}. Get {{months}} Month Free.",
   "taglineShort": "Invite {{count}}. Get 1 Month Free.",
   "subscribedOf": "{{qualified}} of {{per}} friends subscribed",
   "moreToUnlock": "{{remaining}} more paid referral to unlock your free month.",
   "moreToUnlock_plural": "{{remaining}} more paid referrals to unlock your free month.",
   "unlocked": "You unlocked {{count}} month free 🎉",
   "unlocked_plural": "You unlocked {{count}} months free 🎉",
   "nextReward": "Progress toward your next free month",
   "statTotal": "Total referrals", "statPaid": "Paid referrals", "statMonths": "Free months earned", "statProgress": "To next reward",
   "progressShort": "{{qualified}}/{{per}} to next free month",
   "monthsEarned": "{{count}} free month earned", "monthsEarned_plural": "{{count}} free months earned",
   "viewProgress": "View progress",
   "legendInvited": "Invited", "legendSignedUp": "Signed up", "legendPaid": "Paid & qualified", "legendReward": "Reward earned",
   "howTitle": "How it works",
   "how1": "Share your referral link or QR.",
   "how2": "Your friend signs up and subscribes to a paid plan.",
   "how3": "Every {{count}} paid friends earns you {{months}} month free.",
   "qualifiedNote": "Only friends who subscribe to a paid plan count toward your reward. Clicks, sign-ups and trials don't count.",
   "pendingNote": "{{count}} signed up — not subscribed yet",
   "signupDiscount": "New friends also get {{pct}}% off their first month."
 }},
 "ar": {"referralProgram": {
   "tagline": "ادعُ {{count}} واحصل على {{months}} شهر مجانًا.",
   "taglineShort": "ادعُ 5 أصدقاء واحصل على شهر مجانًا",
   "subscribedOf": "{{qualified}} من {{per}} أصدقاء اشتركوا",
   "moreToUnlock": "تبقّى {{remaining}} إحالة مدفوعة لفتح شهرك المجاني.",
   "moreToUnlock_plural": "تبقّى {{remaining}} إحالات مدفوعة لفتح شهرك المجاني.",
   "unlocked": "لقد حصلت على {{count}} شهر مجانًا 🎉",
   "unlocked_plural": "لقد حصلت على {{count}} أشهر مجانًا 🎉",
   "nextReward": "التقدّم نحو شهرك المجاني التالي",
   "statTotal": "إجمالي الإحالات", "statPaid": "الإحالات المدفوعة", "statMonths": "الأشهر المجانية المكتسبة", "statProgress": "نحو المكافأة التالية",
   "progressShort": "{{qualified}}/{{per}} نحو شهر مجاني",
   "monthsEarned": "{{count}} شهر مجاني مكتسب", "monthsEarned_plural": "{{count}} أشهر مجانية مكتسبة",
   "viewProgress": "عرض التقدّم",
   "legendInvited": "مدعو", "legendSignedUp": "سجّل", "legendPaid": "مدفوع ومؤهّل", "legendReward": "مكافأة مكتسبة",
   "howTitle": "كيف يعمل",
   "how1": "شارك رابط الإحالة أو رمز QR.",
   "how2": "يسجّل صديقك ويشترك في خطة مدفوعة.",
   "how3": "كل {{count}} أصدقاء مدفوعين يمنحك {{months}} شهر مجانًا.",
   "qualifiedNote": "تُحتسب فقط إحالات الأصدقاء الذين يشتركون في خطة مدفوعة. النقرات والتسجيلات والتجارب لا تُحتسب.",
   "pendingNote": "{{count}} سجّلوا — لم يشتركوا بعد",
   "signupDiscount": "يحصل الأصدقاء الجدد أيضًا على خصم {{pct}}٪ على شهرهم الأول."
 }},
 "es": {"referralProgram": {
   "tagline": "Invita a {{count}}. Consigue {{months}} mes gratis.",
   "taglineShort": "Invita a 5 amigos y obtén 1 mes gratis.",
   "subscribedOf": "{{qualified}} de {{per}} amigos suscritos",
   "moreToUnlock": "{{remaining}} referido de pago más para desbloquear tu mes gratis.",
   "moreToUnlock_plural": "{{remaining}} referidos de pago más para desbloquear tu mes gratis.",
   "unlocked": "Has desbloqueado {{count}} mes gratis 🎉",
   "unlocked_plural": "Has desbloqueado {{count}} meses gratis 🎉",
   "nextReward": "Progreso hacia tu próximo mes gratis",
   "statTotal": "Referidos totales", "statPaid": "Referidos de pago", "statMonths": "Meses gratis ganados", "statProgress": "Hacia la próxima recompensa",
   "progressShort": "{{qualified}}/{{per}} para un mes gratis",
   "monthsEarned": "{{count}} mes gratis ganado", "monthsEarned_plural": "{{count}} meses gratis ganados",
   "viewProgress": "Ver progreso",
   "legendInvited": "Invitado", "legendSignedUp": "Registrado", "legendPaid": "De pago y cualificado", "legendReward": "Recompensa ganada",
   "howTitle": "Cómo funciona",
   "how1": "Comparte tu enlace de referido o QR.",
   "how2": "Tu amigo se registra y se suscribe a un plan de pago.",
   "how3": "Cada {{count}} amigos de pago te dan {{months}} mes gratis.",
   "qualifiedNote": "Solo cuentan los amigos que se suscriben a un plan de pago. Los clics, registros y pruebas no cuentan.",
   "pendingNote": "{{count}} registrados — aún no suscritos",
   "signupDiscount": "Los nuevos amigos también obtienen un {{pct}}% de descuento en su primer mes."
 }}
}
for lang in ["en","ar","es"]:
    p = os.path.join(BASE, f"{lang}.json")
    d = json.load(open(p, encoding="utf-8"))
    d.update(DATA[lang])
    json.dump(d, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2); open(p,"a").write("\n")
    print(lang,"ok")
