import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ViewerHeader from './ViewerHeader';
import SourceViewer from './SourceViewer';
import { api } from '../../services/api';

export default function ViewerPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const topic    = searchParams.get('topic') || '';
  const question = searchParams.get('question') || '';
  const chunkIds = (searchParams.get('chunks') || '').split(',').filter(Boolean);
  const scores   = (searchParams.get('scores') || '').split(',').map(Number);

  // contexts: { [chunkId]: 'loading' | 'error' | <data object> }
  const [contexts, setContexts] = useState({});

  const fetchChunk = useCallback((id) => {
    setContexts(prev => ({ ...prev, [id]: 'loading' }));
    api.getChunkContext(id, topic)
      .then(data => setContexts(prev => ({ ...prev, [id]: data })))
      .catch(() => setContexts(prev => ({ ...prev, [id]: 'error' })));
  }, [topic]);

  useEffect(() => {
    if (!chunkIds.length || !topic) return;
    chunkIds.forEach(fetchChunk);
  }, []); // intentionally run once on mount

  const allFetched = chunkIds.length > 0 && chunkIds.every(id => contexts[id] !== undefined);
  const allFailed  = allFetched && chunkIds.every(id => contexts[id] === 'error');

  if (!chunkIds.length || !topic) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="text-center text-muted text-sm">
          <p className="mb-4">No source data to display.</p>
          <button onClick={() => navigate('/')} className="text-navy hover:underline">
            ← Back to chat
          </button>
        </div>
      </div>
    );
  }

  if (allFailed) {
    return (
      <div className="min-h-screen bg-bg">
        <ViewerHeader question={question} />
        <div className="max-w-[800px] mx-auto px-6 py-20 text-center">
          <p className="text-muted text-sm mb-6">Couldn&apos;t load any source context.</p>
          <button
            onClick={() => navigate(-1)}
            className="text-navy text-sm hover:underline"
          >
            ← Back to chat
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg">
      <ViewerHeader question={question} />

      <div className="max-w-[800px] mx-auto px-6 py-10">
        {chunkIds.map((id, i) => (
          <SourceViewer
            key={id}
            chunkId={id}
            topic={topic}
            score={scores[i] ?? null}
            sourceNumber={i + 1}
            context={contexts[id] ?? 'loading'}
            onRetry={() => fetchChunk(id)}
            isFirst={i === 0}
          />
        ))}
      </div>
    </div>
  );
}
