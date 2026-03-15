import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Bot } from 'lucide-react';

export default function ViewerHeader({ question }) {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-10 bg-navy shadow-sm">
      <div className="max-w-[800px] mx-auto px-6 py-3 flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-white/70 hover:text-white text-sm transition-colors shrink-0"
        >
          <ArrowLeft size={15} />
          Back to chat
        </button>

        <div className="flex-1 flex justify-center">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-amber-brand flex items-center justify-center">
              <Bot size={13} className="text-navy" />
            </div>
            <span className="font-sans font-semibold text-white text-sm tracking-tight">OnboardAI</span>
          </div>
        </div>

        {/* Balance the back button visually */}
        <div className="w-24 shrink-0" />
      </div>

      {question && (
        <div className="max-w-[800px] mx-auto px-6 pb-4">
          <blockquote className="border-l-2 border-amber-brand pl-3 text-sm text-white/60 italic leading-relaxed">
            &ldquo;{question}&rdquo;
          </blockquote>
        </div>
      )}
    </header>
  );
}
