import { useState } from 'react';
import { Menu, X, Plus, Bot } from 'lucide-react';
import DocumentList from './DocumentList';

function TopicItem({ topic, isActive, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-2 px-3 py-2 text-left transition-colors
        ${isActive
          ? 'border-l-[3px] border-blue-500 bg-blue-50 pl-[9px]'
          : 'border-l-[3px] border-transparent hover:bg-gray-50'
        }
      `}
    >
      <span className="text-base leading-none shrink-0">{topic.icon || '📄'}</span>
      <span className={`flex-1 text-sm ${isActive ? 'font-medium text-navy' : 'text-charcoal'}`}>
        {topic.name}
      </span>
      <span className="shrink-0 text-xs font-mono bg-gray-100 text-muted px-1.5 py-0.5 rounded">
        {topic.chunk_count ?? topic.doc_count ?? 0}
      </span>
    </button>
  );
}

export default function Layout({
  children,
  documents,
  docsLoading,
  topics,
  topicsLoading,
  selectedTopic,
  onSelectTopic,
  onNewChat,
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex flex-col h-screen bg-bg">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-3 bg-navy border-b border-navy-dark shadow-sm z-30">
        <div className="flex items-center gap-3">
          <button
            className="md:hidden text-white/70 hover:text-white transition-colors"
            onClick={() => setSidebarOpen(o => !o)}
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-amber-brand flex items-center justify-center">
              <Bot size={16} className="text-navy" />
            </div>
            <span className="font-sans font-semibold text-white text-base tracking-tight">OnboardAI</span>
          </div>
          {selectedTopic && (
            <span className="hidden sm:block text-xs text-white/40 font-mono">
              Exploring: {selectedTopic.name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onNewChat}
            className="flex items-center gap-1.5 text-white/70 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
          >
            <Plus size={15} />
            <span className="hidden sm:block">New Chat</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Mobile sidebar overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={`
            fixed md:relative z-20 md:z-auto h-full md:h-auto
            w-64 bg-surface border-r border-gray-100 flex flex-col
            transition-transform duration-200
            ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          `}
        >
          <div className="flex-1 overflow-y-auto scrollbar-thin py-4">
            {/* TOPICS section */}
            <div className="px-4 mb-2">
              <p className="text-xs font-semibold text-muted uppercase tracking-wider">Topics</p>
            </div>

            {topicsLoading ? (
              <div className="px-4 py-2 text-xs text-muted">Loading topics…</div>
            ) : topics?.length === 0 ? (
              <div className="px-4 py-2 text-xs text-muted">No topics available.</div>
            ) : (
              <div className="mb-4">
                {topics?.map(topic => (
                  <TopicItem
                    key={topic.id}
                    topic={topic}
                    isActive={selectedTopic?.id === topic.id}
                    onClick={() => {
                      onSelectTopic(topic);
                      setSidebarOpen(false);
                    }}
                  />
                ))}
              </div>
            )}

            {/* DOCUMENTS section */}
            <div className="px-4 mb-2 mt-2">
              <p className="text-xs font-semibold text-muted uppercase tracking-wider">Documents</p>
            </div>
            <DocumentList documents={documents} loading={docsLoading} />
          </div>
        </aside>

        {/* Main content */}
        <main className="flex flex-col flex-1 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
