import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { UserProvider } from './context/UserContext';
import { ToastProvider } from './components/Toast';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { ComplianceMonitor } from './pages/ComplianceMonitor';
import { FindingsReview } from './pages/FindingsReview';
import { RemediationTracker } from './pages/RemediationTracker';
import { EvidenceVerifier } from './pages/EvidenceVerifier';
import { DocumentCentre } from './pages/DocumentCentre';
import { RiskIntelligence } from './pages/RiskIntelligence';
import { AuditHistory } from './pages/AuditHistory';
import { AuditAssistant } from './pages/AuditAssistant';
import { MemoryExplorer } from './pages/MemoryExplorer';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <UserProvider>
        <ToastProvider>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="compliance" element={<ComplianceMonitor />} />
              <Route path="findings" element={<FindingsReview />} />
              <Route path="remediations" element={<RemediationTracker />} />
              <Route path="evidence" element={<EvidenceVerifier />} />
              <Route path="documents" element={<DocumentCentre />} />
              <Route path="risks" element={<RiskIntelligence />} />
              <Route path="history" element={<AuditHistory />} />
              <Route path="assistant" element={<AuditAssistant />} />
              <Route path="memory" element={<MemoryExplorer />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ToastProvider>
      </UserProvider>
    </BrowserRouter>
  );
};

export default App;
