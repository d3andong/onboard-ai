import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { useNavigate } from 'react-router-dom';
import { cleanChunkText } from '../utils/cleanChunkText';

const REHYPE_PLUGINS = [rehypeRaw, rehypeHighlight];

const excerptComponents = {
  p: ({ children }) => <p className="text-xs leading-relaxed mb-1.5 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  ul: ({ children }) => <ul className="list-disc pl-3 space-y-0.5 mb-1 text-xs">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-3 space-y-0.5 mb-1 text-xs">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  code: ({ className, children }) =>
    className
      ? <code className={`font-mono text-xs ${className}`}>{children}</code>
      : <code className="font-mono text-xs bg-white/60 px-1 rounded">{children}</code>,
  pre: ({ children }) => <pre className="bg-white/40 rounded p-2 my-1 overflow-x-auto text-xs">{children}</pre>,
};

function borderClass(pct) {
  if (pct >= 70) return 'border-green-400';
  if (pct >= 50) return 'border-amber-400';
  return 'border-gray-300';
}

function badgeClass(pct) {
  if (pct >= 70) return 'bg-green-50 text-green-700';
  if (pct >= 50) return 'bg-amber-50 text-amber-700';
  return 'bg-gray-100 text-gray-500';
}

function buildViewerUrl(sources, topic, question) {
  const chunks = sources.map(s => s.chunk_id).filter(Boolean).join(',');
  if (!chunks || !topic) return null;
  const scores = sources.map(s => Math.round((s.score || 0) * 100)).join(',');
  const params = new URLSearchParams({ topic, chunks, scores });
  if (question) params.set('question', question);
  return `/viewer?${params.toString()}`;
}

function SingleSource({ source, index, defaultExpanded, topic, question }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const navigate = useNavigate();
  const pct = Math.round((source.score || 0) * 100);

  const viewerUrl = buildViewerUrl([source], topic, question);

  return (
    <div
      id={`source-${index + 1}`}
      onClick={() => setExpanded(e => !e)}
      className={`border-l-[3px] ${borderClass(pct)} rounded-r-lg bg-gray-50 hover:bg-[#f5f5f2] p-3 transition-colors cursor-pointer`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-charcoal">Source {index + 1}</span>
            <span className={`text-xs font-mono px-1.5 py-0.5 rounded-full ${badgeClass(pct)}`}>
              {pct}%
            </span>
          </div>
          <p className="font-mono text-xs text-muted truncate mt-0.5">{source.filename}</p>
          {source.section && (
            <p className="text-xs text-muted/80 mt-0.5">§ {source.section}</p>
          )}
        </div>
        <div className="shrink-0 flex items-center gap-1 text-xs text-navy/60 whitespace-nowrap mt-0.5">
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Hide' : 'View excerpt'}
        </div>
      </div>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-gray-200 text-charcoal/80">
          <ReactMarkdown rehypePlugins={REHYPE_PLUGINS} components={excerptComponents}>
            {cleanChunkText(source.chunk_text)}
          </ReactMarkdown>
        </div>
      )}

      {/* View in document link — stop propagation so card click doesn't also toggle expand */}
      {viewerUrl && (
        <div
          className="mt-2 pt-2 border-t border-gray-100"
          onClick={e => e.stopPropagation()}
        >
          <button
            onClick={() => navigate(viewerUrl)}
            className="flex items-center gap-1 text-xs text-navy/60 hover:text-navy transition-colors"
          >
            View in document
            <ExternalLink size={11} />
          </button>
        </div>
      )}
    </div>
  );
}

export default function SourceCard({ sources, topic, question }) {
  const navigate = useNavigate();
  if (!sources || sources.length === 0) return null;

  const allUrl = buildViewerUrl(sources, topic, question);

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Sources</p>
      <div className="space-y-2">
        {sources.map((s, i) => (
          <SingleSource
            key={`${s.doc_id}-${i}`}
            source={s}
            index={i}
            defaultExpanded={i === 0}
            topic={topic}
            question={question}
          />
        ))}
      </div>

      {/* View all sources in context */}
      {allUrl && sources.length > 1 && (
        <button
          onClick={() => navigate(allUrl)}
          className="mt-3 flex items-center gap-1.5 text-xs text-navy/60 hover:text-navy transition-colors"
        >
          View all sources in context
          <ExternalLink size={11} />
        </button>
      )}
    </div>
  );
}
