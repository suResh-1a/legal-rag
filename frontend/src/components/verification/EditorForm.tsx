"use client";

import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { CheckCircle, AlertTriangle, Save, RefreshCw } from 'lucide-react';

interface SectionData {
  _id: string;
  dafa_no: string;
  title: string;
  content: string;
  amendment_history?: string;
  symbol_found?: string;
  is_incomplete?: boolean;
  type?: string;
}

interface EditorFormProps {
  section: SectionData | null;
  onVerify: (data: any) => Promise<void>;
}

export const EditorForm: React.FC<EditorFormProps> = ({ section, onVerify }) => {
  const [formData, setFormData] = useState<SectionData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setFormData(section);
  }, [section]);

  if (!formData) return <div className="h-full flex items-center justify-center text-gray-500">Select a section to verify</div>;

  const handleSave = async () => {
    setLoading(true);
    await onVerify({
      mongo_id: formData._id,
      content: formData.content,
      amendment_history: formData.amendment_history
    });
    setLoading(false);
  };

  const handleRedo = async () => {
    if (!confirm("This will delete all current pending sections for this page and re-run Gemini extraction. Continue?")) return;
    
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/sections/redo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mongo_id: formData._id }),
      });
      if (res.ok) {
        toast.success("Page re-extraction started! Please wait a few seconds and refresh.");
      } else {
        toast.error("Failed to start re-extraction.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Error connecting to server.");
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col gap-6 p-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
           <h2 className="text-2xl font-bold text-white">Dafa {formData.dafa_no}</h2>
           {formData.type === 'table_row' && (
             <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-1 rounded border border-blue-500/30 uppercase font-bold tracking-wider">Table Row</span>
           )}
           {formData.symbol_found && (
             <span className="flex items-center gap-1 text-xs bg-amber-500/20 text-amber-500 px-2 py-1 rounded border border-amber-500/30">
               <AlertTriangle size={12} />
               Amendment Marker: {formData.symbol_found}
             </span>
           )}
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={handleRedo}
            disabled={loading}
            className="p-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-gray-400 hover:text-white transition-all disabled:opacity-50"
            title="Redo Page Extraction"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
          <button 
            onClick={handleSave}
            disabled={loading}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? "Saving..." : <><CheckCircle size={18} /> Verify & Push</>}
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Section Title</label>
          <input 
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            value={formData.title || ""}
            onChange={(e) => setFormData({...formData, title: e.target.value})}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Content (Nepali Unicode)</label>
          <textarea 
            className="w-full h-64 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white text-nepali text-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            value={formData.content}
            onChange={(e) => setFormData({...formData, content: e.target.value})}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Amendment History (Footnote Data)</label>
          <textarea 
            className="w-full h-24 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            value={formData.amendment_history || ""}
            onChange={(e) => setFormData({...formData, amendment_history: e.target.value})}
            placeholder="No amendment history found..."
          />
        </div>
      </div>
    </div>
  );
};
