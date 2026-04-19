// calendar.jsx v2 — disabled/SOON placeholder
function CalendarScreen({ data, go }) {
  return (
    <main className="page" style={{background: "var(--chirri-paper)"}}>
      <section style={{maxWidth: 680, margin: "80px auto", textAlign: "center", padding: "48px 32px", background: "white", border: "2.5px solid var(--chirri-black)", borderRadius: 24, boxShadow: "5px 5px 0 var(--chirri-black)"}}>
        <div style={{fontSize: 80, marginBottom: 16}}>📅</div>
        <Pill color="yellow">PRÓXIMAMENTE</Pill>
        <h1 className="font-display" style={{fontSize: 72, lineHeight: 0.9, letterSpacing: "-0.03em", margin: "20px 0", textTransform: "lowercase"}}>
          cronograma<br/>de contenidos.
        </h1>
        <p style={{fontSize: 16, lineHeight: 1.5, fontWeight: 500, maxWidth: 480, margin: "0 auto"}}>
          Acá vas a poder ver y aprobar los posts que vienen en el feed de Instagram. Lo estamos cocinando — por ahora todo lo publicado vive en cada <b>reporte</b> de su etapa.
        </p>
        <button className="btn btn-primary" style={{marginTop: 28}} onClick={() => go({ screen: "home" })}>Volver a la home</button>
      </section>
    </main>
  );
}

window.CalendarScreen = CalendarScreen;
