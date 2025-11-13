import { useState } from 'react';
import {
  ContentLayout,
  Header,
  SpaceBetween,
  Alert,
} from '@cloudscape-design/components';
import { Layout } from '../components/Common/Layout';
import { DocumentSelector } from '../components/InsightExtraction/DocumentSelector';
import { PromptInput } from '../components/InsightExtraction/PromptInput';
import { InsightDisplay } from '../components/InsightExtraction/InsightDisplay';
import { extractInsights } from '../services/api';
import type { InsightResult } from '../types/insight';

export const InsightsPage: React.FC = () => {
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [selectedFileName, setSelectedFileName] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [insightResult, setInsightResult] = useState<InsightResult | null>(null);

  const handleDocumentSelect = (docId: string, fileName: string) => {
    setSelectedDocId(docId);
    setSelectedFileName(fileName);
    setInsightResult(null);
    setError(null);
  };

  const handlePromptSubmit = async (prompt: string) => {
    if (!selectedDocId) {
      setError('Please select a document first');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await extractInsights({
        docId: selectedDocId,
        prompt,
      });

      setInsightResult(result);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to extract insights';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <ContentLayout
        header={
          <Header
            variant="h1"
            description="Select a document and enter a prompt to extract structured insights"
          >
            Extract Insights
          </Header>
        }
      >
        <SpaceBetween size="l">
          {error && (
            <Alert type="error" dismissible onDismiss={() => setError(null)}>
              {error}
            </Alert>
          )}

          <DocumentSelector
            onDocumentSelect={handleDocumentSelect}
            selectedDocId={selectedDocId}
          />

          {selectedDocId && (
            <>
              <Alert type="info">
                Selected document: <strong>{selectedFileName}</strong>
              </Alert>

              <PromptInput
                onSubmit={handlePromptSubmit}
                loading={loading}
                disabled={!selectedDocId}
              />
            </>
          )}

          <InsightDisplay insightResult={insightResult} loading={loading} />
        </SpaceBetween>
      </ContentLayout>
    </Layout>
  );
};
