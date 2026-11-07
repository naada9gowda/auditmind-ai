import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DocumentPage, DocumentItem } from '../api/types';
import { XMarkIcon, DocumentTextIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline';
import LoadingSpinner from './LoadingSpinner';

interface SourceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  documentId?: string | null;
  pageNumber?: number | null;
  highlightExcerpt?: string | null;
  controlCode?: string | null;
}

export const SourceDrawer: React.FC<SourceDrawerProps> = ({
  isOpen,
  onClose,
  documentId,
  pageNumber,
  highlightExcerpt,
  controlCode,
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pageData, setPageData] = useState<DocumentPage | null>(null);
  const [docMeta, setDocMeta] = useState<DocumentItem | null>(null);

  useEffect(() => {
    if (!isOpen || !documentId) {
      setPageData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    async function fetchPage() {
      setLoading(true);
      setError(null);
      try {
        const pageNum = pageNumber && pageNumber > 0 ? pageNumber : 1;
        const [page, doc] = await Promise.allSettled([
          api.getDocumentPage(documentId!, pageNum),
          api.getDocument(documentId!),
        ]);

        if (isMounted) {
          if (page.status === 'fulfilled') {
            setPageData(page.value);
          } else {
            // Provide friendly fallback text if page doesn't exist
            setPageData({
              document_id: documentId!,
              page_number: pageNum,
              text: highlightExcerpt
                ? `[Extracted Excerpt]:\n${highlightExcerpt}\n\n(Full raw document page text was not archived in document_pages table for this mock/record).`
                : 'Page text is not available for this document reference.',
            });
          }

          if (doc.status === 'fulfilled') {
            setDocMeta(doc.value);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load source document page.');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchPage();

    return () => {
      isMounted = false;
    };
  }, [isOpen, documentId, pageNumber, highlightExcerpt]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs transition-opacity animate-fade-in">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-white shadow-2xl flex flex-col border-l border-slate-200">
          {/* Header */}
          <div className="p-4 sm:p-6 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-teal-500/20 text-teal-400">
                <DocumentTextIcon className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-base font-semibold leading-6 text-white">
                  Source Evidence Viewer
                </h2>
                <p className="text-xs text-slate-300">
                  {docMeta?.filename || (documentId ? `Document ID: ${documentId.slice(0, 8)}...` : 'Document Page')}
                  {pageNumber ? ` • Page ${pageNumber}` : ''}
                  {controlCode ? ` • Control: ${controlCode}` : ''}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition"
              aria-label="Close drawer"
            >
              <XMarkIcon className="w-6 h-6" />
            </button>
          </div>

          {/* Subheader Metadata */}
          {docMeta && (
            <div className="px-6 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center gap-4">
                <span>
                  Type: <strong className="font-semibold text-slate-800 uppercase">{docMeta.doc_type}</strong>
                </span>
                <span>
                  Status: <strong className="font-semibold text-slate-800">{docMeta.processing_status}</strong>
                </span>
              </div>
              <span className="text-slate-400">
                Uploaded: {new Date(docMeta.uploaded_at).toLocaleDateString()}
              </span>
            </div>
          )}

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
            {loading ? (
              <div className="py-20 flex flex-col items-center justify-center">
                <LoadingSpinner size="lg" message="Loading source text..." />
              </div>
            ) : error ? (
              <div className="rounded-lg p-4 bg-rose-50 border border-rose-200 text-rose-800 text-sm">
                <p className="font-semibold">Error loading source content</p>
                <p className="mt-1 text-xs">{error}</p>
              </div>
            ) : (
              <>
                {/* Highlight excerpt callout */}
                {highlightExcerpt && (
                  <div className="rounded-lg border-2 border-teal-500/30 bg-teal-50/70 p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold uppercase tracking-wider text-teal-800 flex items-center gap-1">
                        <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" /> Cited Excerpt
                      </span>
                      {controlCode && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-teal-200 text-teal-900">
                          {controlCode}
                        </span>
                      )}
                    </div>
                    <blockquote className="text-sm font-medium text-slate-800 italic border-l-3 border-teal-600 pl-3 py-1">
                      "{highlightExcerpt}"
                    </blockquote>
                  </div>
                )}

                {/* Full Extracted Page Text */}
                <div className="bg-white rounded-lg border border-slate-200 shadow-xs p-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Page Content ({pageData?.page_number ? `Page ${pageData.page_number}` : 'Raw Extract'})
                    </span>
                    <span className="text-xs text-slate-400">
                      PyMuPDF Extracted Data
                    </span>
                  </div>

                  <div className="prose prose-sm max-w-none text-slate-700 font-mono text-xs leading-relaxed whitespace-pre-wrap select-text bg-slate-50 p-4 rounded border border-slate-100">
                    {pageData?.text || 'No text extracted on this page.'}
                  </div>
                </div>

                <div className="rounded-md bg-slate-100 p-3 text-xs text-slate-500 flex items-center gap-2">
                  <span className="font-semibold text-slate-700">Security Note:</span>
                  Document text is treated as untrusted data and presented verbatim for human audit verification.
                </div>
              </>
            )}
          </div>

          {/* Drawer Footer */}
          <div className="p-4 bg-white border-t border-slate-200 flex items-center justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition shadow-xs"
            >
              Close Viewer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SourceDrawer;
