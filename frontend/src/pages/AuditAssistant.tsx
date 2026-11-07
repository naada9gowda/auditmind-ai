import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import { ChatResponse, ChatReference } from '../api/types';
import SourceDrawer from '../components/SourceDrawer';
import LoadingSpinner from '../components/LoadingSpinner';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  DocumentMagnifyingGlassIcon,
  SparklesIcon,
  ClockIcon,
  InformationCircleIcon,
  UserCircleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  references?: ChatReference[];
  model_unavailable?: boolean;
  used_history?: boolean;
  timestamp: string;
}

const STARTER_QUESTIONS = [
  'Has SEC-014 been a problem before?',
  'What are the highest risk findings?',
  'Any overdue actions?',
  'Summarize recent access review deficiencies',
];

export const AuditAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: "Hello! I am AuditMind AI, your continuous compliance assurance copilot. Ask me about control status, recurring defect histories across cycles, overdue remediations, or high-risk findings.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [inputQuestion, setInputQuestion] = useState<string>('');
  const [useHistory, setUseHistory] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);

  // Source Drawer state
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState<boolean>(false);
  const [activeReference, setActiveReference] = useState<ChatReference | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (questionToSend?: string) => {
    const q = (questionToSend || inputQuestion).trim();
    if (!q || loading) return;

    const userMsg: Message = {
      id: Math.random().toString(36).substring(2, 9),
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuestion('');
    setLoading(true);

    try {
      const response: ChatResponse = await api.chatAssistant(q, useHistory);

      const assistantMsg: Message = {
        id: Math.random().toString(36).substring(2, 9),
        sender: 'assistant',
        text: response.answer,
        references: response.references || [],
        model_unavailable: response.model_unavailable,
        used_history: response.used_history,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: Math.random().toString(36).substring(2, 9),
        sender: 'assistant',
        text: `Error contacting Audit Assistant: ${err.message || 'Unknown network error'}. Please ensure the backend is running at http://localhost:8000.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenReference = (ref: ChatReference) => {
    setActiveReference(ref);
    setSourceDrawerOpen(true);
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'init-reset',
        sender: 'assistant',
        text: "Conversation cleared. Feel free to ask about any audit controls, findings, or historical recurrences.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-4">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <SparklesIcon className="w-6 h-6 text-teal-600" />
            AI Audit Assistant
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Grounded assurance retrieval answering queries with verifiable source document page citations
          </p>
        </div>

        {/* History Toggle & Clear */}
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-2xs">
            <input
              type="checkbox"
              checked={useHistory}
              onChange={(e) => setUseHistory(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500 h-4 w-4"
            />
            <span className="text-xs font-semibold text-slate-700 flex items-center gap-1">
              <ClockIcon className="w-3.5 h-3.5 text-teal-600" />
              Use audit history
            </span>
          </label>

          <button
            type="button"
            onClick={clearChat}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition"
            title="Clear Chat History"
          >
            <TrashIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Starter Question Chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider mr-1">
          Suggestions:
        </span>
        {STARTER_QUESTIONS.map((sq, i) => (
          <button
            key={i}
            type="button"
            onClick={() => handleSend(sq)}
            className="px-3 py-1 bg-white hover:bg-teal-50 text-slate-700 hover:text-teal-900 rounded-full border border-slate-200 hover:border-teal-300 transition shadow-2xs text-xs font-medium"
          >
            {sq}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-xs p-4 sm:p-6 overflow-y-auto space-y-5">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';

          return (
            <div
              key={msg.id}
              className={clsx('flex gap-3 max-w-3xl', isUser ? 'ml-auto flex-row-reverse' : 'mr-auto')}
            >
              {/* Avatar */}
              <div
                className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold shadow-xs',
                  isUser
                    ? 'bg-slate-900 text-white'
                    : 'bg-teal-600 text-white'
                )}
              >
                {isUser ? 'You' : <SparklesIcon className="w-4 h-4" />}
              </div>

              {/* Message Content Bubble */}
              <div className="space-y-2">
                <div
                  className={clsx(
                    'p-4 rounded-2xl text-xs leading-relaxed shadow-2xs',
                    isUser
                      ? 'bg-slate-900 text-white rounded-tr-none'
                      : 'bg-slate-50 border border-slate-200 text-slate-800 rounded-tl-none'
                  )}
                >
                  {/* Deterministic Mode Notice */}
                  {msg.model_unavailable && (
                    <div className="mb-2.5 pb-2 border-b border-amber-200/60 flex items-center gap-1.5 text-[11px] text-amber-800 font-semibold bg-amber-50 -mx-2 -mt-2 p-2 rounded-t-xl">
                      <InformationCircleIcon className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Deterministic mode — LLM provider not configured. Operating with structured database retrieval rules.</span>
                    </div>
                  )}

                  <div className="whitespace-pre-wrap">{msg.text}</div>
                </div>

                {/* Reference Chips if assistant response */}
                {msg.references && msg.references.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Cited References ({msg.references.length}):
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {msg.references.map((ref, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleOpenReference(ref)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 border border-teal-200 text-[11px] font-medium transition shadow-2xs"
                        >
                          <DocumentMagnifyingGlassIcon className="w-3.5 h-3.5 text-teal-600" />
                          <span className="max-w-[200px] truncate">{ref.label}</span>
                          {ref.page && <span className="text-[10px] text-teal-600 font-bold">• P.{ref.page}</span>}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div
                  className={clsx(
                    'text-[10px] text-slate-400 font-mono px-1',
                    isUser ? 'text-right' : 'text-left'
                  )}
                >
                  {msg.timestamp}
                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 max-w-xl mr-auto">
            <div className="w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center shrink-0">
              <SparklesIcon className="w-4 h-4 animate-spin" />
            </div>
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
              <LoadingSpinner size="sm" />
              <span>Analyzing compliance database and historical records...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-2 bg-white p-2 rounded-xl border border-slate-200 shadow-sm"
      >
        <input
          type="text"
          value={inputQuestion}
          onChange={(e) => setInputQuestion(e.target.value)}
          placeholder="Ask about SEC-014 recurrence, high risk findings, overdue remediations..."
          className="flex-1 px-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-hidden bg-transparent"
        />

        <button
          type="submit"
          disabled={!inputQuestion.trim() || loading}
          className={clsx(
            'inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white shadow-xs transition',
            !inputQuestion.trim() || loading
              ? 'bg-slate-300 cursor-not-allowed'
              : 'bg-teal-600 hover:bg-teal-700'
          )}
        >
          <PaperAirplaneIcon className="w-4 h-4" />
          <span>Send</span>
        </button>
      </form>

      {/* Reference Context Source Drawer */}
      <SourceDrawer
        isOpen={sourceDrawerOpen}
        onClose={() => setSourceDrawerOpen(false)}
        documentId={activeReference?.id}
        pageNumber={activeReference?.page || 1}
        highlightExcerpt={activeReference?.excerpt || null}
        controlCode={activeReference?.label}
      />
    </div>
  );
};

export default AuditAssistant;
