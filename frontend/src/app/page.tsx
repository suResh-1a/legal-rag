"use client";

import React, { useState, useEffect } from 'react';
import { Navbar, SplitView } from '@/components/layout/AppLayout';
import { PdfViewer } from '@/components/verification/PdfViewer';
import { EditorForm } from '@/components/verification/EditorForm';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { IngestionDashboard } from '@/components/ingestion/IngestionDashboard';
import { Info, Diamond, Star, Plus, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
  
  const [sidebarMode, setSidebarMode] = useState<'dafa' | 'page' | 'document'>('dafa');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
  const [selectedPage, setSelectedPage] = useState<number | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);
  const [isAutoSyncEnabled, setIsAutoSyncEnabled] = useState(true);
  const scrollSourceRef = React.useRef<'text' | 'pdf' | null>(null);
  const manualNavRef = React.useRef(false);
  const docContainerRef = React.useRef<HTMLDivElement>(null);

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

  const pdfPages = React.useMemo(() => {
    return pages.map(([pageNum, sections]) => ({
      pageNum,
      src: sections[0]?.source_image_path || ""
    }));
  }, [pages]);

  const fullMarkdown = React.useMemo(() => {
    return filteredSections
      .sort((a, b) => {
        if (a.page_num !== b.page_num) return a.page_num - b.page_num;
        return a._id.localeCompare(b._id); // Secondary stable sort
      })
      .map(s => `## PAGE_REF:${s.page_num}:${s.type === 'table_row' ? 'Table' : 'Dafa '}${s.dafa_no}\n\n${s.content}\n\n---\n`)
      .join('\n');
  }, [filteredSections]);

  useEffect(() => {
    if (sidebarMode !== 'document' || !isAutoSyncEnabled) return;

    const root = docContainerRef.current;
    if (!root) return;

    const observer = new IntersectionObserver((entries) => {
      // Use ref to avoid stale closure and only sync if TEXT is active
      if (manualNavRef.current || scrollSourceRef.current !== 'text') return;
      
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const pageNum = parseInt(entry.target.getAttribute('data-page') || "");
          if (!isNaN(pageNum)) {
            setSelectedPage(pageNum);
          }
        }
      });
    }, { 
      root: root,
      threshold: 0.1, 
      rootMargin: '0px 0px -80% 0px' // More reactive detection window
    });

    const headings = root.querySelectorAll('[data-page]');
    headings.forEach(h => observer.observe(h));

    return () => observer.disconnect();
  }, [sidebarMode, fullMarkdown, isAutoSyncEnabled]);

  const handlePdfPageVisible = (pageNum: number) => {
    // Only sync if PDF is the active scroll source
    if (!isAutoSyncEnabled || manualNavRef.current || sidebarMode !== 'document' || scrollSourceRef.current !== 'pdf') return;
    
    if (selectedPage !== pageNum) {
      setSelectedPage(pageNum);
      
      const el = document.querySelector(`[data-page="${pageNum}"]`);
      if (el) {
        manualNavRef.current = true;
        // Use 'auto' (instant) for synchronization to eliminate lag
        el.scrollIntoView({ behavior: 'auto', block: 'start' });
        setTimeout(() => { manualNavRef.current = false; }, 500);
      }
    }
  };

  const scrollToPage = (pageNum: number) => {
    manualNavRef.current = true;
    setSelectedPage(pageNum);
    
    // Find the header for this page and scroll to it
    setTimeout(() => {
      const el = document.querySelector(`[data-page="${pageNum}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      setTimeout(() => { manualNavRef.current = false; }, 1000); // Re-enable sync after scroll
    }, 100);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(fullMarkdown);
    toast.success("Full document copied to clipboard!");
  };

  const handleMerge = async () => {
    if (selectedIds.length < 2) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/sections/merge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mongo_ids: selectedIds }),
      });
      if (res.ok) {
        // Refresh the list
        const updatedPending = await fetch(`${apiUrl}/api/sections/pending`).then(r => r.json());
        setPendingSections(updatedPending);
        setSelectedIds([]);
        setIsMultiSelectMode(false);
        toast.success("Sections merged successfully!");
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to merge sections.");
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

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
        toast.success("Section verified successfully!");
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
                  <button 
                     onClick={() => setSidebarMode('document')} 
                     className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${sidebarMode === 'document' ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' : 'bg-white/5 text-gray-400 hover:bg-white/10'}`}
                  >
                     Document
                  </button>
               </div>
               
                <div className="flex items-center justify-between mt-2 mb-2">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-widest leading-none">
                    Pending ( {sidebarMode === 'dafa' ? filteredSections.length : pages.length} )
                  </h3>
                  <button 
                    onClick={() => {
                      setIsMultiSelectMode(!isMultiSelectMode);
                      setSelectedIds([]);
                    }}
                    className={`text-[10px] px-2 py-1 rounded border transition-all ${isMultiSelectMode ? 'bg-blue-600 text-white border-blue-500' : 'text-gray-400 border-white/10 hover:bg-white/5'}`}
                  >
                    {isMultiSelectMode ? 'Cancel' : 'Multi-select'}
                  </button>
                </div>
                
                {isMultiSelectMode && selectedIds.length > 1 && (
                  <button 
                    onClick={handleMerge}
                    className="w-full mb-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold py-2 rounded-lg shadow-lg shadow-blue-600/20 flex items-center justify-center gap-2"
                  >
                    Merge {selectedIds.length} Selected
                  </button>
                )}
                
                <div className="flex-1 overflow-auto space-y-2 pr-2">
                  {sidebarMode === 'dafa' ? (
                    filteredSections.map(s => (
                      <button 
                       key={s._id}
                       onClick={() => isMultiSelectMode ? handleToggleSelect(s._id) : setSelectedSection(s)}
                       className={`w-full text-left p-3 rounded-lg transition-all border ${
                         (!isMultiSelectMode && selectedSection?._id === s._id) || (isMultiSelectMode && selectedIds.includes(s._id))
                          ? 'bg-blue-600/10 border-blue-500/40' 
                          : 'bg-white/5 border-transparent hover:border-white/10'
                       }`}
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-bold truncate">Dafa {s.dafa_no}</p>
                          {isMultiSelectMode && (
                            <div className={`w-4 h-4 rounded border flex items-center justify-center ${selectedIds.includes(s._id) ? 'bg-blue-600 border-blue-500' : 'border-white/20'}`}>
                              {selectedIds.includes(s._id) && <div className="w-1.5 h-1.5 bg-white rounded-full" />}
                            </div>
                          )}
                        </div>
                        <p className="text-[10px] text-gray-500 truncate">{s.act_name}</p>
                        {s.type === 'table_row' && (
                          <span className="inline-block mt-1 text-[8px] bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30 uppercase font-bold tracking-tighter">Table Row</span>
                        )}
                      </button>
                    ))
                  ) : sidebarMode === 'page' ? (
                    pages.map(([pageNum, sections]) => (
                       <button 
                         key={pageNum}
                         onClick={() => setSelectedPage(pageNum)}
                         className={`w-full text-left p-3 rounded-lg transition-all border ${selectedPage === pageNum ? 'bg-blue-600/10 border-blue-500/40' : 'bg-white/5 border-transparent hover:border-white/10'}`}
                       >
                         <p className="text-sm font-bold">Page {pageNum}</p>
                         <p className="text-[10px] text-gray-500 truncate">{sections.length} items to verify</p>
                       </button>
                     ))
                   ) : (
                     <div className="p-4 bg-white/5 rounded-xl border border-white/10 text-center">
                        <FileText size={24} className="mx-auto mb-2 text-blue-400/50" />
                        <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Document View</p>
                        <p className="text-[8px] text-gray-500 mt-1">Reading full joined extraction...</p>
                        <button 
                          onClick={copyToClipboard}
                          className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-500 text-[10px] font-bold rounded-lg transition-colors"
                        >
                          Copy Full Text
                        </button>
                     </div>
                   )}
                </div>
            </div>
            
            <div className="flex-1">
              {sidebarMode === 'dafa' ? (
                <SplitView 
                  left={<PdfViewer src={selectedSection?.source_image_path || ""} />}
                  right={<EditorForm section={selectedSection} onVerify={handleVerify} />}
                />
              ) : sidebarMode === 'page' ? (
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
              ) : (
                <SplitView 
                  left={
                    <PdfViewer 
                      src={pages.find(p => p[0] === (selectedPage || 1))?.[1][0]?.source_image_path || ""} 
                      allPages={pdfPages}
                      activePage={scrollSourceRef.current === 'text' ? (selectedPage || undefined) : undefined}
                      onPageVisible={handlePdfPageVisible}
                      onInteractionStart={() => { scrollSourceRef.current = 'pdf'; }}
                    />
                  }
                  right={
                    <div 
                      ref={docContainerRef} 
                      onMouseEnter={() => { scrollSourceRef.current = 'text'; }}
                      onTouchStart={() => { scrollSourceRef.current = 'text'; }}
                      onWheel={() => { scrollSourceRef.current = 'text'; }}
                      className="h-full overflow-auto p-8 bg-[#0a0a0a] border-l border-white/5 scroll-smooth relative"
                    >
                      <div className="max-w-3xl mx-auto">
                        <div className="sticky top-0 z-20 bg-[#0a0a0a]/90 backdrop-blur-md flex items-center justify-between mb-8 border-b border-white/10 pb-4 pt-4 -mt-4 shadow-xl">
                           <h1 className="text-xl font-bold text-gray-300">Unified Document Preview</h1>
                           <div className="flex items-center gap-4">
                              <div className="flex items-center gap-2 mr-4 bg-white/5 px-2 py-1 rounded-lg border border-white/10">
                                 <span className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">Auto-Sync</span>
                                 <button 
                                   onClick={() => setIsAutoSyncEnabled(!isAutoSyncEnabled)}
                                   className={`w-8 h-4 rounded-full relative transition-colors ${isAutoSyncEnabled ? 'bg-blue-600' : 'bg-gray-700'}`}
                                 >
                                    <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-all ${isAutoSyncEnabled ? 'left-4.5' : 'left-0.5'}`} />
                                 </button>
                              </div>
                              <span className="text-[10px] text-gray-500 font-mono">PAGE {selectedPage || (pages[0]?.[0])} / {pages[pages.length-1]?.[0]}</span>
                              <div className="flex gap-1">
                                 <button 
                                   onClick={() => {
                                     const idx = pages.findIndex(p => p[0] === selectedPage);
                                      if (idx > 0) scrollToPage(pages[idx-1][0]);
                                   }} 
                                   className="p-1 hover:bg-white/10 rounded disabled:opacity-30"
                                   disabled={pages.findIndex(p => p[0] === selectedPage) <= 0}
                                 >◀</button>
                                 <button 
                                   onClick={() => {
                                      const idx = pages.findIndex(p => p[0] === selectedPage);
                                      if (idx < pages.length - 1 && idx !== -1) scrollToPage(pages[idx+1][0]);
                                      else if (idx === -1 && pages.length > 0) scrollToPage(pages[0][0]);
                                   }} 
                                   className="p-1 hover:bg-white/10 rounded disabled:opacity-30"
                                   disabled={pages.findIndex(p => p[0] === selectedPage) >= pages.length - 1}
                                 >▶</button>
                              </div>
                           </div>
                        </div>
                        <div className="prose prose-invert prose-blue max-w-none prose-sm prose-headings:text-blue-400 prose-headings:font-bold prose-p:text-gray-300 prose-p:text-nepali prose-p:text-lg prose-table:border prose-table:border-white/10">
                           <ReactMarkdown 
                              remarkPlugins={[remarkGfm]}
                              components={{
                                 table: ({node, ...props}) => <div className="overflow-x-auto my-6"><table className="w-full text-left border-collapse border border-white/10" {...props} /></div>,
                                 th: ({node, ...props}) => <th className="border border-white/10 p-2 font-bold bg-white/5" {...props} />,
                                 td: ({node, ...props}) => <td className="border border-white/10 p-2 text-gray-400" {...props} />,
                                 h2: ({node, ...props}) => {
                                    const children = React.Children.toArray(props.children);
                                    const firstChild = String(children[0] || "");
                                    
                                    if (firstChild.startsWith('PAGE_REF:')) {
                                       const parts = firstChild.split(':');
                                       const pageNum = parts[1];
                                       const labelPrefix = parts.slice(2).join(':');
                                       // Merge remaining children back
                                       const restChildren = children.slice(1);
                                       
                                       return (
                                          <h2 
                                            data-page={pageNum} 
                                            className="text-lg font-bold mt-10 mb-4 text-blue-400 border-l-4 border-blue-600 pl-3 scroll-mt-24"
                                          >
                                             {labelPrefix}
                                             {restChildren}
                                          </h2>
                                       );
                                    }
                                    return <h2 className="text-lg font-bold mt-10 mb-4 text-blue-400 border-l-4 border-blue-600 pl-3" {...props} />;
                                 },
                                 hr: ({node, ...props}) => <hr className="my-8 border-white/10" {...props} />,
                                 p: ({node, ...props}) => <p className="mb-6 leading-relaxed" {...props} />,
                              }}
                           >
                              {fullMarkdown}
                           </ReactMarkdown>
                        </div>
                      </div>
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
