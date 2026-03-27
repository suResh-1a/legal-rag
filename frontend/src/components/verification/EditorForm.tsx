"use client";

import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertTriangle, Save } from 'lucide-react';

interface SectionData {
  _id: string;
  dafa_no: string;
  title: string;
  content: string;
  amendment_history?: string;
  symbol_found?: string;
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

  return (
    <div className="flex flex-col gap-6 p-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
           <h2 className="text-2xl font-bold text-white">Dafa {formData.dafa_no}</h2>
           {formData.symbol_found && (
             <span className="flex items-center gap-1 text-xs bg-amber-500/20 text-amber-500 px-2 py-1 rounded border border-amber-500/30">
               <AlertTriangle size={12} />
               Amendment Marker: {formData.symbol_found}
             </span>
           )}
        </div>
        <button 
          onClick={handleSave}
          disabled={loading}
          className="btn-primary flex items-center gap-2"
        >
          {loading ? "Saving..." : <><CheckCircle size={18} /> Verify & Push</>}
        </button>
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
