import { useState, useCallback } from 'react';
import { api } from '../services/api';

export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchDocuments = useCallback(async (topic = null) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDocuments(topic);
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteDocument = useCallback(async (docId) => {
    await api.deleteDocument(docId);
    setDocuments(prev => prev.filter(d => d.doc_id !== docId));
  }, []);

  return { documents, loading, error, fetchDocuments, deleteDocument };
}
