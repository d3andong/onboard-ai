import { Upload, X, FileText } from 'lucide-react';

export default function UploadCTA({ onUpload, onDismiss }) {
  return (
    <div className="mx-4 mb-3 flex items-center gap-3 bg-navy/5 border border-navy/10 rounded-xl px-4 py-3">
      <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-amber-brand/20 shrink-0">
        <FileText size={16} className="text-amber-dark" />
      </div>
      <p className="flex-1 text-sm text-charcoal">
        <span className="font-medium">Try it with your own docs</span> — upload a handbook, wiki, or any PDF and start asking questions.
      </p>
      <button
        onClick={onUpload}
        className="shrink-0 flex items-center gap-1.5 bg-amber-brand hover:bg-amber-light text-navy text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
      >
        <Upload size={12} />
        Upload
      </button>
      <button
        onClick={onDismiss}
        className="shrink-0 text-muted hover:text-charcoal transition-colors"
        aria-label="Dismiss"
      >
        <X size={16} />
      </button>
    </div>
  );
}
