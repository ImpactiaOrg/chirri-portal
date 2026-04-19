// data.jsx v2 — campaigns + stages + reports jerárquicos

const CHIRRI_DATA = {
  client: {
    id: "balanz",
    name: "Balanz",
    initials: "Bz",
    monthShort: "03 · 2026"
  },
  user: {
    name: "Belén Rizzo",
    initials: "BR",
    role: "Brand Lead · Balanz",
    email: "belen.rizzo@balanz.com"
  },

  brand: { id: "balanz", name: "Balanz" },

  // Multiple campaigns — 1 activa + 2 terminadas
  campaigns: [
    {
      id: "ahorrista-inversor",
      name: "De Ahorrista a Inversor",
      status: "active",
      startDate: "Ene 2026",
      endDate: null,
      period: "Ene 2026 – presente",
      brief: "Acompañar al ahorrista argentino en su viaje a inversor. 4 actos: Awareness, Educación, Validación, Conversión.",
      totalReach: "8.1M",
      pieces: 35,
      influencers: 6,
      lastReportDate: "02 Abr 2026",
      nextReportDate: "02 May 2026",
      stages: ["awareness", "educacion", "validacion", "conversion"],
      heroColor: "var(--chirri-yellow)"
    },
    {
      id: "harry-potter-2025",
      name: "Harry Potter × Yelmo",
      status: "finished",
      startDate: "Oct 2025",
      endDate: "Feb 2026",
      period: "Oct 2025 – Feb 2026",
      brief: "Campaña cinematográfica alrededor del estreno. Cobranded con Yelmo cines.",
      totalReach: "12.3M",
      pieces: 48,
      influencers: 9,
      lastReportDate: "28 Feb 2026 · Cierre",
      stages: ["awareness-hp", "conversion-hp"],
      heroColor: "var(--chirri-pink)"
    },
    {
      id: "lanzamiento-app",
      name: "Lanzamiento App v2",
      status: "finished",
      startDate: "Jun 2025",
      endDate: "Sep 2025",
      period: "Jun – Sep 2025",
      brief: "Relanzamiento de la app con onboarding nuevo. Foco en descargas + primera inversión.",
      totalReach: "5.6M",
      pieces: 22,
      influencers: 4,
      lastReportDate: "15 Sep 2025 · Cierre",
      stages: ["conversion-app"],
      heroColor: "var(--chirri-mint)"
    }
  ],

  stages: {
    awareness: {
      id: "awareness", campaignId: "ahorrista-inversor",
      num: "01", name: "Awareness",
      desc: "Plantar la idea: 'hay un mundo más allá del plazo fijo'.",
      reach: "920K", pieces: 8, color: "organic",
      lead: "@nacho.elizalde", period: "Ene – Feb 2026",
      status: "finished"
    },
    educacion: {
      id: "educacion", campaignId: "ahorrista-inversor",
      num: "02", name: "Educación",
      desc: "Bajar tecnicismos. Traducir CEDEARs, Bonos, FCI a humano.",
      reach: "640K", pieces: 12, color: "organic",
      lead: "@martibenza", period: "Feb – Mar 2026",
      status: "active"
    },
    validacion: {
      id: "validacion", campaignId: "ahorrista-inversor",
      num: "03", name: "Validación",
      desc: "Testimonios reales. 'Yo tampoco sabía nada y empecé'.",
      reach: "780K", pieces: 9, color: "influencer",
      lead: "@sofi.gonet", period: "Mar – Abr 2026",
      status: "active"
    },
    conversion: {
      id: "conversion", campaignId: "ahorrista-inversor",
      num: "04", name: "Conversión",
      desc: "El call to action. Descargá la app. Empezá hoy.",
      reach: "500K", pieces: 6, color: "paid",
      lead: "@flor.sosa", period: "Abr – May 2026",
      status: "planned"
    }
  },

  // Reports indexed by stage — multiple types per stage
  reportsByStage: {
    awareness: [
      { id: "aw-feb-2026", type: "cierre", title: "Cierre de Awareness", period: "Feb 2026", publishedDate: "05 Mar 2026", author: "Vicky", reach: "920K", pieces: 8, status: "published" },
      { id: "aw-ene-2026", type: "general", title: "Reporte general · Enero", period: "Ene 2026", publishedDate: "02 Feb 2026", author: "Julián", reach: "480K", pieces: 4, status: "published" }
    ],
    educacion: [
      { id: "ed-mar-2026", type: "general", title: "Reporte general · Marzo", period: "Mar 2026", publishedDate: "02 Abr 2026", author: "Vicky", reach: "412K", pieces: 6, status: "published", featured: true },
      { id: "ed-mar-inf-2026", type: "influencers", title: "Reporte de influencers · Marzo", period: "Mar 2026", publishedDate: "02 Abr 2026", author: "Tati", reach: "228K", pieces: 3, status: "published" },
      { id: "ed-feb-2026", type: "general", title: "Reporte general · Febrero", period: "Feb 2026", publishedDate: "03 Mar 2026", author: "Julián", reach: "320K", pieces: 4, status: "published" }
    ],
    validacion: [
      { id: "va-mar-2026", type: "general", title: "Reporte general · Marzo", period: "Mar 2026", publishedDate: "02 Abr 2026", author: "Vicky", reach: "2.43M", pieces: 9, status: "published", featured: true, isLatest: true },
      { id: "va-mar-inf-2026", type: "influencers", title: "Reporte de influencers · Marzo", period: "Mar 2026", publishedDate: "02 Abr 2026", author: "Tati", reach: "2.1M", pieces: 5, status: "published" }
    ],
    conversion: [
      { id: "co-plan", type: "plan", title: "Plan de la etapa", period: "Abr – May", publishedDate: "28 Mar 2026", author: "Vicky", status: "draft" }
    ]
  },

  history: [
    { month: "Marzo", year: "2026", reach: "2.84M", delta: "+12%", stageId: "validacion", reportId: "va-mar-2026" },
    { month: "Febrero", year: "2026", reach: "2.53M", delta: "+8%", stageId: "validacion", reportId: "ed-feb-2026" },
    { month: "Enero", year: "2026", reach: "2.34M", delta: "+22%", stageId: "awareness", reportId: "aw-ene-2026" },
    { month: "Diciembre", year: "2025", reach: "1.91M", delta: "-4%", stageId: null, reportId: null },
    { month: "Noviembre", year: "2025", reach: "1.99M", delta: "+31%", stageId: null, reportId: null }
  ],

  kpis: [
    { label: "Total Reach", value: 2.84, unit: "M", delta: 12.4 },
    { label: "Organic Reach", value: 412, unit: "K", delta: 6.1 },
    { label: "Influencers Reach", value: 2.43, unit: "M", delta: 14.8 },
    { label: "Engagement", value: 4.8, unit: "%", delta: 0.3 },
    { label: "Seguidores +", value: "+18.4", unit: "K", delta: 24 }
  ],

  distribution: {
    instagram: { organic: 284000, paid: 512000, influencer: 1640000 },
    tiktok:    { organic: 98000, paid: 180000, influencer: 620000 },
    x:         { organic: 30000, paid: 42000, influencer: 170000 }
  },

  topOrganic: [
    { rank: 1, title: "Carrusel: 5 errores del ahorrista argentino", reach: "184K", saves: 8200, er: "7.2%", format: "carrusel" },
    { rank: 2, title: "Reel: Qué es un CEDEAR en 45 segundos", reach: "142K", saves: 6100, er: "6.4%", format: "reel" },
    { rank: 3, title: "Reel: 'Lo saqué del colchón'", reach: "98K", saves: 3400, er: "5.8%", format: "reel" }
  ],

  topInfluencers: [
    { rank: 1, handle: "@sofi.gonet", name: "Sofi Gonet", avatarColor: "#F478A8", initial: "S", followers: "1.1M", network: "IG", narrative: "Testimonios personales", reach: "980K", views: "1.2M", likes: "68K", comments: "4.2K", fee: "U$S 4.800", cpm: "U$S 4.0", stage: "validacion", caption: "\"Yo tampoco sabía nada\" — abrió con la historia de cómo empezó ella.", notes: "Pico de downloads esa noche.", posts: 2 },
    { rank: 2, handle: "@nacho.elizalde", name: "Nacho Elizalde", avatarColor: "#FFE74C", initial: "N", followers: "540K", network: "IG", narrative: "FOMO financiero", reach: "640K", views: "820K", likes: "41K", comments: "3.1K", fee: "U$S 2.900", cpm: "U$S 3.5", stage: "awareness", caption: "Humor + punzada: 'todos invierten menos yo'.", notes: "Reel con 18% de guardados.", posts: 3 },
    { rank: 3, handle: "@martibenza", name: "Marti Benza", avatarColor: "#00C9B7", initial: "M", followers: "1M", network: "IG", narrative: "Educación simple", reach: "510K", views: "680K", likes: "32K", comments: "1.8K", fee: "U$S 4.100", cpm: "U$S 6.0", stage: "educacion", caption: "Storytime: cómo armó su primer portfolio sin ser experta.", notes: "Audiencia femenina 25-34 respondió fuerte.", posts: 2 }
  ],

  pipeline: [
    { handle: "@flor.sosa", followers: "470K", narrative: "Lo saqué del colchón", status: "próximo mes" },
    { handle: "@coni_fach", followers: "290K", narrative: "Educación simple", status: "propuesta" },
    { handle: "@jazmin.bardach", followers: "340K", narrative: "Rol del asesor", status: "propuesta" }
  ],

  utm: [
    { handle: "@sofi.gonet", clicks: 14200, downloads: 2840, ctr: "2.4%", cvr: "20.0%" },
    { handle: "@nacho.elizalde", clicks: 9800, downloads: 1420, ctr: "1.9%", cvr: "14.5%" },
    { handle: "@martibenza", clicks: 8100, downloads: 1180, ctr: "1.9%", cvr: "14.6%" },
    { handle: "@flor.sosa", clicks: 4400, downloads: 620, ctr: "1.5%", cvr: "14.1%" }
  ],

  note: {
    body: "Marzo fue el mes donde la campaña dejó de ser un experimento y empezó a tener patrón. El carrusel de los 5 errores del ahorrista se volvió el contenido más guardado del trimestre (8.2K saves) — señal clarísima de que la audiencia está usando el feed como biblioteca, no como entretenimiento.",
    author: "Vicky, Julián y Tati — Chirri"
  }
};

window.CHIRRI_DATA = CHIRRI_DATA;
