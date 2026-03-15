import { useState, useRef, useEffect } from 'react';
import { FileText, ExternalLink, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { api } from '../../services/api';
import { cleanChunkText } from '../../utils/cleanChunkText';

// ─── Markdown renderers ───────────────────────────────────────────────────────

// Shared base — context text is slightly muted, highlight text is full opacity.
// Both use the same font size, line height, and element styling (Fix 3).
function makeComponents(muted) {
  const color = muted ? 'text-gray-500' : 'text-charcoal';
  return {
    p:          ({ children }) => <p          className={`text-[15px] leading-[1.7] mb-3 last:mb-0 ${color}`}>{children}</p>,
    strong:     ({ children }) => <strong     className="font-semibold text-charcoal">{children}</strong>,
    em:         ({ children }) => <em         className="italic">{children}</em>,
    h1:         ({ children }) => <h1         className="font-sans font-bold text-navy text-xl mt-6 mb-2">{children}</h1>,
    h2:         ({ children }) => <h2         className="font-sans font-semibold text-navy text-lg mt-5 mb-2">{children}</h2>,
    h3:         ({ children }) => <h3         className="font-sans font-semibold text-navy text-base mt-4 mb-1.5">{children}</h3>,
    h4:         ({ children }) => <h4         className="font-sans font-medium text-navy text-[15px] mt-3 mb-1">{children}</h4>,
    ul:         ({ children }) => <ul         className={`list-disc pl-5 space-y-1 mb-3 text-[15px] ${color}`}>{children}</ul>,
    ol:         ({ children }) => <ol         className={`list-decimal pl-5 space-y-1 mb-3 text-[15px] ${color}`}>{children}</ol>,
    li:         ({ children }) => <li         className={`leading-[1.7] ${color}`}>{children}</li>,
    blockquote: ({ children }) => <blockquote className="border-l-2 border-gray-300 pl-3 my-3 italic text-gray-500">{children}</blockquote>,
    a:          ({ href, children }) => (
      <a href={href} target="_blank" rel="noopener noreferrer"
         className="text-blue-600 underline hover:text-blue-800 transition-colors">
        {children}
      </a>
    ),
    code: ({ className, children }) =>
      className
        ? <code className={`font-mono text-sm ${className}`}>{children}</code>
        : <code className="font-mono text-sm bg-gray-100 text-navy px-1.5 py-0.5 rounded">{children}</code>,
    pre: ({ children }) => (
      <pre className="bg-gray-50 border border-gray-100 rounded-lg p-4 my-3 overflow-x-auto">{children}</pre>
    ),
  };
}

const ctxComponents       = makeComponents(true);
const highlightComponents = makeComponents(false);

const REHYPE_PLUGINS = [rehypeRaw, rehypeHighlight];

// ─── Sentence-boundary helpers ────────────────────────────────────────────────

function cleanBoundaries(chunkText, contextBefore, contextAfter) {
  let highlight = chunkText ?? '';
  let before    = contextBefore ?? '';
  let after     = contextAfter  ?? '';

  // Start fix: if highlight opens mid-word, move orphaned prefix to before
  if (/^[a-z]/.test(highlight.trimStart())) {
    const m = highlight.match(/[.!?]["')]*\s+[A-Z]/);
    if (m && m.index != null) {
      const splitAt = m.index + m[0].length - 1;
      before    = before + highlight.slice(0, splitAt);
      highlight = highlight.slice(splitAt);
    }
  }

  // End fix: if highlight closes mid-sentence, pull completing text from after
  if (highlight && !/[.!?]["')]*\s*$/.test(highlight.trimEnd())) {
    const m = after.match(/[.!?]["')]*(?=\s|$)/);
    if (m && m.index != null) {
      const splitAt = m.index + m[0].length;
      highlight = highlight + after.slice(0, splitAt);
      after     = after.slice(splitAt).replace(/^\s+/, '');
    }
  }

  return { before, highlight, after };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relevanceBadgeClass(pct) {
  if (pct >= 70) return 'bg-green-50 text-green-700 border border-green-200';
  if (pct >= 50) return 'bg-amber-50 text-amber-700 border border-amber-200';
  return 'bg-gray-50 text-gray-500 border border-gray-200';
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 bg-gray-100 rounded w-3/4" />
      <div className="h-4 bg-gray-100 rounded w-full" />
      <div className="h-4 bg-gray-100 rounded w-5/6" />
      <div className="my-4 h-20 bg-amber-50 rounded border-l-[3px] border-amber-200" />
      <div className="h-4 bg-gray-100 rounded w-full" />
      <div className="h-4 bg-gray-100 rounded w-2/3" />
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function SourceViewer({ chunkId, topic, score, sourceNumber, context, onRetry, isFirst }) {
  const [expanded, setExpanded]         = useState(false);
  const [expandedData, setExpandedData] = useState(null);
  const [expanding, setExpanding]       = useState(false);
  const highlightRef = useRef(null);

  const pct  = (score != null) ? Math.round(score) : null;
  const data = expandedData ?? (context !== 'loading' && context !== 'error' ? context : null);

  // Auto-scroll first highlighted excerpt into view once data loads
  useEffect(() => {
    if (!isFirst || context === 'loading' || context === 'error') return;
    const timer = setTimeout(() => {
      highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 250);
    return () => clearTimeout(timer);
  }, [context, isFirst]);

  const handleToggleContext = async () => {
    if (expanded) {
      setExpanded(false);
      setExpandedData(null);
      return;
    }
    setExpanding(true);
    try {
      const result = await api.getChunkContext(chunkId, topic, 6000);
      setExpandedData(result);
      setExpanded(true);
    } catch {
      // stay collapsed on failure
    } finally {
      setExpanding(false);
    }
  };

  const rawDocUrl = data ? api.getDocumentRawUrl(data.document.doc_id, topic) : null;

  // Clean text and adjust sentence boundaries
  const { before, highlight, after } = data
    ? cleanBoundaries(
        cleanChunkText(data.chunk_text),
        cleanChunkText(data.context_before),
        cleanChunkText(data.context_after),
      )
    : { before: '', highlight: '', after: '' };

  return (
    <section className="mb-10">
      {/* Document header */}
      <div className="flex items-start gap-3 mb-5">
        <FileText size={17} className="text-muted mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center flex-wrap gap-x-3 gap-y-1">
            <span className="font-semibold text-sm text-navy">
              {data?.document.filename ?? chunkId}
            </span>
            <span className="text-xs text-muted">Source {sourceNumber}</span>
            {data?.document.page_number != null && (
              <span className="text-xs text-muted">Page {data.document.page_number}</span>
            )}
            {pct != null && (
              <span className={`text-xs font-mono px-1.5 py-0.5 rounded-full ${relevanceBadgeClass(pct)}`}>
                {pct}% match
              </span>
            )}
          </div>
          {data?.section && (
            <p className="text-xs text-muted mt-0.5">§ {data.section}</p>
          )}
        </div>
      </div>

      {context === 'loading' && <LoadingSkeleton />}
      {context === 'error'   && <ErrorState onRetry={onRetry} />}

      {data && (
        <>
          {before && (
            <ReactMarkdown rehypePlugins={REHYPE_PLUGINS} components={ctxComponents}>
              {before}
            </ReactMarkdown>
          )}

          <div
            ref={isFirst ? highlightRef : undefined}
            className="my-5 border-l-[3px] border-amber-400 bg-amber-50 px-4 py-4 rounded-sm"
          >
            <ReactMarkdown rehypePlugins={REHYPE_PLUGINS} components={highlightComponents}>
              {highlight}
            </ReactMarkdown>
          </div>

          {after && (
            <ReactMarkdown rehypePlugins={REHYPE_PLUGINS} components={ctxComponents}>
              {after}
            </ReactMarkdown>
          )}

          <div className="flex items-center gap-6 mt-5">
            <button
              onClick={handleToggleContext}
              disabled={expanding}
              className="text-sm text-navy/60 hover:text-navy transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {expanding && <RotateCcw size={12} className="animate-spin" />}
              {expanded ? 'Show less context' : 'Show more context'}
            </button>

            {rawDocUrl && (
              <a
                href={rawDocUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-navy hover:text-amber-dark transition-colors flex items-center gap-1.5"
              >
                Open full document
                <ExternalLink size={13} />
              </a>
            )}
          </div>
        </>
      )}

      <hr className="border-gray-100 mt-8" />
    </section>
  );
}

function ErrorState({ onRetry }) {
  return (
    <div className="flex items-center gap-3 py-5 text-sm text-muted">
      <span>Couldn&apos;t load source context.</span>
      {onRetry && (
        <button onClick={onRetry} className="text-navy hover:underline flex items-center gap-1">
          <RotateCcw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
