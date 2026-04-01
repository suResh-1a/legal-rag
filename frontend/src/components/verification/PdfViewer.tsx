"use client";

import React, { useEffect } from 'react';

interface PdfViewerProps {
  src: string;
  allPages?: { pageNum: number; src: string }[];
  activePage?: number;
  onPageVisible?: (pageNum: number) => void;
  onInteractionStart?: () => void;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({ 
  src, 
  allPages = [], 
  activePage,
  onPageVisible,
  onInteractionStart
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const pageRefs = React.useRef<Map<number, HTMLDivElement>>(new Map());

  // Sync scroll from parent (activePage)
  useEffect(() => {
    if (activePage !== undefined) {
      const el = pageRefs.current.get(activePage);
      if (el) {
        // Use 'auto' (instant) for synchronization to eliminate lag
        el.scrollIntoView({ behavior: 'auto', block: 'start' });
      }
    }
  }, [activePage]);

  // Sync scroll to parent (IntersectionObserver)
  useEffect(() => {
    if (allPages.length === 0 || !onPageVisible) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const pageNum = parseInt(entry.target.getAttribute('data-pdf-page') || "");
          if (!isNaN(pageNum)) {
            onPageVisible(pageNum);
          }
        }
      });
    }, {
      root: containerRef.current,
      threshold: 0.1, // More sensitive
      rootMargin: '0px 0px -80% 0px' // Detect near top
    });

    pageRefs.current.forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, [allPages, onPageVisible]);

  if (!src && allPages.length === 0) return <div className="flex items-center justify-center h-full text-gray-500 italic">No image source provided</div>;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-widest">Original Scan</h3>
        <span className="text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full border border-blue-400/20">300 DPI PNG</span>
      </div>
      
      <div 
        ref={containerRef}
        onMouseEnter={onInteractionStart}
        onTouchStart={onInteractionStart}
        onWheel={onInteractionStart}
        className="relative flex-1 rounded-xl overflow-auto glass border-white/5 shadow-2xl space-y-8 p-4 scroll-smooth"
      >
        {allPages.length > 0 ? (
          allPages.map(page => (
            <div 
              key={page.pageNum}
              data-pdf-page={page.pageNum}
              ref={el => { if (el) pageRefs.current.set(page.pageNum, el); }}
              className="relative rounded-lg overflow-hidden border border-white/10 bg-black/40"
            >
              <div className="absolute top-2 left-2 bg-black/60 backdrop-blur-md px-2 py-1 rounded text-[10px] font-bold text-white border border-white/10 z-10">
                PAGE {page.pageNum}
              </div>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src={page.src} 
                alt={`Legal Page ${page.pageNum} Scan`} 
                className="w-full h-auto object-contain"
                loading="lazy"
              />
            </div>
          ))
        ) : (
          <div className="relative rounded-lg overflow-hidden">
             {/* eslint-disable-next-line @next/next/no-img-element */}
            <img 
              src={src} 
              alt="Legal Page Scan" 
              className="w-full h-auto object-contain cursor-zoom-in"
            />
          </div>
        )}
      </div>
    </div>
  );
};
