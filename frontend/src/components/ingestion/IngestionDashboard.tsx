"use client";

import React, { useState, useEffect } from 'react';
import { UploadCloud, FileType, CheckCircle, AlertTriangle, Loader2, ArrowRight, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export const IngestionDashboard = () => {
  const [jobs, setJobs] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  
  // Poll extraction jobs
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/extraction-jobs');
        if (res.ok) {
          const data = await res.json();
          setJobs(data);
        }
      } catch (e) {
        console.error("Error fetching jobs:", e);
      }
    };
    
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm("Are you sure you want to completely delete this document and all its extracted legal sections from the database?")) return;
    
    try {
      const res = await fetch(`http://localhost:8000/api/extraction-jobs/${jobId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setJobs(prev => prev.filter(j => j.job_id !== jobId));
      } else {
        alert("Failed to delete the document.");
      }
    } catch (err) {
      console.error("Error deleting job:", err);
      alert("Error connecting to server to delete.");
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      alert("Please upload a valid PDF file.");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/upload-pdf', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        // Trigger immediate fetch
        const jobsRes = await fetch('http://localhost:8000/api/extraction-jobs');
        if (jobsRes.ok) setJobs(await jobsRes.json());
      } else {
        alert("Upload failed.");
      }
    } catch (err) {
      console.error(err);
      alert("Error connecting to server.");
    } finally {
      setIsUploading(false);
      // Reset input
      if (e.target) e.target.value = "";
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] p-8 max-w-6xl mx-auto w-full gap-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold bg-gradient-to-r from-amber-400 to-orange-500 bg-clip-text text-transparent mb-2">
          Knowledge Ingestion Hub
        </h2>
        <p className="text-gray-400">Upload raw Legal PDFs to automatically extract, stitch, and seed them into the Vector Database using Background LLM Workers.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 flex-1 min-h-0">
        
        {/* Upload Zone */}
        <div className="col-span-1 border-2 border-dashed border-white/20 rounded-2xl flex flex-col items-center justify-center p-8 bg-white/5 hover:bg-white/10 transition-colors relative group">
           <input 
             type="file" 
             accept=".pdf" 
             className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
             onChange={handleFileUpload}
             disabled={isUploading}
           />
           {isUploading ? (
             <Loader2 className="w-16 h-16 text-amber-500 animate-spin mb-4" />
           ) : (
             <UploadCloud className="w-16 h-16 text-gray-500 group-hover:text-amber-500 transition-colors mb-4" />
           )}
           <h3 className="text-xl font-semibold mb-2">{isUploading ? "Uploading..." : "Click or Drag PDF"}</h3>
           <p className="text-sm text-gray-500 text-center">Automatically runs Gemini Vision Extraction in the background.</p>
        </div>

        {/* Jobs List */}
        <div className="col-span-2 bg-black/20 rounded-2xl border border-white/10 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-white/10 glass-dark flex justify-between items-center">
             <h3 className="font-semibold text-gray-300">Active & Recent Jobs</h3>
             <div className="flex items-center gap-2">
               <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
               <span className="text-xs text-gray-500">Live Queue</span>
             </div>
          </div>
          
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {jobs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-3">
                 <FileType size={48} className="opacity-20" />
                 <p>No jobs in queue.</p>
              </div>
            ) : (
              jobs.map(job => {
                const isCompleted = job.status === 'completed';
                const isFailed = job.status === 'failed';
                const isProcessing = job.status === 'processing';
                
                const percent = job.total_pages > 0 
                  ? Math.round((job.processed_pages / job.total_pages) * 100) 
                  : 0;

                return (
                  <div key={job.job_id} className="p-5 rounded-xl border border-white/5 bg-white/5 relative overflow-hidden">
                    {/* Background Progress Bar */}
                    {isProcessing && (
                      <div 
                        className="absolute inset-y-0 left-0 bg-amber-500/10 transition-all duration-1000 ease-in-out"
                        style={{ width: `${percent}%` }}
                      />
                    )}
                    
                    <div className="relative z-10 flex justify-between items-start mb-3">
                       <div>
                         <h4 className="font-bold text-gray-200">{job.filename}</h4>
                         <p className="text-xs text-gray-500 mt-1 font-mono">{job.job_id.split('-')[0]}</p>
                       </div>
                       
                       <div className="flex items-center gap-3">
                         <div className={cn(
                           "px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5",
                           isCompleted ? "bg-green-500/20 text-green-400 border-green-500/30" :
                           isFailed ? "bg-red-500/20 text-red-400 border-red-500/30" :
                           "bg-amber-500/20 text-amber-400 border-amber-500/30"
                         )}>
                           {isProcessing && <Loader2 size={12} className="animate-spin" />}
                           {isCompleted && <CheckCircle size={12} />}
                           {isFailed && <AlertTriangle size={12} />}
                           {job.status.toUpperCase()}
                         </div>
                         <button 
                           onClick={() => handleDeleteJob(job.job_id)}
                           className="p-1.5 rounded-md bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 border border-transparent hover:border-red-500/30 transition-all"
                           title="Delete Document Data"
                         >
                           <Trash2 size={14} />
                         </button>
                       </div>
                    </div>

                    <div className="relative z-10 flex items-end justify-between">
                       <div className="flex-1 mr-6">
                         <div className="flex justify-between text-xs text-gray-400 mb-2">
                           <span>{job.progress_message}</span>
                           {job.total_pages > 0 && <span>{job.processed_pages} / {job.total_pages} Pages</span>}
                         </div>
                         {/* Foreground thin bar */}
                         {!isCompleted && !isFailed && job.total_pages > 0 && (
                           <div className="h-1.5 w-full bg-black/40 rounded-full overflow-hidden">
                             <div 
                               className="h-full bg-amber-400 transition-all duration-1000"
                               style={{ width: `${percent}%` }}
                             />
                           </div>
                         )}
                       </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
