import { useState, useCallback, useRef } from 'react';
import { api } from '../services/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const queryCount = useRef(0);

  const sendMessage = useCallback(async (question, topic = null) => {
    const userMsg = { role: 'user', content: question, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    // Build conversation history (last 5 turns = 10 messages)
    const history = messages.slice(-10).map(m => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const data = await api.query(question, history, topic);
      queryCount.current += 1;
      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        id: Date.now() + 1,
      };
      setMessages(prev => [...prev, assistantMsg]);
      return { queryCount: queryCount.current };
    } catch (err) {
      setError(err.message);
      const errMsg = {
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        sources: [],
        id: Date.now() + 1,
        isError: true,
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }, [messages]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    queryCount.current = 0;
  }, []);

  return { messages, loading, error, sendMessage, clearChat, queryCount: queryCount.current };
}
