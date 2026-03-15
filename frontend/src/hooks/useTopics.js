import { useState, useEffect } from 'react';
import { api } from '../services/api';

export function useTopics() {
  const [topics, setTopics] = useState([]);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTopics()
      .then(data => {
        const t = data.topics || [];
        setTopics(t);
        if (t.length > 0) setSelectedTopic(t[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { topics, selectedTopic, setSelectedTopic, loading };
}
