"""Seed data for the ARIADNI ID demo profile (feras-askar)."""

DEMO_CARD = {
    "slug": "feras-askar",
    "templateId": "beige-luxury",
    "accent": "gold",
    "status": "published",
    "identity": {
        "fullName": "Feras Askar",
        "jobTitle": "Executive Real Estate Advisor",
        "company": "Askar Properties",
        "companyLogo": "",
        "profilePhoto": "https://images.unsplash.com/photo-1560250097-0b93528c311a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBleGVjdXRpdmUlMjBwb3J0cmFpdCUyMG1hbiUyMHN1aXQlMjBjYWxtfGVufDB8fHx8MTc4NjE5MTc4N3ww&ixlib=rb-4.1.0&q=85",
        "bio": "Curating exceptional residences and investment properties across the Emirates. Two decades of quiet, trusted advisory for a discerning clientele.",
        "city": "Dubai",
        "country": "United Arab Emirates",
        "availabilityBadge": "Available for Work",
    },
    "contact": {
        "phone": "+971501234567",
        "whatsapp": "+971501234567",
        "email": "feras@askarproperties.ae",
        "website": "https://askarproperties.ae",
        "address": "DIFC, Gate Village 4, Dubai, UAE",
        "mapsUrl": "https://maps.google.com/?q=DIFC+Dubai",
    },
    "social": {
        "linkedin": "https://linkedin.com/in/ferasaskar",
        "instagram": "https://instagram.com/ferasaskar",
        "x": "https://x.com/ferasaskar",
        "youtube": "",
        "tiktok": "",
    },
    "actions": ["message", "call", "whatsapp", "email", "meet", "book"],
    "services": [
        {"icon": "Building2", "title": "Luxury Residential", "description": "Handpicked penthouses, villas and waterfront homes matched to your lifestyle.", "ctaUrl": "", "order": 0, "enabled": True},
        {"icon": "TrendingUp", "title": "Investment Advisory", "description": "Data-led guidance on high-yield acquisitions and portfolio growth.", "ctaUrl": "", "order": 1, "enabled": True},
        {"icon": "KeyRound", "title": "Off-Market Access", "description": "Private listings and pre-launch opportunities reserved for select clients.", "ctaUrl": "", "order": 2, "enabled": True},
        {"icon": "Handshake", "title": "Concierge Closing", "description": "White-glove handling of legal, finance and handover from offer to keys.", "ctaUrl": "", "order": 3, "enabled": True},
    ],
    "projects": [
        {"coverImage": "https://images.unsplash.com/photo-1591931681345-16b532514cde?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzl8MHwxfHNlYXJjaHwzfHxsdXh1cnklMjBlZGl0b3JpYWwlMjBhcmNoaXRlY3R1cmUlMjBpbnRlcmlvcnxlbnwwfHx8fDE3ODYxOTE3ODd8MA&ixlib=rb-4.1.0&q=85", "name": "The Palm Signature Villa", "category": "Residential · Palm Jumeirah", "description": "AED 42M beachfront estate, sold in 11 days.", "url": "", "order": 0},
        {"coverImage": "https://images.unsplash.com/photo-1518733057094-95b53143d2a7?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzl8MHwxfHNlYXJjaHwyfHxsdXh1cnklMjBlZGl0b3JpYWwlMjBhcmNoaXRlY3R1cmUlMjBpbnRlcmlvcnxlbnwwfHx8fDE3ODYxOTE3ODd8MA&ixlib=rb-4.1.0&q=85", "name": "Downtown Sky Collection", "category": "Investment · Downtown Dubai", "description": "Full-floor acquisition, 9.4% projected yield.", "url": "", "order": 1},
        {"coverImage": "https://images.unsplash.com/photo-1599696848652-f0ff23bc911f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzl8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBlZGl0b3JpYWwlMjBhcmNoaXRlY3R1cmUlMjBpbnRlcmlvcnxlbnwwfHx8fDE3ODYxOTE3ODd8MA&ixlib=rb-4.1.0&q=85", "name": "Hills Grove Residences", "category": "Residential · Dubai Hills", "description": "Private garden mansion, off-market placement.", "url": "", "order": 2},
    ],
    "booking": {"bookingUrl": "https://cal.com/ferasaskar/consultation"},
}
