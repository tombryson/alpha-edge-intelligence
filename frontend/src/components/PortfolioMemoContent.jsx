import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const components = {
  table: ({ children }) => <div className="portfolio-memo-table"><table>{children}</table></div>,
};

function allocationSections() {
  return (tree) => {
    const result = [];
    for (let index = 0; index < tree.children.length; index += 1) {
      const node = tree.children[index];
      const title = node.type === 'heading' && node.depth === 2 && node.children.map((child) => child.value || '').join('');
      if (title === 'Recommended Portfolio') {
        const retained = [];
        while (index + 1 < tree.children.length) {
          const next = tree.children[index + 1];
          if (next.type === 'heading' && next.depth <= 2) break;
          index += 1;
          if (next.type !== 'table') retained.push(next);
        }
        // Older memos put rationale alongside this table; preserve that prose.
        if (retained.length) result.push({ ...node, children: [{ type: 'text', value: 'Allocation Rationale' }] }, ...retained);
      } else {
        if (title === 'Investment Case') node.children = [{ type: 'text', value: 'Allocation Rationale' }];
        result.push(node);
      }
    }
    tree.children = result;
  };
}

export default function PortfolioMemoContent({ markdown, independent, executiveSummary, allocationTables = false }) {
  const sourceHeading = independent ? markdown.lastIndexOf('\n## Sources\n') : -1;
  const content = sourceHeading >= 0 ? markdown.slice(0, sourceHeading) : markdown;
  const researchHeading = independent ? content.indexOf('\n## Supporting Research\n') : -1;
  let body = researchHeading >= 0 ? content.slice(0, researchHeading) : content;
  if (independent && typeof executiveSummary === 'string' && executiveSummary.trim()) {
    body = body.replace(`## Executive View\n\n${executiveSummary.trim()}\n`, '## Executive View\n');
    body = body.replace(/## Executive View\s*(?=## |$)/, '');
  }
  const research = researchHeading >= 0 ? content.slice(researchHeading + '\n## Supporting Research\n'.length) : '';
  const sources = sourceHeading >= 0 ? markdown.slice(sourceHeading + '\n## Sources\n'.length) : '';
  return <div className="markdown-content">
    <ReactMarkdown remarkPlugins={allocationTables ? [remarkGfm, allocationSections] : [remarkGfm]} components={components}>{body}</ReactMarkdown>
    {research && <details className="portfolio-memo-sources"><summary>Supporting research</summary>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{research}</ReactMarkdown>
    </details>}
    {sources && <details className="portfolio-memo-sources"><summary>Sources</summary>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{sources}</ReactMarkdown>
    </details>}
  </div>;
}
