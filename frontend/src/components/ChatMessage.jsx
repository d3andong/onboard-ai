import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import SourceCard from './SourceCard';

function highlightSource(num) {
  const el = document.getElementById(`source-${num}`);
  if (!el) return;
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  el.classList.add('ring-2', 'ring-blue-400', 'ring-offset-1', 'rounded-r-lg');
  setTimeout(() => el.classList.remove('ring-2', 'ring-blue-400', 'ring-offset-1', 'rounded-r-lg'), 1500);
}

const markdownComponents = {
  p: ({ children }) => <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-charcoal">{children}</strong>,
  h1: ({ children }) => <h1 className="font-sans font-semibold text-navy mt-3 mb-1.5 text-sm">{children}</h1>,
  h2: ({ children }) => <h2 className="font-sans font-semibold text-navy mt-3 mb-1.5 text-sm">{children}</h2>,
  h3: ({ children }) => <h3 className="font-sans font-semibold text-navy mt-3 mb-1.5 text-sm">{children}</h3>,
  ul: ({ children }) => <ul className="list-disc pl-4 space-y-1 mb-2 text-sm">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 space-y-1 mb-2 text-sm">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  blockquote: ({ children }) => <blockquote className="border-l-2 border-amber-brand pl-3 my-2 text-sm italic text-charcoal/70">{children}</blockquote>,
  code: ({ className, children }) =>
    className
      ? <code className={`font-mono text-xs ${className}`}>{children}</code>
      : <code className="font-mono text-xs bg-gray-100 text-navy px-1.5 py-0.5 rounded">{children}</code>,
  pre: ({ children }) => <pre className="bg-gray-50 border border-gray-100 rounded-lg p-3 my-2 overflow-x-auto">{children}</pre>,
  a: ({ href, children }) => {
    if (href?.startsWith('#source-')) {
      const num = href.replace('#source-', '');
      return (
        <a
          href={href}
          onClick={e => { e.preventDefault(); highlightSource(num); }}
          className="text-navy font-medium hover:underline cursor-pointer"
        >
          {children}
        </a>
      );
    }
    return <a href={href} className="text-navy underline hover:text-amber-dark">{children}</a>;
  },
};

// Turn [Source 1] into a markdown link so the `a` override can handle it
function linkifySources(content) {
  return content.replace(/\[Source (\d+)\]/g, (_, n) => `[Source ${n}](#source-${n})`);
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-8 h-8 rounded-full bg-navy flex items-center justify-center shrink-0">
        <span className="text-amber-brand text-xs font-bold font-sans">AI</span>
      </div>
      <div className="bg-surface rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-5">
          <span className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-muted rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

export default function ChatMessage({ message, topic, question }) {
  const isUser = message.role === 'user';
  const time = new Date(message.id).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%]">
          <div className="bg-navy text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
          <p className="text-xs text-muted text-right mt-1">{time}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="w-8 h-8 rounded-full bg-navy flex items-center justify-center shrink-0 mt-1">
        <span className="text-amber-brand text-xs font-bold font-sans">AI</span>
      </div>
      <div className="max-w-[80%]">
        <div className={`bg-surface rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm ${message.isError ? 'border border-red-100' : ''}`}>
          <ReactMarkdown rehypePlugins={[rehypeHighlight]} components={markdownComponents}>
            {linkifySources(message.content)}
          </ReactMarkdown>
          <SourceCard sources={message.sources} topic={topic} question={question} />
        </div>
        <p className="text-xs text-muted mt-1">{time}</p>
      </div>
    </div>
  );
}

export { TypingIndicator };
