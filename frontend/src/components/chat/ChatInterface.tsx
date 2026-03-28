"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Search, FileText, Calendar, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  token_usage?: { prompt: number, completion: number, total: number };
}

interface ReasoningStep {
  node: string;
  update: any;
}

export const ReasoningTrace: React.FC<{ steps: ReasoningStep[] }> = ({ steps }) => {
  return (
    <div className="flex flex-col gap-4 p-4 glass-dark h-full overflow-auto">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-2">
        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
        Thought Process
      </h3>
      <div className="space-y-6 relative mt-4">
        <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-blue-500/20" />
        {steps.map((step, i) => (
          <div key={i} className="relative pl-8 animate-in slide-in-from-left-2 duration-300">
             <div className="absolute left-0 top-1 w-6 h-6 rounded-full glass border-blue-500/50 flex items-center justify-center bg-black/50 z-10">
                {step.node === 'retriever' && <Search size={12} className="text-blue-400" />}
                {step.node === 'analyzer' && <FileText size={12} className="text-purple-400" />}
                {step.node === 'date_tool' && <Calendar size={12} className="text-amber-400" />}
                {step.node === 'synthesizer' && <CheckCircle2 size={12} className="text-green-400" />}
             </div>
             <div>
                <p className="text-xs font-bold text-gray-300 uppercase mb-1">{step.node.replace('_', ' ')}</p>
                <div className="text-sm text-gray-400 leading-relaxed italic">
                  {JSON.stringify(step.update.reasoning_steps?.[step.update.reasoning_steps.length - 1] || "Processing...")}
                </div>
             </div>
          </div>
        ))}
        {steps.length === 0 && <p className="text-sm text-gray-500 text-center py-10">Waiting for user question...</p>}
      </div>
    </div>
  );
};

export const ChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setReasoningSteps([]);
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let assistantContent = '';
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              const nodeName = Object.keys(data)[0];
              const updates = data[nodeName];
              
              setReasoningSteps(prev => [...prev, { node: nodeName, update: updates }]);
              
              if (nodeName === 'synthesizer' && updates.final_answer) {
                assistantContent = updates.final_answer;
                const tokenUsage = updates.token_usage;
                setMessages(prev => {
                   const last = prev[prev.length - 1];
                   if (last?.role === 'assistant') {
                      return [...prev.slice(0, -1), { role: 'assistant', content: assistantContent, token_usage: tokenUsage }];
                   }
                   return [...prev, { role: 'assistant', content: assistantContent, token_usage: tokenUsage }];
                });
              }
            } catch (pErr) {
              console.error("JSON Error resolving chunk:", pErr, line);
            }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'assistant', content: "An error occurred. Please try again." }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-full gap-6">
      {/* Chat Window */}
      <div className="flex-1 flex flex-col glass overflow-hidden">
        <div className="flex-1 overflow-auto p-6 space-y-6" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={cn(
              "flex flex-col w-full animate-in fade-in duration-500",
              m.role === 'user' ? "items-end" : "items-start"
            )}>
              <div className={cn(
                "max-w-[80%] p-4 rounded-2xl shadow-xl flex gap-3",
                m.role === 'user' ? "glass-dark border-blue-500/20" : "glass border-purple-500/20"
              )}>
                <div className="shrink-0 mt-1">
                  {m.role === 'user' ? <User size={20} className="text-blue-400" /> : <Bot size={20} className="text-purple-400" />}
                </div>
                <div className={cn(
                  "text-md leading-relaxed whitespace-pre-wrap",
                  m.role === 'assistant' ? "text-nepali text-lg text-white" : "text-gray-200"
                )}>
                  {m.content}
                </div>
              </div>
              {m.role === 'assistant' && m.token_usage && (
                <div className="text-[10px] text-gray-500 mt-2 px-2 flex items-center gap-1.5 opacity-70 border border-white/5 rounded-full px-3 py-1 bg-black/20">
                   <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                   <span className="font-semibold text-gray-400">{m.token_usage.total} tokens</span> 
                   ({m.token_usage.prompt} prompt, {m.token_usage.completion} completion)
                </div>
              )}
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start animate-pulse">
              <div className="glass p-4 rounded-2xl flex gap-3">
                <Bot size={20} className="text-purple-400" />
                <div className="flex gap-1 items-center">
                  <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
        </div>
        
        <form onSubmit={handleSubmit} className="p-4 border-t border-white/10 bg-black/30">
          <div className="relative group">
             <input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isTyping}
              placeholder="Ask anything about Nepalese Laws..."
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-6 pr-14 py-4 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all group-hover:bg-white/10"
             />
             <button 
              type="submit"
              className="absolute right-2 top-2 bottom-2 aspect-square bg-blue-600 hover:bg-blue-500 rounded-lg flex items-center justify-center transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
             >
               <Send size={20} className="text-white" />
             </button>
          </div>
        </form>
      </div>

      {/* Thought Process Panel (Beside Chat) */}
      <div className="w-80 h-full">
        <ReasoningTrace steps={reasoningSteps} />
      </div>
    </div>
  );
};
