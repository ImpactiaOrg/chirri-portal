# NOTAS DE DISEÑO — Portal Chirri (Claude)

## Sistema visual decidido (v1)

**Paleta (de chirripeppers.com):**
- Amarillo Chirri `#FFE74C` — background dominante en momentos-hero
- Rosa chicle `#FFB3D1` — acento alto contraste / estados activos
- Negro `#0A0A0A` — texto, cards, contraste fuerte
- Blanco roto `#FAF6EC` — background neutro de trabajo
- Verde picante `oklch(72% 0.18 145)` — positivos / orgánico
- Rojo picante `oklch(60% 0.22 25)` — pauta / paid
- Violeta `oklch(55% 0.18 300)` — influencers

**Tipografía:**
- Display: **Instrument Serif** (serif cursiva editorial, eco del logo chirri)
- UI/body: **Space Grotesk** (neutral, moderno, argentino feel)
- Data/números: **JetBrains Mono** (tabular numbers para KPIs)

**Principios:**
- Editorial-magazine, no dashboard SaaS
- Números XXL como protagonistas
- Separación cromática clara: orgánico (verde) / pauta (rojo) / influencer (violeta)
- Copy informal argentino con humor sutil
- El logo del cliente aparece sutil en el header; el portal es 100% Chirri

---

# Prompt para Claude Design — Portal Chirri

## Contexto

Chirri es una agencia argentina de redes sociales (Vicky, Julián y Tati) que maneja Instagram, TikTok y X para ~6 marcas: Plataforma Diez, First Rate, FW, Shellmo, Ultracom, Maria de Tommaso, y campañas one-off como Balanz. Hoy arman reportes mensuales en Canva a mano, cargando números desde Metricool y del panel de Instagram. Cada cliente pide un formato distinto, todo es manual, y el valor que agregan (separar orgánico de pauta, contextualizar los números, narrar la campaña) se pierde entre slides con screenshots de Metricool.

El portal que vamos a diseñar reemplaza ese ida y vuelta de PDFs por mail. Cada cliente entra con su login, ve sus reportes con la identidad visual de su marca, y puede revisar tanto **lo que viene** (contenido programado) como **lo que pasó** (métricas del mes).

## Quién lo usa

- **El cliente (ej: Belén, del equipo de Balanz)**: entra a ver su reporte del mes, baja PDF/Excel si lo necesita para presentar internamente, y mira qué posts vienen en el calendario. No es power user; quiere que la info hable por sí sola.
- **El equipo Chirri (Vicky, Julián, Tati)**: no usa esta UI para cargar datos — lo hacen desde Django Admin. Pero el portal **es su entregable**, es cómo firman su trabajo. Tiene que transmitir que alguien pensó el contenido, no que es un export automático.

## El caso ancla: Balanz — "De Ahorrista a Inversor"

Usen Balanz como el cliente de referencia para el diseño. Tagline: *"Es tiempo de invertir. Necesitás Balanz."* La campaña tiene 4 etapas narrativas (Awareness → Educación → Validación/Testimonios → Conversión) y trabaja con influencers reales, cada uno asignado a una línea narrativa del brief:

- *"Yo tampoco sabía nada"* (testimonios personales)
- *"FOMO financiero"* (todos invierten, menos yo)
- *"Lo saqué del colchón"* (humor + verdad argentina)
- *"Educación simple"* (cómo empezar sin ser experto)
- *"Rol del asesor"* (diferencial Balanz)

Influencers top: Sofi Gonet (1.1M IG), Nacho Elizalde (540K IG), Marti Benza (1M IG), Flor Sosa (470K IG). Alternativos: Coni Fach, Jazmin Bardach.

## Qué hay que diseñar

Estas son las vistas mínimas. La estructura interna es orientativa — **proponé lo que funcione mejor**, no copies slide por slide el reporte actual de Canva.

1. **Login**: email + password, identidad Chirri.
2. **Home del cliente**: historial de reportes mensuales, el último destacado. Pantalla de aterrizaje post-login. El logo del cliente (ej: Balanz) aparece sutilmente para que el usuario sepa que está en su espacio, pero el portal se siente Chirri.
3. **Detalle de reporte mensual** (la pieza principal). Tiene que contener:
   - KPIs del mes (Total Reach, Organic Reach, Influencers' Reach, ER, seguidores ganados) con delta vs mes anterior.
   - Comparativa trimestral (Q) cuando corresponda.
   - Por red social (IG, TikTok, X): crecimiento de seguidores, performance de posts/reels, **separación clara entre orgánico y contenido de influencers**.
   - Top contenidos: 3 mejores orgánicos + 3 mejores de influencers (con @handle, miniatura, métricas).
   - Tabla OneLink/UTM por influencer: clicks, descargas atribuidas.
   - Conclusiones (texto libre que escribe Chirri — la voz humana del reporte).
   - Acciones: **exportar reporte** (ver sección más abajo).
4. **Cronograma de contenidos IG**: los 3 posts que vienen en el mes (espaciados cada ~15 días). Cada post: miniatura, caption, fecha programada, estado (Borrador / Aprobado / Publicado). Es "lo que viene" — Belén quiere ver el plan antes de que salga.
5. **Export de reporte**: vista previa + descarga en PDF y Excel. **Acá sí hay un espacio interesante para branding del cliente** — el cliente lo baja para presentar internamente a sus jefes, entonces el PDF exportado idealmente lleva la identidad de la marca del cliente (logo grande, colores, tipografía), no la de Chirri. Chirri firma chiquito al pie ("Preparado por Chirri"). Es un switch consciente: **en pantalla el cliente ve el trabajo de Chirri; en el PDF que presenta internamente, ve su propia marca**. Proponé cómo tratar este momento — ¿vista previa del PDF con branding del cliente antes de descargar? ¿opción de elegir plantilla?
6. **Cualquier vista extra que consideres valiosa**: vista de campaña, detalle de influencer, lo que se te ocurra.

## Donde más quiero que propongas ideas piolas

No quiero un clon de Metricool ni un dashboard SaaS gris. Algunas líneas donde espero creatividad:

- **Hacer "viva" la distinción orgánico vs pauta vs influencer**. Es el mayor pain point de los datos (Metricool los mezcla y el cliente no distingue qué alcance fue plata puesta y qué fue laburo orgánico). Resolverlo visualmente es el principal valor del portal.
- **Narrar la campaña Balanz**. Las 4 etapas + líneas narrativas son un hilo conductor fuerte. ¿Timeline? ¿Mapa narrativo? ¿Cada influencer como un personaje que aporta a una etapa? Hay algo acá que no es un dashboard — es una historia.
- **Influencers como actores reales, no filas de tabla**. Hay data rica: followers, ER por red, fee, nicho, formato top, línea narrativa asignada, colaboraciones previas. Mostralos como humanos que están contando una historia, no como SKUs.
- **Que el cliente perciba el trabajo del equipo**. El portal no puede sentirse como un export automático. Tiene que transmitir criterio, curaduría, opinión. ¿Cómo? No sé, proponé.
- **Micro-interacciones, transiciones, momentos donde un número se vuelve contexto**. Si hubo un pico, ¿qué lo causó? Si un influencer rindió más, ¿por qué? El reporte tiene que responder preguntas, no mostrar tablas.

## Branding

**Dos universos de branding distintos, a propósito:**

1. **El portal en pantalla = Chirri**. El look & feel es 100% Chirri (voy a pasar aparte la presentación con el branding de Chirri — paleta, tipografías, recursos). El cliente entra a un espacio que claramente es "de Chirri", porque ese es el valor: están contratando a Chirri, no a un dashboard genérico. El único elemento de la marca del cliente en pantalla es su **logo** (ubicado de forma sutil para que el usuario se ubique en su tenant), nada de recolorear la UI.

2. **El PDF exportado = marca del cliente**. Cuando el cliente descarga el reporte para presentarlo internamente a su gente (CMO, directorio, etc.), lo necesita con la identidad de su propia marca. Ahí el PDF se viste con el logo + paleta + tipografía del cliente, y Chirri firma chiquito al pie.

Este split es intencional y es parte del valor: Chirri se luce en la relación con el cliente, y el cliente se luce puertas adentro.

## Tono

- **Chirri es una agencia joven, argentina, con onda**. Nada de "synergy" ni jerga SaaS. Premium pero con personalidad. La voz del equipo es directa, informal, con humor — ese tono tiene que colarse (por ejemplo, en copys de estados vacíos, en la manera de presentar conclusiones, en los micro-copies).

## Restricciones técnicas (para feasibility, no para limitar el diseño)

- Web, desktop-first pero responsive (el cliente va a revisar reportes en el celular también).
- Stack: Django 5 + DRF atrás, Next.js (App Router) adelante.
- Datos reales vendrán de API Metricool, Instagram Graph API, y carga manual complementaria. Para el mock asumí que los datos están disponibles.

## Entregable esperado

Propuesta de diseño cubriendo las vistas de arriba, con énfasis en el **detalle de reporte mensual** y el **cronograma de contenidos**. Si tenés 2-3 direcciones visuales distintas (ej: editorial magazine-style / data-viz moderno / playful argentino), mostralas — queremos ver dónde puede ir esto antes de cerrar una dirección.
