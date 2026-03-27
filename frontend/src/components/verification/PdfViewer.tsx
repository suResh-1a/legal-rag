"use client";

import React from 'react';

interface PdfViewerProps {
  src: string;
}

export const PdfViewer: React.FC<PdfViewerProps> = ({ src }) => {
  if (!src) return <div className="flex items-center justify-center h-full text-gray-500 italic">No image source provided</div>;

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-widest">Original Scan</h3>
        <span className="text-xs text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded-full border border-blue-400/20">300 DPI PNG</span>
      </div>
      <div className="relative flex-1 rounded-xl overflow-hidden glass border-white/5 shadow-2xl">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img 
          src={src} 
          alt="Legal Page Scan" 
          className="w-full h-auto object-contain cursor-zoom-in"
        />
      </div>
    </div>
  );
};
