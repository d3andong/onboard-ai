import { useState, useRef, useCallback } from 'react';
import { Upload, X, CheckCircle, AlertCircle, FileText, Loader2 } from 'lucide-react';
import { api } from '../services/api';

const ACCEPTED = ['.pdf', '.docx', '.md', '.txt'];
const MAX_MB = 20;

function FileRow({ fileState }) {
  const { file, status, message } = fileState;
  const icon = {
    pending: <FileText size={16} className="text-muted" />,
    uploading: <Loader2 size={16} className="text-amber-brand animate-spin" />,
    done: <CheckCircle size={16} className="text-green-500" />,
    error: <AlertCircle size={16} className="text-red-400" />,
  }[status];

  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-gray-50 last:border-0">
      {icon}
      <div className="flex-1 min-w-0">
        <p className="font-mono text-xs text-charcoal truncate">{file.name}</p>
        {message && (
          <p className={`text-xs mt-0.5 ${status === 'error' ? 'text-red-400' : 'text-muted'}`}>
            {message}
          </p>
        )}
      </div>
    </div>
  );
}

export default function UploadPanel({ isOpen, onClose, onSuccess }) {
  const [fileStates, setFileStates] = useState([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const updateFile = (index, update) => {
    setFileStates(prev => prev.map((f, i) => i === index ? { ...f, ...update } : f));
  };

  const processFiles = useCallback(async (files) => {
    const newFiles = Array.from(files).map(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase();
      if (!ACCEPTED.includes(ext)) {
        return { file: f, status: 'error', message: `Unsupported file type (${ext})` };
      }
      if (f.size > MAX_MB * 1024 * 1024) {
        return { file: f, status: 'error', message: `File too large (max ${MAX_MB}MB)` };
      }
      return { file: f, status: 'pending', message: null };
    });

    const startIndex = fileStates.length;
    setFileStates(prev => [...prev, ...newFiles]);

    const validFiles = newFiles.map((fs, i) => ({ ...fs, index: startIndex + i }))
      .filter(fs => fs.status === 'pending');

    for (const { file, index } of validFiles) {
      updateFile(index, { status: 'uploading', message: 'Processing...' });
      try {
        const result = await api.ingest([file]);
        const info = result.results?.[0];
        updateFile(index, {
          status: 'done',
          message: info ? `✓ ${info.chunk_count} chunks indexed` : '✓ Indexed',
        });
        onSuccess?.();
      } catch (err) {
        updateFile(index, { status: 'error', message: err.message });
      }
    }
  }, [fileStates, onSuccess]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    processFiles(e.dataTransfer.files);
  }, [processFiles]);

  const handleClose = () => {
    setFileStates([]);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-surface rounded-2xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-sans font-semibold text-navy text-lg">Upload Documents</h2>
          <button onClick={handleClose} className="text-muted hover:text-charcoal transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              dragging
                ? 'border-amber-brand bg-amber-brand/5'
                : 'border-gray-200 hover:border-navy/30 hover:bg-navy/2'
            }`}
          >
            <Upload size={32} className={`mx-auto mb-3 ${dragging ? 'text-amber-brand' : 'text-muted'}`} />
            <p className="font-sans font-medium text-charcoal mb-1">
              Drop files here or <span className="text-navy underline">click to browse</span>
            </p>
            <p className="text-xs text-muted mb-3">Supports PDF, DOCX, MD, TXT — max {MAX_MB}MB each</p>
            <div className="flex justify-center gap-2">
              {['PDF', 'DOCX', 'MD', 'TXT'].map(t => (
                <span key={t} className="text-xs font-mono font-medium bg-navy/8 text-navy px-2 py-0.5 rounded">
                  {t}
                </span>
              ))}
            </div>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={ACCEPTED.join(',')}
              className="hidden"
              onChange={e => processFiles(e.target.files)}
            />
          </div>

          {/* File list */}
          {fileStates.length > 0 && (
            <div className="mt-4 bg-gray-50 rounded-xl px-4 py-1">
              {fileStates.map((fs, i) => (
                <FileRow key={i} fileState={fs} />
              ))}
            </div>
          )}
        </div>

        <div className="px-6 pb-6 flex justify-end">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-muted hover:text-charcoal transition-colors"
          >
            {fileStates.some(f => f.status === 'done') ? 'Done' : 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  );
}
