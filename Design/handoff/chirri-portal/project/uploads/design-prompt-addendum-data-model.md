# Addendum al prompt de diseño — Modelo de datos y navegación

Este documento complementa `design-prompt.md`. Define la jerarquía de entidades del portal y las implicancias de navegación/UI que el diseño tiene que absorber. Leer los dos juntos.

## Jerarquía de entidades

```
Client (tenant, el que logea)
 └─ Brand (1..N)              # una marca del cliente
     └─ Campaign (1..N)       # tiene status: ACTIVE / FINISHED / PAUSED
         ├─ Stage (1..N)      # etapas narrativas de la campaña
         │   └─ Report (1..N) # reportes (mensuales, Q, finales)
         └─ NarrativeLine (0..N)   # líneas del brief, transversales a las etapas
```

Entidades satélite:

- `Influencer` (global, no por cliente) ↔ `CampaignInfluencer` (through: le asigna status MUST/ALT, línea narrativa, etapa, fee).
- `ScheduledPost` (cronograma IG/TikTok): cuelga de `Brand` y opcionalmente de `Campaign` / `Stage` / `CampaignInfluencer`.
- `ReportMetric`: dentro de `Report`, separada por red social y `source_type ∈ {organic, influencer, paid}` — la separación orgánico vs pauta vs influencer es estructural, no cosmética.

## Los dos casos que tenés que diseñar bien

### Caso A — Balanz (campaña one-off rica)

- 1 Client ("Balanz")
- 1 Brand ("Balanz")
- 1 Campaign activa ("De Ahorrista a Inversor")
- 4 Stages (Awareness → Educación → Validación → Conversión)
- 5 NarrativeLines
- ~20-30 Influencers asignados a líneas y etapas
- Reports mensuales dentro de la campaña

Acá la jerarquía **se ve** — la campaña tiene identidad, etapas con arco narrativo, influencers como elenco. Es el caso donde el portal cuenta una historia.

### Caso B — Plataforma Diez (marca con operación continua)

- 1 Client
- 1 Brand
- 1 Campaign implícita "Operación continua" con 1 Stage "Ongoing"
- Reports mensuales sin más estructura

Acá la jerarquía **se colapsa**. El cliente no debería ver las palabras "campaña" ni "etapa" — solo ve sus reportes mensuales. Es una marca con reportes, punto.

**Criterio de UX:** si una marca tiene una única campaña con una única etapa y esa etapa es "Ongoing", colapsá la jerarquía. Mostrá el historial de reportes directamente.

## Reglas de navegación y UI

1. **Auto-select de marca:** si el cliente tiene 1 sola Brand, no hay selector. Si tiene varias (caso hipotético — hoy ninguno), aparece un selector arriba.

2. **Auto-select de campaña:** si la Brand tiene 1 sola Campaign activa, no hay selector. Si tiene varias activas, selector con activas arriba y finished abajo.

3. **Auto-select de etapa:** si la Campaign tiene 1 sola Stage, no mostrar la etapa como dimensión en la UI.

4. **Historial de campañas:** campañas activas arriba, finished abajo con un corte visual claro. El cliente debe poder entrar a campañas terminadas para ver su reporte final o su evolución histórica.

5. **Un Report vive dentro de una Stage.** El breadcrumb natural es `Brand > Campaign > Stage > Report`. Cuando la jerarquía se colapsa (caso B), el breadcrumb se reduce a `Brand > Report`.

6. **Separación orgánico vs pauta vs influencer** no es una tab más — es la lente con la que se lee cada número. Pensalo como un eje visual permanente (color, icono, agrupamiento) en cualquier métrica que mostremos.

## Qué querés resolver con el diseño (además de lo del prompt original)

- **Cómo se ve la "Home" de un cliente** cuando la jerarquía está colapsada (P10) vs cuando no (Balanz). Dos layouts distintos o uno que se adapta.
- **Cómo se narra el arco de una campaña** en el detalle — las 4 etapas no son tabs, son un recorrido. ¿Scroll narrativo? ¿Timeline? ¿Capítulos?
- **Cómo se muestra una campaña finalizada** — ya no es "lo que viene", es "lo que pasó, y ahí quedó el mojón". Tono distinto al de una campaña activa.
- **Dónde viven los influencers en la UI** — ¿sección propia? ¿dentro de la etapa que les corresponde? ¿una vista "elenco" que atraviesa todas las etapas?
- **El cronograma de contenidos IG** (DEV-65) — ¿es una vista propia, o vive pegado al detalle de la campaña activa?

## Nota técnica para feasibility

- Backend Django 5 + DRF, frontend Next.js (App Router). Todo server-rendered o SSR donde convenga.
- Todas las entidades están scoped al `Client` del usuario autenticado. El diseño puede asumir que el dato está.
- Las métricas mezclan fuentes reales (Metricool, IG Graph API) con carga manual del equipo Chirri. Para el mock, asumí todo disponible.
