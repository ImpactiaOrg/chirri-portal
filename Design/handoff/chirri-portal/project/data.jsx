// data.jsx — mocked data for Balanz, Marzo 2026

const CHIRRI_DATA = {
  client: {
    id: "balanz",
    name: "Balanz",
    initials: "Bz",
    tagline: "Es tiempo de invertir. Necesitás Balanz.",
    campaign: "De Ahorrista a Inversor",
    month: "Marzo 2026",
    monthShort: "03 · 2026",
    prevMonth: "Febrero 2026"
  },

  user: {
    name: "Belén Rizzo",
    initials: "BR",
    role: "Brand Lead · Balanz",
    email: "belen.rizzo@balanz.com"
  },

  // Historial de reportes para el home
  history: [
    { month: "Marzo", year: "2026", reach: "2.84M", delta: "+12%", status: "latest", slug: "marzo-2026" },
    { month: "Febrero", year: "2026", reach: "2.53M", delta: "+8%", status: "closed", slug: "febrero-2026" },
    { month: "Enero", year: "2026", reach: "2.34M", delta: "+22%", status: "closed", slug: "enero-2026" },
    { month: "Diciembre", year: "2025", reach: "1.91M", delta: "-4%", status: "closed", slug: "diciembre-2025" },
    { month: "Noviembre", year: "2025", reach: "1.99M", delta: "+31%", status: "closed", slug: "noviembre-2025" }
  ],

  // KPIs del mes con delta vs mes anterior
  kpis: [
    { label: "Total Reach", value: 2.84, unit: "M", delta: 12.4, raw: 2840000, ctx: "2do mes consecutivo sobre 2.5M. Etapa de Validación en plena tracción." },
    { label: "Organic Reach", value: 412, unit: "K", delta: 6.1, raw: 412000, ctx: "El feed orgánico sostiene. Reels de educación financiera hicieron picos el 11 y el 22." },
    { label: "Influencers Reach", value: 2.43, unit: "M", delta: 14.8, raw: 2430000, ctx: "Sofi Gonet con su post de testimonio llevó 980K reach solita." },
    { label: "Engagement", value: 4.8, unit: "%", delta: 0.3, raw: 0.048, ctx: "ER sano sobre 2M+ de reach. Comentarios auténticos en testimonios, no bot." },
    { label: "Seguidores +", value: "+18.4", unit: "K", delta: 24, raw: 18400, ctx: "Mayor pico de seguidores netos del Q1. Efecto FOMO financiero." }
  ],

  // Distribución orgánico / paid / influencer por red
  distribution: {
    instagram: { organic: 284000, paid: 512000, influencer: 1640000 },
    tiktok:    { organic: 98000, paid: 180000, influencer: 620000 },
    x:         { organic: 30000, paid: 42000, influencer: 170000 }
  },

  // 4 etapas narrativas de la campaña
  stages: [
    {
      id: "awareness",
      num: "01",
      name: "Awareness",
      pct: 34,
      color: "organic",
      desc: "Plantar la idea: 'hay un mundo más allá del plazo fijo'.",
      reach: "920K",
      pieces: 8,
      lead: "@sofi.gonet"
    },
    {
      id: "educacion",
      num: "02",
      name: "Educación",
      pct: 28,
      color: "organic",
      desc: "Bajar tecnicismos. Traducir CEDEARs, Bonos, FCI a humano.",
      reach: "640K",
      pieces: 12,
      lead: "@martibenza"
    },
    {
      id: "validacion",
      num: "03",
      name: "Validación",
      pct: 24,
      color: "influencer",
      desc: "Testimonios reales. 'Yo tampoco sabía nada y empecé'.",
      reach: "780K",
      pieces: 9,
      lead: "@nacho.elizalde"
    },
    {
      id: "conversion",
      num: "04",
      name: "Conversión",
      pct: 14,
      color: "paid",
      desc: "El call to action. Descargá la app. Empezá hoy.",
      reach: "500K",
      pieces: 6,
      lead: "@flor.sosa"
    }
  ],

  // Top contenidos orgánicos
  topOrganic: [
    { rank: 1, title: "Carrusel: 5 errores del ahorrista argentino", reach: "184K", saves: 8200, er: "7.2%", format: "carrusel" },
    { rank: 2, title: "Reel: Qué es un CEDEAR en 45 segundos", reach: "142K", saves: 6100, er: "6.4%", format: "reel" },
    { rank: 3, title: "Reel: 'Lo saqué del colchón'", reach: "98K", saves: 3400, er: "5.8%", format: "reel" }
  ],

  // Top contenidos influencers
  topInfluencers: [
    {
      rank: 1,
      handle: "@sofi.gonet",
      name: "Sofi Gonet",
      avatarColor: "#F478A8",
      initial: "S",
      followers: "1.1M",
      network: "IG",
      narrative: "Testimonios personales",
      reach: "980K",
      views: "1.2M",
      likes: "68K",
      comments: "4.2K",
      fee: "U$S 4.800",
      cpm: "U$S 4.0",
      stage: "validacion",
      caption: "\"Yo tampoco sabía nada\" — abrió con la historia de cómo empezó ella.",
      notes: "El comentario más repetido: 'gracias por hablar claro'. Pico de downloads esa noche.",
      posts: 2
    },
    {
      rank: 2,
      handle: "@nacho.elizalde",
      name: "Nacho Elizalde",
      avatarColor: "#FFE74C",
      initial: "N",
      followers: "540K",
      network: "IG",
      narrative: "FOMO financiero",
      reach: "640K",
      views: "820K",
      likes: "41K",
      comments: "3.1K",
      fee: "U$S 2.900",
      cpm: "U$S 3.5",
      stage: "awareness",
      caption: "Humor + punzada: 'todos invierten menos yo'. Lo bancó bien.",
      notes: "Reel con 18% de guardados — la gente volvió al post después.",
      posts: 3
    },
    {
      rank: 3,
      handle: "@martibenza",
      name: "Marti Benza",
      avatarColor: "#00C9B7",
      initial: "M",
      followers: "1M",
      network: "IG",
      narrative: "Educación simple",
      reach: "510K",
      views: "680K",
      likes: "32K",
      comments: "1.8K",
      fee: "U$S 4.100",
      cpm: "U$S 6.0",
      stage: "educacion",
      caption: "Storytime: cómo armó su primer portfolio sin ser experta.",
      notes: "Audiencia femenina 25-34 respondió fuerte. Buen match.",
      posts: 2
    }
  ],

  // Influencers alternativos / pipeline
  pipeline: [
    { handle: "@flor.sosa", followers: "470K", narrative: "Lo saqué del colchón", status: "próximo mes" },
    { handle: "@coni_fach", followers: "290K", narrative: "Educación simple", status: "propuesta" },
    { handle: "@jazmin.bardach", followers: "340K", narrative: "Rol del asesor", status: "propuesta" }
  ],

  // Tabla OneLink / UTM
  utm: [
    { handle: "@sofi.gonet", clicks: 14200, downloads: 2840, ctr: "2.4%", cvr: "20.0%" },
    { handle: "@nacho.elizalde", clicks: 9800, downloads: 1420, ctr: "1.9%", cvr: "14.5%" },
    { handle: "@martibenza", clicks: 8100, downloads: 1180, ctr: "1.9%", cvr: "14.6%" },
    { handle: "@flor.sosa", clicks: 4400, downloads: 620, ctr: "1.5%", cvr: "14.1%" }
  ],

  // Cronograma de contenidos (próximos IG)
  upcoming: [
    {
      id: 1,
      date: "06 Abril",
      time: "19:30",
      format: "Reel",
      status: "approved",
      caption: "El plazo fijo que te gana, pero cada vez menos. Capítulo 1 de la nueva serie educativa. 🎬",
      copy: "Abrimos Abril con una pregunta incómoda: ¿sabías que tu plazo fijo no te protegió de la inflación real el último año?",
      stage: "educacion",
      hashtags: "#BalanzApp #AhorroVsInversión"
    },
    {
      id: 2,
      date: "18 Abril",
      time: "20:00",
      format: "Carrusel",
      status: "draft",
      caption: "Las 3 preguntas que hacerle a un asesor financiero antes de confiarle un peso.",
      copy: "Vicky cerró el copy anoche — Julián sugirió un cambio en el slide 4. Lo miramos martes.",
      stage: "validacion",
      hashtags: "#AsesorFinanciero #BalanzAsesor"
    },
    {
      id: 3,
      date: "29 Abril",
      time: "18:00",
      format: "Reel",
      status: "draft",
      caption: "Cierre de mes con @flor.sosa: 'Lo saqué del colchón y no me morí en el intento'.",
      copy: "Grabación confirmada para el 22. Primera colaboración de Flor con la marca.",
      stage: "awareness",
      hashtags: "#BalanzApp"
    }
  ],

  // Nota editorial del equipo Chirri
  note: {
    body: "Marzo fue el mes donde la campaña dejó de ser un experimento y empezó a tener patrón. El carrusel de los 5 errores del ahorrista se volvió el contenido más guardado del trimestre (8.2K saves) — señal clarísima de que la audiencia está usando el feed como biblioteca, no como entretenimiento. Para abril: más contenido guardable, menos chistes de paso.",
    author: "Vicky, Julián y Tati — Chirri"
  }
};

window.CHIRRI_DATA = CHIRRI_DATA;
