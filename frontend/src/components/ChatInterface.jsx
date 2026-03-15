import { useEffect, useRef, useState } from 'react';
import { Send, RotateCcw, Loader2 } from 'lucide-react';
import ChatMessage, { TypingIndicator } from './ChatMessage';
import SuggestedQuestions from './SuggestedQuestions';
import { api } from '../services/api';

const GLASS_BG = 'rgba(248, 247, 244, 0.88)';
const GLASS_GRADIENT = `linear-gradient(to top, ${GLASS_BG} 0%, transparent 100%)`;

function SuggestionChips({ chips, onSelect, loading }) {
  if (!chips || chips.length === 0) return null;

  return (
    <div className="px-4 pt-3 pb-2 max-w-3xl mx-auto w-full">
      {loading && <Loader2 size={11} className="text-muted animate-spin mb-2" />}
      <div className="flex flex-wrap gap-x-3 gap-y-2">
        {chips.map((chip, i) => {
          const text = typeof chip === 'string' ? chip : chip.text;
          return (
            <button
              key={i}
              onClick={() => onSelect(text)}
              className="max-w-[300px] text-left text-[13px] text-charcoal bg-white/70 border border-gray-200 hover:bg-white rounded-full px-3 py-1.5 transition-colors"
            >
              {text}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function ChatInterface({
  messages,
  loading,
  onSend,
  onClear,
  suggestedQuestions,
  questionsLoading,
  selectedTopicId,
}) {
  const [input, setInput] = useState('');
  const [chipQuestions, setChipQuestions] = useState([]);
  const [chipsLoading, setChipsLoading] = useState(false);
  const lastAiCount = useRef(0);
  const chipsInitialized = useRef(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (messages.length === 0) {
      setChipQuestions([]);
      lastAiCount.current = 0;
      chipsInitialized.current = false;
    }
  }, [messages.length]);

  useEffect(() => {
    const aiMsgs = messages.filter(m => m.role === 'assistant' && !m.isError);
    if (aiMsgs.length === 0 || aiMsgs.length === lastAiCount.current) return;
    lastAiCount.current = aiMsgs.length;

    if (!chipsInitialized.current) {
      chipsInitialized.current = true;
      setChipQuestions(suggestedQuestions);
      return;
    }

    const lastAi = aiMsgs[aiMsgs.length - 1];
    const userMsgs = messages.filter(m => m.role === 'user');
    const lastUser = userMsgs[userMsgs.length - 1];

    setChipsLoading(true);
    api.getFollowUpQuestions(lastUser?.content, lastAi.content, selectedTopicId)
      .then(data => {
        if (data.questions?.length > 0) setChipQuestions(data.questions);
      })
      .catch(err => console.warn('[ChatInterface] follow-up chips failed', err))
      .finally(() => setChipsLoading(false));
  }, [messages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput('');
    onSend(q);
  };

  const isEmpty = messages.length === 0;
  const showChips = !isEmpty && !loading;

  return (
    <div className="relative flex-1 min-h-0">
      {/*
        Scroll area fills the whole space. pb-48 ensures the last message
        scrolls clear of the absolutely-positioned footer below.
      */}
      <div className="absolute inset-0 overflow-y-auto scrollbar-thin px-4 pt-4 pb-48">
        {isEmpty ? (
          <SuggestedQuestions questions={suggestedQuestions} onSelect={onSend} loading={questionsLoading} />
        ) : (
          <div className="max-w-3xl mx-auto">
            {messages.map((msg, i) => {
              const prevMsg = i > 0 ? messages[i - 1] : null;
              const question = (msg.role === 'assistant' && prevMsg?.role === 'user')
                ? prevMsg.content : undefined;
              return (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  topic={selectedTopicId}
                  question={question}
                />
              );
            })}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/*
        Footer is absolutely anchored to the bottom of this container,
        so it physically overlaps the scroll area — making backdrop-filter
        actually blur the content behind it.
      */}
      <div
        className="absolute bottom-0 left-0 right-0"
        style={{
          background: GLASS_BG,
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          boxShadow: '0 -2px 8px rgba(0,0,0,0.04)',
        }}
      >
        {/*
          Gradient bleeds upward out of the footer, fading messages
          into the glass background. -translate-y-full lifts it
          above the footer without affecting layout.
        */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute top-0 left-0 right-0 h-12 -translate-y-full"
          style={{ background: GLASS_GRADIENT }}
        />

        {showChips && (
          <SuggestionChips chips={chipQuestions} onSelect={onSend} loading={chipsLoading} />
        )}

        <div className="px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={onClear}
                className="p-2 text-muted hover:text-charcoal transition-colors rounded-lg hover:bg-white/60"
                title="New chat"
              >
                <RotateCcw size={16} />
              </button>
            )}
            <div className="flex-1 flex items-center bg-white/80 border border-gray-200 rounded-xl overflow-hidden focus-within:border-navy/40 transition-colors">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                placeholder="Ask a question about your docs..."
                disabled={loading}
                className="flex-1 bg-transparent px-4 py-3 text-sm text-charcoal placeholder-muted outline-none disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="m-1.5 p-2 bg-navy text-white rounded-lg hover:bg-navy-light disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
