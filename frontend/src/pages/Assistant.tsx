import React, { useState, useRef, useEffect } from 'react';
import { api } from '../api/client';
import { ChatResponse, ChatReference } from '../api/types';
import LoadingSpinner from '../components/LoadingSpinner';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  ClockIcon,
  DocumentTextIcon,
  ShieldCheckIcon,
  ExclamationCircleIcon,
  TrashIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  references?: ChatReference[];
  usedHistory?: boolean;
  modelUnavailable?: boolean;
  timestamp: string;
}

const SUGGESTED_PROMPTS = [
  'Has SEC-014 been a problem before?',
  'What controls currently have open gaps?',
  'Which remediation actions are overdue?',
  'Summarize findings from the January audit.',
];

export const Assistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am AuditMind AI Assistant. I can analyze control statuses, cross-cycle audit findings, remediation actions, and evidence records. All answers are grounded in database records with citations.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [useHistory, setUseHistory] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim() || loading) return;

    const userMessage: Message = {
      id: Math.random().toString(36).substring(2, 9),
      sender: 'user',
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    try {
      const response: ChatResponse = await api.chatAssistant(textToSend.trim(), useHistory);

      const assistantMessage: Message = {
        id: Math.random().toString(36).substring(2, 9),
        sender: 'assistant',
        text: response.answer,
        references: response.references,
        usedHistory: response.used_history,
        modelUnavailable: response.model_unavailable,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: Message = {
        id: Math.random().toString(36).substring(2, 9),
        sender: 'assistant',
        text: `Error contacting assistant: ${err?.message || 'Server error'}. Please try again.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'welcome',
        sender: 'assistant',
        text: 'Chat history cleared. How can I help you today?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  return (
    <div className="space-y-6 flex flex-col h-[calc(100vh-140px)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <ChatBubbleLeftRightIcon className="w-7 h-7 text-teal-600" />
            AI Audit Assistant
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Conversational compliance intelligence grounded in structured SQL audit records with verifiable citations.
          </p>
        </div>

        {/* History Toggle & Clear */}
        <div className="flex items-center gap-4 bg-white p-2.5 rounded-xl border border-slate-200 shadow-xs">
          <label className="flex items-center gap-2.5 text-xs font-semibold text-slate-700 cursor-pointer select-none">
            <div className="relative inline-flex items-center">
              <input
                type="checkbox"
                checked={useHistory}
                onChange={(e) => setUseHistory(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-teal-600"></div>
            </div>
            <span className="flex items-center gap-1.5">
              <ClockIcon className="w-4 h-4 text-teal-600" />
              Use Multi-Cycle History
            </span>
          </label>

          <div className="h-4 w-px bg-slate-200" />

          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-slate-500 hover:text-rose-600 flex items-center gap-1 transition"
            title="Clear Chat"
          >
            <TrashIcon className="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>

      {/* Suggested prompts bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 shrink-0">
        <span className="text-xs font-semibold text-slate-500 flex items-center gap-1 shrink-0">
          <LightBulbIcon className="w-3.5 h-3.5 text-amber-500" />
          Suggested:
        </span>
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSend(prompt)}
            disabled={loading}
            className="text-xs whitespace-nowrap bg-white hover:bg-teal-50 text-slate-700 hover:text-teal-800 border border-slate-200 hover:border-teal-300 rounded-lg px-3 py-1.5 transition shadow-2xs font-medium"
          >
            "{prompt}"
          </button>
        ))}
      </div>

      {/* Chat Area */}
      <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={clsx(
                'flex gap-3 max-w-3xl',
                msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
              )}
            >
              {/* Avatar */}
              <div
                className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold shadow-xs',
                  msg.sender === 'user'
                    ? 'bg-slate-900 text-white'
                    : 'bg-teal-600 text-white'
                )}
              >
                {msg.sender === 'user' ? 'U' : <SparklesIcon className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={clsx(
                  'rounded-2xl p-4 text-sm space-y-2.5 shadow-2xs leading-relaxed',
                  msg.sender === 'user'
                    ? 'bg-teal-600 text-white rounded-tr-xs'
                    : 'bg-slate-50 border border-slate-200/80 text-slate-800 rounded-tl-xs'
                )}
              >
                {/* Meta info header */}
                <div className="flex items-center justify-between gap-3 text-[11px] opacity-75">
                  <span className="font-semibold">
                    {msg.sender === 'user' ? 'You' : 'AuditMind Assistant'}
                  </span>
                  <span>{msg.timestamp}</span>
                </div>

                {/* Text Content */}
                <div className="whitespace-pre-line font-sans">{msg.text}</div>

                {/* Badges on assistant messages */}
                {msg.sender === 'assistant' && msg.id !== 'welcome' && (
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {msg.usedHistory ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-teal-800 bg-teal-100/80 px-2 py-0.5 rounded border border-teal-200">
                        <ClockIcon className="w-3 h-3" /> Grounded in multi-cycle SQL history
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-700 bg-slate-200/80 px-2 py-0.5 rounded border border-slate-300">
                        Current cycle isolated
                      </span>
                    )}

                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded border border-emerald-200">
                      <ShieldCheckIcon className="w-3 h-3" /> Verified DB Records
                    </span>
                  </div>
                )}

                {/* References Citing Cards */}
                {msg.references && msg.references.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-200 space-y-1.5">
                    <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider block">
                      Cited Sources & References:
                    </span>
                    <div className="grid grid-cols-1 gap-2">
                      {msg.references.map((ref, idx) => (
                        <div
                          key={idx}
                          className="bg-white p-2.5 rounded-lg border border-slate-200 text-xs shadow-2xs flex flex-col gap-1"
                        >
                          <div className="flex items-center justify-between gap-2 font-semibold text-slate-800">
                            <span className="flex items-center gap-1.5">
                              {ref.type === 'control' && <ShieldCheckIcon className="w-3.5 h-3.5 text-teal-600" />}
                              {ref.type === 'finding' && <DocumentTextIcon className="w-3.5 h-3.5 text-rose-600" />}
                              {ref.label}
                            </span>
                            {ref.page && (
                              <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded font-mono">
                                Page {ref.page}
                              </span>
                            )}
                          </div>
                          {ref.excerpt && (
                            <p className="text-[11px] text-slate-600 italic bg-slate-50 p-1.5 rounded border border-slate-100">
                              "{ref.excerpt}"
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 max-w-xl mr-auto">
              <div className="w-8 h-8 rounded-full bg-teal-600 text-white flex items-center justify-center shrink-0">
                <SparklesIcon className="w-4 h-4 animate-spin" />
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-xs p-4 text-xs text-slate-500 flex items-center gap-2">
                <LoadingSpinner />
                <span>Retrieving database records & formulating response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-slate-50 border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder={
                useHistory
                  ? 'Ask anything across all audit cycles (e.g., "Has SEC-014 been a problem before?")...'
                  : 'Ask about current cycle controls and evidence...'
              }
              disabled={loading}
              className="flex-1 bg-white border border-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 shadow-2xs"
            />
            <button
              type="submit"
              disabled={loading || !inputQuery.trim()}
              className="bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-xl px-5 py-3 transition shadow-xs flex items-center gap-1.5 font-medium text-sm"
            >
              <PaperAirplaneIcon className="w-4 h-4" />
              <span>Send</span>
            </button>
          </form>
          <p className="text-[11px] text-slate-500 mt-2 text-center">
            AuditMind AI uses deterministic queries & advisory LLM generation. Human review is required before findings are finalized.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Assistant;
