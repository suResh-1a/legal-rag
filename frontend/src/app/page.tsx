"use client";

import React, { useState, useEffect } from 'react';
import { Navbar, SplitView } from '@/components/layout/AppLayout';
import { PdfViewer } from '@/components/verification/PdfViewer';
import { EditorForm } from '@/components/verification/EditorForm';
import { ChatInterface, ReasoningTrace } from '@/components/chat/ChatInterface';
import { Info, Diamond, Star, Square, Plus } from 'lucide-react';

const SymbolLegend = () => (
  <div className="flex flex-col gap-4 p-4 glass-dark h-full border-l border-white/10">
    <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-widest flex items-center gap-2">
      <Info className="w-4 h-4 text-amber-500" />
      Symbol Legend
    </h3>
    <div className="space-y-4 mt-2">
      <div className="flex items-start gap-3">
        <Diamond size={16} className="text-blue-400 mt-1" />
        <div>
          <p className="text-xs font-bold text-gray-300">Diamond (⊓)</p>
          <p className="text-xs text-gray-500">First Amendment (२०७५)</p>
        </div>
      </div>
      <div className="flex items-start gap-3">
        <Star size={16} className="text-purple-400 mt-1" />
        <div>
          <p className="text-xs font-bold text-gray-300">Star (Σ)</p>
          <p className="text-xs text-gray-500">Second Amendment (२०७७)</p>
        </div>
      </div>
      <div className="flex items-start gap-3">
        <Plus size={16} className="text-green-400 mt-1" />
        <div>
          <p className="text-xs font-bold text-gray-300">Plus (+)</p>
          <p className="text-xs text-gray-500">Recent Clause Insertion</p>
        </div>
      </div>
    </div>
    <div className="mt-auto p-4 glass bg-blue-500/10 border-blue-500/20 text-[10px] text-blue-300 leading-tight">
      <p>⚠️ Always verify the symbol with the footnotes at the bottom of the page before clicking 'Verify'.</p>
    </div>
  </div>
);

export default function Home() {
  const [activeTab, setActiveTab] = useState('verify');
  const [pendingSections, setPendingSections] = useState<any[]>([]);
  const [selectedSection, setSelectedSection] = useState<any>(null);
  const [reasoningSteps, setReasoningSteps] = useState<any[]>([]);

  useEffect(() => {
    if (activeTab === 'verify') {
      fetch('http://localhost:8000/api/sections/pending')
        .then(res => res.json())
        .then(data => {
          setPendingSections(data);
          if (data.length > 0 && !selectedSection) {
            setSelectedSection(data[0]);
          }
        });
    }
  }, [activeTab]);

  const handleVerify = async (data: any) => {
    try {
      const res = await fetch('http://localhost:8000/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        setPendingSections(prev => prev.filter(s => s._id !== data.mongo_id));
        setSelectedSection(null);
        alert("Section verified successfully!");
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <main className="flex flex-col min-h-screen bg-black text-white selection:bg-blue-500/30">
      <Navbar activeTab={activeTab} onTabChange={(tab) => setActiveTab(tab)} />
      
      <div className="flex-1">
        {activeTab === 'verify' ? (
          <div className="flex h-full">
            <div className="w-1/4 h-[calc(100vh-64px)] overflow-auto border-r border-white/10 p-4 space-y-2">
               <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-4">Pending ( {pendingSections.length} )</h3>
               {pendingSections.map(s => (
                 <button 
                  key={s._id}
                  onClick={() => setSelectedSection(s)}
                  className={`w-full text-left p-3 rounded-lg transition-all border ${selectedSection?._id === s._id ? 'bg-blue-600/10 border-blue-500/40' : 'bg-white/5 border-transparent hover:border-white/10'}`}
                 >
                   <p className="text-sm font-bold truncate">Dafa {s.dafa_no}</p>
                   <p className="text-[10px] text-gray-500 truncate">{s.act_name}</p>
                 </button>
               ))}
            </div>
            <div className="flex-1">
              <SplitView 
                left={<PdfViewer src={selectedSection?.source_image_path || ""} />}
                right={<EditorForm section={selectedSection} onVerify={handleVerify} />}
              />
            </div>
            <div className="w-1/5 h-[calc(100vh-64px)]">
              <SymbolLegend />
            </div>
          </div>
        ) : (
          <div className="flex h-full">
             <div className="flex-1 h-[calc(100vh-64px)] p-6">
                <ChatInterface />
             </div>
             <div className="w-1/4 h-[calc(100vh-64px)]">
                {/* Reasoning Trace should be dynamic based on ChatInterface state. 
                   For simplicity in this demo, let's assume it's integrated or passed via context.
                   Actually, let's just make ChatInterface handle its own local reasoning state for now.
                */}
                <ReasoningTrace steps={[]} /> {/* This will be empty until shared state is added, but UI is ready */}
             </div>
          </div>
        )}
      </div>
    </main>
  );
}
