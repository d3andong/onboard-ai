import { useEffect, useRef, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ChatInterface from './components/ChatInterface';
import OnboardingModal from './components/OnboardingModal';
import ColdStartToast from './components/ColdStartToast';
import ViewerPage from './components/viewer/ViewerPage';
import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';
import { useTopics } from './hooks/useTopics';
import { api } from './services/api';

export default function App() {
  const { messages, loading, sendMessage, clearChat } = useChat();
  const { documents, loading: docsLoading, fetchDocuments } = useDocuments();
  const { topics, selectedTopic, setSelectedTopic, loading: topicsLoading } = useTopics();
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const prevTopicId = useRef(null);

  const anyLoading = topicsLoading || loading || questionsLoading;

  const [showOnboarding, setShowOnboarding] = useState(
    () => localStorage.getItem('onboarding-complete') !== 'true'
  );

  useEffect(() => {
    if (!selectedTopic) return;
    if (prevTopicId.current === selectedTopic.id) return;
    prevTopicId.current = selectedTopic.id;

    clearChat();
    fetchDocuments(selectedTopic.id);

    setQuestionsLoading(true);
    api.getSuggestedQuestions(selectedTopic.id)
      .then(data => setSuggestedQuestions(data.questions || []))
      .catch(() => setSuggestedQuestions([]))
      .finally(() => setQuestionsLoading(false));
  }, [selectedTopic]);

  const handleSend = (question) => sendMessage(question, selectedTopic?.id ?? null);

  const handleOnboardingComplete = (pickedTopic) => {
    localStorage.setItem('onboarding-complete', 'true');
    if (pickedTopic) setSelectedTopic(pickedTopic);
    setShowOnboarding(false);
  };

  return (
    <Routes>
      <Route
        path="/"
        element={
          <>
            <Layout
              documents={documents}
              docsLoading={docsLoading}
              topics={topics}
              topicsLoading={topicsLoading}
              selectedTopic={selectedTopic}
              onSelectTopic={setSelectedTopic}
              onNewChat={clearChat}
            >
              <ChatInterface
                messages={messages}
                loading={loading}
                onSend={handleSend}
                onClear={clearChat}
                suggestedQuestions={suggestedQuestions}
                questionsLoading={questionsLoading}
                selectedTopicId={selectedTopic?.id ?? null}
              />
            </Layout>

            {showOnboarding && (
              <OnboardingModal
                topics={topics}
                topicsLoading={topicsLoading}
                onComplete={handleOnboardingComplete}
              />
            )}

            <ColdStartToast loading={anyLoading} />
          </>
        }
      />
      <Route path="/viewer" element={<ViewerPage />} />
    </Routes>
  );
}
