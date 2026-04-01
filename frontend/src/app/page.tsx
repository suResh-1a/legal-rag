"use client";

import React, { useState, useEffect } from 'react';
import { Navbar, SplitView } from '@/components/layout/AppLayout';
import { PdfViewer } from '@/components/verification/PdfViewer';
import { EditorForm } from '@/components/verification/EditorForm';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { IngestionDashboard } from '@/components/ingestion/IngestionDashboard';
import { Info, Diamond, Star, Plus, FileText } from 'lucide-react';

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
      <p>⚠️ Always verify the symbol with the footnotes at the bottom of the page before clicking &apos;Verify&apos;.</p>
    </div>
  </div>
);

export default function Home() {
  const [activeTab, setActiveTab] = useState('verify');
  const [pendingSections, setPendingSections] = useState<any[]>([]);
  const [selectedSection, setSelectedSection] = useState<any>(null);
  
  const [sidebarMode, setSidebarMode] = useState<'dafa' | 'page'>('dafa');
  const [selectedPage, setSelectedPage] = useState<number | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    if (activeTab === 'verify') {
      fetch(`${apiUrl}/api/sections/pending`)
        .then(res => res.json())
        .then(data => {
          setPendingSections(data);
          if (data.length > 0) {
            if (!selectedSection) setSelectedSection(data[0]);
            setSelectedPage(prev => prev === null ? data[0].page_num : prev);
          }
        });
    }
  }, [activeTab]);

  const documents = React.useMemo(() => {
     const docs = new Set<string>();
     pendingSections.forEach(s => {
        docs.add(s.document_filename || s.act_name || "Unknown Document");
     });
     return Array.from(docs).sort();
  }, [pendingSections]);

  useEffect(() => {
     if (documents.length > 0 && (!selectedDocument || !documents.includes(selectedDocument))) {
        setSelectedDocument(documents[0]);
     } else if (documents.length === 0) {
        setSelectedDocument(null);
     }
  }, [documents, selectedDocument]);

  const filteredSections = React.useMemo(() => {
     if (!selectedDocument) return [];
     return pendingSections.filter(s => (s.document_filename || s.act_name || "Unknown Document") === selectedDocument);
  }, [pendingSections, selectedDocument]);

  useEffect(() => {
     if (filteredSections.length > 0) {
        if (!selectedSection || !filteredSections.find(s => s._id === selectedSection._id)) {
           setSelectedSection(filteredSections[0]);
        }
        if (selectedPage === null || !filteredSections.find(s => s.page_num === selectedPage)) {
           setSelectedPage(filteredSections[0].page_num);
        }
     }
  }, [filteredSections, selectedDocument]);

  const pages = React.useMemo(() => {
    const grouped = new Map<number, any[]>();
    filteredSections.forEach(s => {
      if(!grouped.has(s.page_num)) grouped.set(s.page_num, []);
      grouped.get(s.page_num)!.push(s);
    });
    return Array.from(grouped.entries()).sort((a,b) => a[0] - b[0]);
  }, [filteredSections]);

  const handleVerify = async (data: any) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        setPendingSections(prev => prev.filter(s => s._id !== data.mongo_id));
        if (sidebarMode === 'dafa') {
           setSelectedSection(null);
        }
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
            <div className="w-[260px] flex-shrink-0 h-[calc(100vh-64px)] overflow-auto border-r border-white/10 p-4 flex flex-col gap-2 relative">
               
               {/* Global Document Selector */}
               {documents.length > 0 && (
                 <div className="mb-4 bg-white/5 p-3 rounded-xl border border-white/10">
                   <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <FileText size={12} className="text-amber-500" />
                      Select Document
                   </p>
                   <select 
                     value={selectedDocument || ""} 
                     onChange={(e) => setSelectedDocument(e.target.value)}
                     className="w-full bg-black/40 border border-white/10 text-xs text-gray-300 rounded-lg p-2 outline-none focus:border-blue-500/50"
                   >
                     {documents.map(doc => (
                       <option key={doc} value={doc}>{doc}</option>
                     ))}
                   </select>
                 </div>
               )}

               <div className="flex gap-2 mb-2">
                  <button 
                     onClick={() => setSidebarMode('dafa')} 
                     className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${sidebarMode === 'dafa' ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}
                  >
                     Dafa Wise
                  </button>
                  <button 
                     onClick={() => setSidebarMode('page')} 
                     className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${sidebarMode === 'page' ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}
                  >
                     Page Wise
                  </button>
               </div>
               
               <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mt-2 mb-2">
                 Pending ( {sidebarMode === 'dafa' ? filteredSections.length : pages.length} )
               </h3>
               
               <div className="flex-1 overflow-auto space-y-2 pr-2">
                 {sidebarMode === 'dafa' ? (
                   filteredSections.map(s => (
                     <button 
                      key={s._id}
                      onClick={() => setSelectedSection(s)}
                      className={`w-full text-left p-3 rounded-lg transition-all border ${selectedSection?._id === s._id ? 'bg-blue-600/10 border-blue-500/40' : 'bg-white/5 border-transparent hover:border-white/10'}`}
                     >
                       <p className="text-sm font-bold truncate">Dafa {s.dafa_no}</p>
                       <p className="text-[10px] text-gray-500 truncate">{s.act_name}</p>
                     </button>
                   ))
                 ) : (
                   pages.map(([pageNum, sections]) => (
                     <button 
                      key={pageNum}
                      onClick={() => setSelectedPage(pageNum)}
                      className={`w-full text-left p-3 rounded-lg transition-all border ${selectedPage === pageNum ? 'bg-blue-600/10 border-blue-500/40' : 'bg-white/5 border-transparent hover:border-white/10'}`}
                     >
                       <p className="text-sm font-bold truncate">Page {pageNum}</p>
                       <p className="text-[10px] text-gray-500 truncate">{sections.length} items to verify</p>
                     </button>
                   ))
                 )}
               </div>
            </div>
            
            <div className="flex-1">
              {sidebarMode === 'dafa' ? (
                <SplitView 
                  left={<PdfViewer src={selectedSection?.source_image_path || ""} />}
                  right={<EditorForm section={selectedSection} onVerify={handleVerify} />}
                />
              ) : (
                <SplitView 
                  left={<PdfViewer src={pages.find(p => p[0] === selectedPage)?.[1][0]?.source_image_path || ""} />}
                  right={
                    <div className="space-y-6 pb-20">
                      {pages.find(p => p[0] === selectedPage)?.[1].map((s: any) => (
                        <div key={s._id} className="bg-black/20 rounded-xl border border-white/5 shadow-sm p-2">
                           <EditorForm section={s} onVerify={handleVerify} />
                        </div>
                      ))}
                      {(!pages.find(p => p[0] === selectedPage)?.[1] || pages.find(p => p[0] === selectedPage)?.[1].length === 0) && (
                        <div className="h-full flex items-center justify-center text-gray-500 mt-20">Select a page to verify</div>
                      )}
                    </div>
                  }
                />
              )}
            </div>
            
            <div className="w-[240px] flex-shrink-0 h-[calc(100vh-64px)]">
              <SymbolLegend />
            </div>
          </div>
        ) : activeTab === 'ingestion' ? (
          <div className="flex h-full w-full">
             <IngestionDashboard />
          </div>
        ) : (
          <div className="flex h-full">
             <div className="flex-1 h-[calc(100vh-64px)] p-6">
                <ChatInterface />
             </div>
          </div>
        )}
      </div>
    </main>
  );
}
