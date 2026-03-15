export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  async getTopics() {
    const res = await fetch(`${API_BASE}/api/topics`);
    if (!res.ok) throw new Error(`Failed to fetch topics: ${res.status}`);
    return res.json();
  },

  async query(question, conversationHistory = [], topic = null) {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        conversation_history: conversationHistory,
        ...(topic && { topic }),
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Query failed: ${res.status}`);
    }
    return res.json();
  },

  async ingest(files) {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    const res = await fetch(`${API_BASE}/api/ingest`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed: ${res.status}`);
    }
    return res.json();
  },

  async getDocuments(topic = null) {
    const url = topic
      ? `${API_BASE}/api/documents?topic=${encodeURIComponent(topic)}`
      : `${API_BASE}/api/documents`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch documents: ${res.status}`);
    return res.json();
  },

  async deleteDocument(docId) {
    const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Delete failed: ${res.status}`);
    }
    return res.json();
  },

  async getChunkContext(chunkId, topic, contextChars = 2000) {
    const url = `${API_BASE}/api/chunks/${encodeURIComponent(chunkId)}/context?topic=${encodeURIComponent(topic)}&context_chars=${contextChars}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch chunk context: ${res.status}`);
    return res.json();
  },

  getDocumentRawUrl(docId, topic) {
    return `${API_BASE}/api/documents/${encodeURIComponent(docId)}/raw?topic=${encodeURIComponent(topic)}`;
  },

  async getFollowUpQuestions(question, answer, topic = null) {
    try {
      const res = await fetch(`${API_BASE}/api/suggested-questions/follow-up`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ last_question: question, last_answer: answer, ...(topic && { topic }) }),
      });
      if (!res.ok) {
        console.warn('[follow-up] request failed', res.status, await res.text().catch(() => ''));
        return { questions: [] };
      }
      return res.json();
    } catch (err) {
      console.warn('[follow-up] fetch error', err);
      return { questions: [] };
    }
  },

  async getSuggestedQuestions(topic = null) {
    const url = topic
      ? `${API_BASE}/api/suggested-questions?topic=${encodeURIComponent(topic)}`
      : `${API_BASE}/api/suggested-questions`;
    const res = await fetch(url);
    if (!res.ok) return { questions: [] };
    return res.json();
  },
};
