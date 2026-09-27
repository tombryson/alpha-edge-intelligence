import './IntelligenceHome.css';

const CAPABILITIES = [
  {
    key: 'council',
    number: '01',
    title: 'Analyst Council',
    detail: 'Per-security research, model outputs, and durable run artefacts.',
    path: '/council',
  },
  {
    key: 'router',
    number: '02',
    title: 'Announcement Router',
    detail: 'Announcement evidence, scenario changes, and analyst review.',
    path: '/announcement-router',
  },
  {
    key: 'portfolio',
    number: '03',
    title: 'Portfolio Analysis',
    detail: 'Top-down portfolio analysis and Portfolio Memo review.',
    path: '/portfolio-analysis',
  },
  {
    key: 'model-routing',
    number: '04',
    title: 'Model Routing',
    detail: 'Live model assignments across council, router, portfolio, and market intelligence.',
    path: '/model-routing',
  },
];

export default function IntelligenceHome({ onNavigate }) {
  return (
    <main className="intelligence-home">
      <section className="intelligence-home-intro" aria-labelledby="intelligence-home-title">
        <h1 id="intelligence-home-title">Alpha Edge Intelligence</h1>
        <p className="intelligence-home-copy">
          Analyst Council, announcement routing, and portfolio analysis in one working surface.
        </p>
      </section>

      <section className="intelligence-capability-list" aria-label="Intelligence capabilities">
        {CAPABILITIES.map((capability) => (
          <button
            type="button"
            className="intelligence-capability-row"
            key={capability.key}
            onClick={() => onNavigate(capability.path)}
          >
            <span className="intelligence-capability-number">{capability.number}</span>
            <span className="intelligence-capability-copy">
              <strong>{capability.title}</strong>
              <span>{capability.detail}</span>
            </span>
            <span className="intelligence-capability-open" aria-hidden="true">Open</span>
          </button>
        ))}
      </section>

      <footer className="intelligence-home-boundary">
        <span>OPERATIONAL WORKSPACE</span>
        <p>Three analysis services, one Alpha Edge runtime.</p>
      </footer>
    </main>
  );
}
