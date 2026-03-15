import { MessageSquare, Loader2 } from 'lucide-react';

export default function SuggestedQuestions({ questions, onSelect, loading }) {
  const isEmpty = !questions || questions.length === 0;

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-4 pb-8">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-navy mb-4">
            <MessageSquare className="text-amber-brand" size={24} />
          </div>
          <h2 className="text-2xl font-sans font-semibold text-navy mb-2">Welcome to OnboardAI</h2>
          <p className="text-muted text-sm">Ask anything about your company docs, policies, and processes.</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 text-muted text-sm py-6">
            <Loader2 size={16} className="animate-spin" />
            <span>Generating questions…</span>
          </div>
        ) : isEmpty ? null : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {questions.map((q, i) => {
              const text = typeof q === 'string' ? q : q.text;
              const topic = typeof q === 'string' ? null : q.topic;
              return (
                <button
                  key={i}
                  onClick={() => onSelect(text)}
                  className="text-left p-4 bg-surface rounded-xl border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group"
                >
                  <p className="text-sm font-medium text-charcoal group-hover:text-navy mb-1">{text}</p>
                  {topic && (
                    <span className="inline-block text-xs text-muted bg-gray-50 px-2 py-0.5 rounded-full">
                      {topic}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
