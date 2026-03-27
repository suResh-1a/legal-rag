"use client";

import React, { useState } from 'react';
import { LayoutDashboard, MessageSquare, ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SplitViewProps {
  left: React.ReactNode;
  right: React.ReactNode;
}

export const SplitView: React.FC<SplitViewProps> = ({ left, right }) => {
  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden">
      <div className="w-1/2 h-full border-r border-white/10 overflow-auto bg-black/20 p-4">
        {left}
      </div>
      <div className="w-1/2 h-full overflow-auto p-4 bg-black/40">
        {right}
      </div>
    </div>
  );
};

export const Navbar: React.FC<{ activeTab: string; onTabChange: (tab: string) => void }> = ({ activeTab, onTabChange }) => {
  return (
    <nav className="h-16 border-b border-white/10 glass-dark flex items-center justify-between px-6 z-50">
      <div className="flex items-center gap-2">
        <ShieldCheck className="text-blue-500 w-8 h-8" />
        <h1 className="text-xl font-bold tracking-tighter bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
          LEGAL-RAG NEPAL
        </h1>
      </div>
      <div className="flex gap-4">
        <button
          onClick={() => onTabChange('verify')}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg transition-all",
            activeTab === 'verify' ? "bg-blue-600/20 text-blue-400 border border-blue-500/30" : "text-gray-400 hover:text-white"
          )}
        >
          <LayoutDashboard size={18} />
          Verification
        </button>
        <button
          onClick={() => onTabChange('chat')}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg transition-all",
            activeTab === 'chat' ? "bg-purple-600/20 text-purple-400 border border-purple-500/30" : "text-gray-400 hover:text-white"
          )}
        >
          <MessageSquare size={18} />
          Legal Agent
        </button>
      </div>
      <div className="w-32"></div> {/* Spacer for balance */}
    </nav>
  );
};
