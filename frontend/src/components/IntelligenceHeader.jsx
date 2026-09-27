import './IntelligenceHeader.css';

const NAV_ITEMS = [
  { key: 'overview', label: 'Overview', path: '/' },
  { key: 'council', label: 'Analyst Council', path: '/council' },
  { key: 'router', label: 'Announcement Router', path: '/announcement-router' },
  { key: 'portfolio', label: 'Portfolio Analysis', path: '/portfolio-analysis' },
  { key: 'model-routing', label: 'Model Routing', path: '/model-routing' },
];

function itemIsActive(item, path) {
  if (item.key === 'overview') return path === '/';
  if (item.key === 'council') {
    return ['/council', '/council/new', '/council/runs', '/gantt-lab', '/gantt-demo'].includes(path);
  }
  if (item.key === 'router') return ['/announcement-router', '/scenario-router'].includes(path);
  if (item.key === 'portfolio') {
    return ['/portfolio-analysis', '/portfolio-positioning', '/portfolio-positioning-memos'].includes(path);
  }
  if (item.key === 'model-routing') return path === '/model-routing';
  return false;
}

export default function IntelligenceHeader({ currentPath, onNavigate }) {
  return (
    <header className="intelligence-header">
      <button
        type="button"
        className="intelligence-lockup"
        onClick={() => onNavigate('/')}
        aria-label="Alpha Edge Intelligence overview"
      >
        <img src="/alpha-edge-intelligence.svg" alt="" className="intelligence-lockup-mark" />
        <span className="intelligence-lockup-product">ALPHA EDGE</span>
        <span className="intelligence-lockup-divider" aria-hidden="true">/</span>
        <span className="intelligence-lockup-service">INTELLIGENCE</span>
      </button>

      <nav className="intelligence-nav" aria-label="Alpha Edge Intelligence">
        {NAV_ITEMS.map((item) => {
          const active = itemIsActive(item, currentPath);
          return (
            <button
              type="button"
              key={item.key}
              className={`intelligence-nav-item${active ? ' is-active' : ''}`}
              aria-current={active ? 'page' : undefined}
              onClick={() => onNavigate(item.path)}
            >
              {item.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
