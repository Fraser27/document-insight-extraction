import { useEffect, useState } from 'react';
import {
  Container,
  ProgressBar,
  SpaceBetween,
  Box,
  StatusIndicator,
  ExpandableSection,
  Alert,
} from '@cloudscape-design/components';
import { websocketService } from '../../services/websocket';
import type { ProgressMessage } from '../../services/websocket';
import { getAuthHeaders } from '../../utils/authUtils';
import { getConfig } from '../../config/config';

interface ProcessingError {
  page: number;
  message: string;
  timestamp: number;
}

interface UploadProgressProps {
  docId: string;
  fileName: string;
  onComplete?: (docId: string) => void;
  onError?: (error: string) => void;
}

export const UploadProgress: React.FC<UploadProgressProps> = ({
  docId,
  fileName,
  onComplete,
  onError,
}) => {
  const [progress, setProgress] = useState(0);
  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [pagesProcessed, setPagesProcessed] = useState(0);
  const [status, setStatus] = useState<'processing' | 'completed' | 'error'>('processing');
  const [statusMessage, setStatusMessage] = useState('Waiting for processing to start...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [processingErrors, setProcessingErrors] = useState<ProcessingError[]>([]);

  useEffect(() => {
    // Subscribe to WebSocket messages
    const unsubscribe = websocketService.onMessage((message: ProgressMessage) => {
      // Only handle messages for this document
      if (message.docId !== docId) {
        return;
      }

      switch (message.status) {
        case 'processing_started':
          setStatus('processing');
          setTotalPages(message.totalPages || null);
          setStatusMessage(`Processing started - ${message.totalPages || 0} pages detected`);
          break;

        case 'progress':
          if (message.pagesProcessed && message.totalPages) {
            setPagesProcessed(message.pagesProcessed);
            setTotalPages(message.totalPages);
            const progressPercent = (message.pagesProcessed / message.totalPages) * 100;
            setProgress(progressPercent);
            setStatusMessage(
              `Processing page ${message.pagesProcessed} of ${message.totalPages}`
            );
          }
          break;

        case 'processing_complete':
          setStatus('completed');
          setProgress(100);
          setStatusMessage('Processing completed successfully');
          
          // Fetch final status to check for any errors
          fetchProcessingStatus();
          
          // Notify parent component
          setTimeout(() => {
            onComplete?.(docId);
          }, 2000); // Wait 2 seconds before notifying
          break;

        case 'error':
          setStatus('error');
          const errMsg = message.message || 'An error occurred during processing';
          setErrorMessage(errMsg);
          setStatusMessage('Processing failed');
          
          // Fetch detailed error information
          fetchProcessingStatus();
          
          onError?.(errMsg);
          break;
      }
    });

    // Cleanup subscription on unmount
    return () => {
      unsubscribe();
    };
  }, [docId, onComplete, onError]);

  const fetchProcessingStatus = async () => {
    try {
      const config = getConfig();
      const headers = await getAuthHeaders();
      const response = await fetch(`${config.apiUrl}/documents/${docId}/status`, {
        headers,
      });

      if (response.ok) {
        const statusData = await response.json();
        
        // Check for errors in the processing
        if (statusData.errors && statusData.errors.length > 0) {
          setProcessingErrors(statusData.errors);
        }
        
        // Update error message if present
        if (statusData.errorMessage) {
          setErrorMessage(statusData.errorMessage);
        }
      }
    } catch (error) {
      console.error('Error fetching processing status:', error);
    }
  };

  const getStatusIndicator = () => {
    switch (status) {
      case 'processing':
        return <StatusIndicator type="in-progress">Processing</StatusIndicator>;
      case 'completed':
        return <StatusIndicator type="success">Completed</StatusIndicator>;
      case 'error':
        return <StatusIndicator type="error">Failed</StatusIndicator>;
    }
  };

  return (
    <Container
      header={
        <SpaceBetween size="xs">
          <Box variant="h3">Document Processing</Box>
          {getStatusIndicator()}
        </SpaceBetween>
      }
    >
      <SpaceBetween size="m">
        <Box>
          <Box variant="awsui-key-label">File name</Box>
          <Box>{fileName}</Box>
        </Box>

        {totalPages !== null && (
          <Box>
            <Box variant="awsui-key-label">Total pages</Box>
            <Box>{totalPages}</Box>
          </Box>
        )}

        {status === 'processing' && (
          <ProgressBar
            value={progress}
            label="Processing progress"
            description={statusMessage}
            status="in-progress"
          />
        )}

        {status === 'completed' && (
          <Box color="text-status-success" fontSize="body-m">
            {statusMessage}
          </Box>
        )}

        {status === 'error' && errorMessage && (
          <Alert type="error" header="Processing failed">
            {errorMessage}
          </Alert>
        )}

        {processingErrors.length > 0 && (
          <ExpandableSection
            headerText={`Processing errors (${processingErrors.length})`}
            variant="footer"
          >
            <SpaceBetween size="xs">
              {processingErrors.map((error, index) => (
                <Box key={index} variant="small">
                  <Box variant="strong">Page {error.page}:</Box> {error.message}
                </Box>
              ))}
            </SpaceBetween>
          </ExpandableSection>
        )}

        {status === 'completed' && processingErrors.length > 0 && (
          <Alert type="warning" header="Completed with warnings">
            Processing completed but {processingErrors.length} page(s) had errors. 
            The document may be incomplete.
          </Alert>
        )}

        {pagesProcessed > 0 && totalPages && status === 'processing' && (
          <Box variant="small" color="text-body-secondary">
            {pagesProcessed} of {totalPages} pages processed
          </Box>
        )}
      </SpaceBetween>
    </Container>
  );
};
