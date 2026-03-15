import { useState } from 'react';
import { FileText, Trash2, File, FileCode, BookOpen } from 'lucide-react';

function fileIcon(fileType) {
  const t = fileType?.toLowerCase();
  if (t === '.pdf') return <BookOpen size={14} className="text-red-400" />;
  if (t === '.docx') return <FileText size={14} className="text-blue-400" />;
  if (t === '.md') return <FileCode size={14} className="text-purple-400" />;
  return <File size={14} className="text-muted" />;
}

function DocItem({ doc, onDelete }) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete(doc.doc_id);
    } finally {
      setDeleting(false);
      setConfirming(false);
    }
  };

  const date = new Date(doc.uploaded_at).toLocaleDateString([], { month: 'short', day: 'numeric' });

  return (
    <div className="group relative flex items-start gap-2 px-3 py-2 rounded-lg hover:bg-navy/4 transition-colors">
      <div className="mt-0.5 shrink-0">{fileIcon(doc.file_type)}</div>
      <div className="flex-1 min-w-0">
        <p className="font-mono text-xs text-charcoal truncate" title={doc.filename}>
          {doc.filename}
        </p>
        <p className="text-xs text-muted mt-0.5">
          {doc.chunk_count} chunks · {date}
        </p>
      </div>
      {!confirming && (
        <button
          onClick={() => setConfirming(true)}
          className="opacity-0 group-hover:opacity-100 shrink-0 p-1 text-muted hover:text-red-400 transition-all"
          aria-label="Delete document"
        >
          <Trash2 size={13} />
        </button>
      )}
      {confirming && (
        <div className="absolute right-2 top-1 flex items-center gap-1 bg-surface border border-gray-200 rounded-lg shadow-sm px-2 py-1 z-10">
          <span className="text-xs text-charcoal whitespace-nowrap">Remove?</span>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="text-xs text-red-400 hover:text-red-600 font-medium px-1"
          >
            {deleting ? '…' : 'Yes'}
          </button>
          <button
            onClick={() => setConfirming(false)}
            className="text-xs text-muted hover:text-charcoal font-medium px-1"
          >
            No
          </button>
        </div>
      )}
    </div>
  );
}

export default function DocumentList({ documents, onDelete, loading }) {
  if (loading) {
    return (
      <div className="px-3 py-4 text-center">
        <p className="text-xs text-muted">Loading...</p>
      </div>
    );
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="px-3 py-4 text-center">
        <p className="text-xs text-muted leading-relaxed">
          No documents yet.<br />Upload your first doc to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {documents.map(doc => (
        <DocItem key={doc.doc_id} doc={doc} onDelete={onDelete} />
      ))}
    </div>
  );
}
