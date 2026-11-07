import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { DocumentItem, DocumentType, AnalyzeDocumentResponse } from '../api/types';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import AiSuggestionBanner from '../components/AiSuggestionBanner';
import {
  ArrowUpTrayIcon,
  DocumentArrowUpIcon,
  CpuChipIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

export const DocumentCentre: React.FC = () => {
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocumentType>('audit_report');
  const [version, setVersion] = useState<string>('1.0');
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  // Process & Analyze Action states
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);

  // Last Analysis Result Panel
  const [analysisResult, setAnalysisResult] = useState<AnalyzeDocumentResponse | null>(null);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load document records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileChange = (file: File) => {
    setUploadError(null);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'pdf' && ext !== 'txt') {
      setUploadError('Invalid file format. Only PDF and plain-text (TXT) files are permitted.');
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setUploadError('File exceeds the maximum permitted size of 20 MB.');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError('Please select a PDF or TXT file to upload.');
      return;
    }

    setUploading(true);
    setUploadError(null);
    try {
      const doc = await api.uploadDocument(selectedFile, docType, version);
      showToast(`Document "${doc.filename}" uploaded successfully.`, 'success');
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      loadDocuments();
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed.');
      showToast(err.message || 'Upload failed', 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async (docId: string) => {
    setProcessingId(docId);
    try {
      const updated = await api.processDocument(docId);
      showToast(`Text extraction complete: ${updated.filename}`, 'success');
      setDocuments((prev) => prev.map((d) => (d.id === docId ? updated : d)));
    } catch (err: any) {
      showToast(err.message || 'Document processing failed.', 'error');
    } finally {
      setProcessingId(null);
    }
  };

  const handleAnalyze = async (docId: string) => {
    setAnalyzingId(docId);
    setAnalysisResult(null);
    try {
      const result = await api.analyzeDocument(docId);
      setAnalysisResult(result);
      showToast(
        `Compliance analysis complete. ${result.findings_created} draft finding(s), ${result.evidence_items_created} evidence item(s) generated.`,
        'success'
      );
      loadDocuments();
    } catch (err: any) {
      showToast(err.message || 'Compliance analysis failed.', 'error');
    } finally {
      setAnalyzingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Processed':
        return 'bg-emerald-50 text-emerald-800 border-emerald-300';
      case 'Processing':
        return 'bg-amber-50 text-amber-800 border-amber-300 animate-pulse';
      case 'Failed':
        return 'bg-rose-50 text-rose-800 border-rose-300';
      case 'Uploaded':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Document Centre
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Secure ingest, PyMuPDF extraction, and rule-based / LLM compliance mapping pipeline
          </p>
        </div>
        <button
          type="button"
          onClick={loadDocuments}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh Documents
        </button>
      </div>

      {/* Upload Zone & Form */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 sm:p-6 space-y-4">
        <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <DocumentArrowUpIcon className="w-5 h-5 text-teal-600" />
          Upload Compliance Document or Audit Artifact
        </h2>

        <form onSubmit={handleUpload} className="space-y-4">
          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileChange(e.dataTransfer.files[0]);
              }
            }}
            className={clsx(
              'border-2 border-dashed rounded-xl p-6 sm:p-8 text-center transition flex flex-col items-center justify-center cursor-pointer',
              isDragOver
                ? 'border-teal-500 bg-teal-50/50'
                : 'border-slate-300 hover:border-teal-400 bg-slate-50/50'
            )}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept=".pdf,.txt"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileChange(e.target.files[0]);
                }
              }}
            />

            <div className="p-3 bg-white rounded-full text-teal-600 shadow-xs mb-2">
              <ArrowUpTrayIcon className="w-6 h-6" />
            </div>

            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-900">{selectedFile.name}</p>
                <p className="text-[11px] text-slate-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB • Ready to upload
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                  className="text-xs text-rose-600 font-semibold hover:underline mt-1"
                >
                  Choose different file
                </button>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-700">
                  <span className="text-teal-600 hover:underline">Click to browse</span> or drag and drop file here
                </p>
                <p className="text-[11px] text-slate-400">
                  Supported formats: PDF, TXT (Maximum file size: 20 MB)
                </p>
              </div>
            )}
          </div>

          {/* Upload Error Banner */}
          {uploadError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-center gap-2">
              <ExclamationTriangleIcon className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Form Fields: doc_type & version */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Document Classification (doc_type)
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value as DocumentType)}
                className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
              >
                <option value="audit_report">Audit Report (Extracts Findings)</option>
                <option value="evidence">Evidence (Maps to Controls)</option>
                <option value="policy">Policy (Baseline Governance)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Document Version
              </label>
              <input
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="e.g. 1.0 or 2026-Q1"
                className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
              />
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={!selectedFile || uploading}
                className={clsx(
                  'w-full py-2 px-4 rounded-lg text-xs font-bold text-white shadow-xs transition flex items-center justify-center gap-2',
                  !selectedFile || uploading
                    ? 'bg-slate-300 cursor-not-allowed'
                    : 'bg-teal-600 hover:bg-teal-700'
                )}
              >
                {uploading ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <ArrowUpTrayIcon className="w-4 h-4" />
                    <span>Upload Artifact</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Analysis Results Panel (if just run) */}
      {analysisResult && (
        <div className="bg-white rounded-xl border-2 border-teal-500/50 shadow-md p-5 space-y-4 animate-slide-up">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-teal-100 text-teal-800">
                <SparklesIcon className="w-5 h-5" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Analysis Pipeline Completed
                </h3>
                <p className="text-xs text-slate-500">
                  Target: {analysisResult.doc_type} • Mapped {analysisResult.control_matches} control(s)
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setAnalysisResult(null)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Dismiss
            </button>
          </div>

          <AiSuggestionBanner
            message={analysisResult.note}
            className="text-xs"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-700">Draft Findings Extracted</span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {analysisResult.findings_created}
                </p>
                <p className="text-[11px] text-slate-500">
                  AI suggestions waiting in review queue
                </p>
              </div>
              <Link
                to="/findings"
                className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-semibold shadow-xs flex items-center gap-1"
              >
                <span>Review Findings</span>
                <ArrowRightIcon className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-700">Evidence Items Mapped</span>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {analysisResult.evidence_items_created}
                </p>
                <p className="text-[11px] text-slate-500">
                  Classified against ISO 27001 controls
                </p>
              </div>
              <Link
                to="/evidence"
                className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-2xs flex items-center gap-1"
              >
                <span>Verify Evidence</span>
                <ArrowRightIcon className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Document Register Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Uploaded Documents & Artifacts
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Securely isolated by organisation ID • Processed using local text extraction
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-500">
            {documents.length} document(s)
          </span>
        </div>

        {loading ? (
          <div className="py-20 flex items-center justify-center">
            <LoadingSpinner size="md" message="Loading documents..." />
          </div>
        ) : error ? (
          <EmptyState title="Error Loading Documents" message={error} actionLabel="Retry" onAction={loadDocuments} />
        ) : documents.length === 0 ? (
          <EmptyState
            title="No Documents Uploaded"
            message="No documents found for your organisation. Upload a PDF or TXT audit report above to begin."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Processing Status</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {documents.map((doc) => {
                  const isProcessing = processingId === doc.id;
                  const isAnalyzing = analyzingId === doc.id;

                  return (
                    <tr key={doc.id} className="hover:bg-slate-50/60 transition">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <DocumentTextIcon className="w-4 h-4 text-slate-400 shrink-0" />
                          <span className="font-semibold text-slate-900 max-w-xs truncate" title={doc.filename}>
                            {doc.filename}
                          </span>
                        </div>
                        <span className="font-mono text-[10px] text-slate-400 block mt-0.5">
                          ID: {doc.id.slice(0, 8)}...
                        </span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="uppercase font-semibold text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
                          {doc.doc_type}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-600 font-mono">
                        {doc.version || '1.0'}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span
                          className={clsx(
                            'text-xs font-semibold px-2 py-0.5 rounded-full border',
                            getStatusBadge(doc.processing_status)
                          )}
                        >
                          {doc.processing_status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap text-right space-x-2">
                        {doc.processing_status === 'Uploaded' && (
                          <button
                            type="button"
                            disabled={isProcessing}
                            onClick={() => handleProcess(doc.id)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded-lg shadow-2xs transition"
                          >
                            <CpuChipIcon className="w-3.5 h-3.5" />
                            <span>{isProcessing ? 'Processing...' : 'Process Text'}</span>
                          </button>
                        )}

                        {doc.processing_status === 'Processed' && (
                          <button
                            type="button"
                            disabled={isAnalyzing}
                            onClick={() => handleAnalyze(doc.id)}
                            className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-xs transition"
                          >
                            <SparklesIcon className="w-3.5 h-3.5" />
                            <span>{isAnalyzing ? 'Analyzing...' : 'Analyze Document'}</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentCentre;
