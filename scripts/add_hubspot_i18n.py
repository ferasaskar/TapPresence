import json, io
BASE = "/app/frontend/src/i18n/locales"
DATA = {
  "en": {
    "hubspot": {
      "connected": "HubSpot connected", "connectFailed": "Couldn't connect HubSpot",
      "notAvailable": "HubSpot isn't available", "disconnected": "HubSpot disconnected",
      "couldNotDisconnect": "Something went wrong", "saved": "Saved",
      "statusConnected": "Connected", "reconnectNeeded": "Reconnect needed",
      "connectedDesc": "Connected to portal {{hub}}. Leads sync to your HubSpot CRM.",
      "disconnectedDesc": "Connect HubSpot to sync leads and deals into your CRM.",
      "autoSync": "Automatically sync leads to HubSpot",
      "connect": "Connect HubSpot", "reconnect": "Reconnect", "disconnect": "Disconnect",
      "synced": "Synced to HubSpot", "syncFailed": "HubSpot sync failed",
      "syncToHubspot": "Sync to HubSpot", "retrySync": "Retry sync",
      "lastSynced": "Last synced {{when}}",
      "state_synced": "Synced", "state_pending": "Pending", "state_failed": "Failed", "state_not_synced": "Not synced",
      "eventSyncSummary": "Synced {{synced}} · failed {{failed}} · skipped {{skipped}}"
    },
    "eventDash": {"exportCsv": "Export CSV", "syncHubspot": "Sync leads to HubSpot"}
  },
  "ar": {
    "hubspot": {
      "connected": "تم ربط HubSpot", "connectFailed": "تعذّر ربط HubSpot",
      "notAvailable": "HubSpot غير متاح", "disconnected": "تم فصل HubSpot",
      "couldNotDisconnect": "حدث خطأ ما", "saved": "تم الحفظ",
      "statusConnected": "متصل", "reconnectNeeded": "يلزم إعادة الربط",
      "connectedDesc": "متصل بالحساب {{hub}}. تتم مزامنة العملاء مع HubSpot.",
      "disconnectedDesc": "اربط HubSpot لمزامنة العملاء والصفقات مع نظام CRM.",
      "autoSync": "مزامنة العملاء تلقائيًا مع HubSpot",
      "connect": "ربط HubSpot", "reconnect": "إعادة الربط", "disconnect": "فصل",
      "synced": "تمت المزامنة مع HubSpot", "syncFailed": "فشلت مزامنة HubSpot",
      "syncToHubspot": "مزامنة إلى HubSpot", "retrySync": "إعادة المحاولة",
      "lastSynced": "آخر مزامنة {{when}}",
      "state_synced": "متزامن", "state_pending": "قيد الانتظار", "state_failed": "فشل", "state_not_synced": "غير متزامن",
      "eventSyncSummary": "تمت مزامنة {{synced}} · فشل {{failed}} · تم تخطي {{skipped}}"
    },
    "eventDash": {"exportCsv": "تصدير CSV", "syncHubspot": "مزامنة العملاء مع HubSpot"}
  },
  "es": {
    "hubspot": {
      "connected": "HubSpot conectado", "connectFailed": "No se pudo conectar HubSpot",
      "notAvailable": "HubSpot no está disponible", "disconnected": "HubSpot desconectado",
      "couldNotDisconnect": "Algo salió mal", "saved": "Guardado",
      "statusConnected": "Conectado", "reconnectNeeded": "Reconexión necesaria",
      "connectedDesc": "Conectado al portal {{hub}}. Los leads se sincronizan con HubSpot.",
      "disconnectedDesc": "Conecta HubSpot para sincronizar leads y negocios con tu CRM.",
      "autoSync": "Sincronizar leads automáticamente con HubSpot",
      "connect": "Conectar HubSpot", "reconnect": "Reconectar", "disconnect": "Desconectar",
      "synced": "Sincronizado con HubSpot", "syncFailed": "Falló la sincronización de HubSpot",
      "syncToHubspot": "Sincronizar con HubSpot", "retrySync": "Reintentar",
      "lastSynced": "Última sincronización {{when}}",
      "state_synced": "Sincronizado", "state_pending": "Pendiente", "state_failed": "Fallido", "state_not_synced": "Sin sincronizar",
      "eventSyncSummary": "Sincronizados {{synced}} · fallidos {{failed}} · omitidos {{skipped}}"
    },
    "eventDash": {"exportCsv": "Exportar CSV", "syncHubspot": "Sincronizar leads con HubSpot"}
  },
}
for lang, ns_map in DATA.items():
    p = f"{BASE}/{lang}.json"
    d = json.load(io.open(p, encoding="utf-8"))
    for ns, keys in ns_map.items():
        d.setdefault(ns, {})
        d[ns].update(keys)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2); f.write("\n")
    print("updated", p)
