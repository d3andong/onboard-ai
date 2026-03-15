import { useState } from 'react';
import { FileSearch, Library, MessageSquare, BadgeCheck, Loader2 } from 'lucide-react';

// ─── Page 1 ──────────────────────────────────────────────────────────────────

function WelcomePage() {
  return (
    <div className="text-center px-10 pt-8 pb-4">
      <div className="flex justify-center mb-4">
        <div className="w-14 h-14 rounded-2xl bg-amber-50 flex items-center justify-center">
          <FileSearch size={32} className="text-amber-brand" strokeWidth={1.5} />
        </div>
      </div>
      <h1 className="font-sans font-bold text-[21px] text-navy mb-3 leading-snug">
        Your documents, instantly searchable
      </h1>
      <p className="text-sm text-charcoal leading-relaxed">
        OnboardAI turns complex documents into a conversation. Handbooks, operations
        manuals, compliance guides, tax resources — ask questions in plain English and
        get cited answers in seconds. No more digging through 300-page PDFs.
      </p>
    </div>
  );
}

// ─── Page 2 ──────────────────────────────────────────────────────────────────

const STEPS = [
  {
    Icon: Library,
    color: '#3b82f6',
    title: 'Choose a knowledge base',
    desc: 'Browse topics covering HR, franchise ops, real estate, taxes, and developer docs',
  },
  {
    Icon: MessageSquare,
    color: '#d97706',
    title: 'Ask a question',
    desc: "Type a question like you'd ask a coworker who read the whole document",
  },
  {
    Icon: BadgeCheck,
    color: '#16a34a',
    title: 'Get cited answers',
    desc: 'Every answer links back to the source text so you can verify and dig deeper',
  },
];

function HowItWorksPage() {
  return (
    <div className="px-10 pt-8 pb-4">
      <h1 className="font-sans font-bold text-[21px] text-navy mb-6 text-center leading-snug">
        Ask anything. Get answers with sources.
      </h1>
      <div className="space-y-4">
        {STEPS.map(({ Icon, color, title, desc }, i) => (
          <div key={i} className="flex items-start gap-4">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ backgroundColor: `${color}18` }}>
              <Icon size={18} strokeWidth={1.75} style={{ color }} />
            </div>
            <div>
              <p className="font-semibold text-sm text-navy mb-0.5">{title}</p>
              <p className="text-sm text-muted leading-relaxed">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Page 3 ──────────────────────────────────────────────────────────────────

function TopicPickerPage({ topics, topicsLoading, onPick }) {
  return (
    <div className="px-8 pt-6 pb-4">
      <h1 className="font-sans font-bold text-[21px] text-navy mb-1 text-center leading-snug">
        Try it now
      </h1>
      <p className="text-sm text-muted text-center mb-4">
        These are real documents we&apos;ve pre-loaded for you. Pick one to get started.
      </p>

      {topicsLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 size={22} className="text-muted animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {topics.map(topic => (
            <button
              key={topic.id}
              onClick={() => onPick(topic)}
              className="text-left p-3 bg-bg rounded-xl border border-gray-100 hover:border-amber-brand hover:shadow-md transition-all duration-200 group"
            >
              <div className="text-xl mb-1">{topic.icon || '📄'}</div>
              <p className="font-semibold text-[13px] text-navy group-hover:text-amber-dark transition-colors mb-0.5 leading-snug">
                {topic.name}
              </p>
              {topic.description && (
                <p className="text-[11px] text-muted leading-snug mb-1.5">{topic.description}</p>
              )}
              <span className="inline-block text-[10px] font-mono text-muted bg-gray-100 px-1.5 py-0.5 rounded">
                {topic.chunk_count ?? 0} chunks
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Dot indicators ───────────────────────────────────────────────────────────

function Dots({ count, current }) {
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`rounded-full transition-all duration-300 ${
            i === current ? 'w-5 h-2 bg-navy' : 'w-2 h-2 bg-gray-300'
          }`}
        />
      ))}
    </div>
  );
}

// ─── Modal ────────────────────────────────────────────────────────────────────

const TOTAL_PAGES = 3;

export default function OnboardingModal({ topics, topicsLoading, onComplete }) {
  const [page, setPage] = useState(0);

  const handleSkip = () => onComplete(null);
  const handleNext = () => setPage(p => Math.min(p + 1, TOTAL_PAGES - 1));

  const pageContent = [
    <WelcomePage key="welcome" />,
    <HowItWorksPage key="how" />,
    <TopicPickerPage
      key="topics"
      topics={topics}
      topicsLoading={topicsLoading}
      onPick={(topic) => onComplete(topic)}
    />,
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{
        backgroundColor: 'rgba(0,0,0,0.5)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
      }}
    >
      {/* max-h-[90vh] caps the modal below the viewport; overflow-hidden prevents any inner scroll */}
      <div className="bg-white rounded-2xl w-full max-w-[560px] max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">

        {/* Slide carousel — flex-1 so it takes remaining space above the footer */}
        <div className="overflow-hidden flex-1">
          <div
            className="flex h-full transition-transform duration-300 ease-in-out"
            style={{ transform: `translateX(-${page * 100}%)` }}
          >
            {pageContent.map((content, i) => (
              <div key={i} className="min-w-full">
                {content}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-10 py-5 flex items-center shrink-0 border-t border-gray-50">
          {page < TOTAL_PAGES - 1 ? (
            <>
              <button
                onClick={handleSkip}
                className="text-sm text-muted hover:text-charcoal transition-colors"
              >
                Skip
              </button>
              <div className="flex-1 flex justify-center">
                <Dots count={TOTAL_PAGES} current={page} />
              </div>
              <button
                onClick={handleNext}
                className="bg-navy text-white text-sm font-semibold px-5 py-2 rounded-xl hover:bg-navy-light transition-colors"
              >
                Next →
              </button>
            </>
          ) : (
            <>
              <div className="w-6" />
              <div className="flex-1 flex justify-center">
                <Dots count={TOTAL_PAGES} current={page} />
              </div>
              <button
                onClick={handleSkip}
                className="bg-navy text-white text-sm font-semibold px-5 py-2 rounded-xl hover:bg-navy-light transition-colors"
              >
                Get Started →
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  );
}
