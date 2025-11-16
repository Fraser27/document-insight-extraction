import { useEffect, useState } from 'react';
import {
  Table,
  Box,
  SpaceBetween,
  Button,
  StatusIndicator,
  Header,
  ProgressBar,
} from '@cloudscape-design/components';
import { listDocuments, getProcessingStatus } from '../../services/api';
import type { Document, ProcessingStatus } from '../../services/api';

interface DocumentListProps {
  refreshTrigger?: number;
  onDocumentSelect?: (document: Document) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  refreshTrigger,
  onDocumentSelect,
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItems, setSelectedItems] = useState<Document[]>([]);
  const [processingStatuses, setProcessingStatuses] = useState<Map<string, ProcessingStatus>>(new Map());

  const fetchDocuments = async () => {
    setLoading(true);

    try {
      const docs = await listDocuments();
      setDocuments(docs);
      
      // Fetch detailed processing status for documents that are processing
      const statusMap = new Map<string, ProcessingStatus>();
      
      for (const doc of docs) {
        if (doc.status === 'processing' || doc.status === 'in-progress') {
          try {
            const status = await getProcessingStatus(doc.docId);
            statusMap.set(doc.docId, status);
          } catch (err) {
            console.warn(`Failed to get status for ${doc.docId}:`, err);
          }
        }
      }
      
      setProcessingStatuses(statusMap);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [refreshTrigger]);

  // Auto-refresh processing documents every 5 seconds
  useEffect(() => {
    const hasProcessingDocs = documents.some(doc => 
      doc.status === 'processing' || doc.status === 'in-progress' ||
      processingStatuses.get(doc.docId)?.status === 'in-progress'
    );

    if (hasProcessingDocs) {
      const interval = setInterval(() => {
        fetchDocuments();
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [documents, processingStatuses]);

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getStatusIndicator = (document: Document) => {
    const processingStatus = processingStatuses.get(document.docId);
    
    if (processingStatus) {
      switch (processingStatus.status) {
        case 'in-progress':
          const progress = processingStatus.totalPages && processingStatus.currentPage 
            ? (processingStatus.currentPage / processingStatus.totalPages) * 100 
            : 0;
          
          const inProgressErrorCount = processingStatus.errorCount || 0;
          const pagesText = `${processingStatus.currentPage || 0}/${processingStatus.totalPages || 0} pages`;
          const inProgressStatusText = inProgressErrorCount > 0
            ? `${pagesText}, ${inProgressErrorCount} error${inProgressErrorCount > 1 ? 's' : ''}`
            : pagesText;
          
          return (
            <SpaceBetween size="xs">
              <StatusIndicator type={inProgressErrorCount > 0 ? "warning" : "in-progress"}>
                Processing ({inProgressStatusText})
              </StatusIndicator>
              {processingStatus.totalPages && (
                <ProgressBar
                  value={progress}
                  additionalInfo={processingStatus.progressMessage || ''}
                  description="Processing progress"
                  status={inProgressErrorCount > 0 ? "error" : "in-progress"}
                />
              )}
            </SpaceBetween>
          );
        case 'completed':
          const errorCount = processingStatus.errorCount || 0;
          const chunksText = `${processingStatus.totalChunks || 0} chunks`;
          const statusText = errorCount > 0 
            ? `${chunksText}, ${errorCount} error${errorCount > 1 ? 's' : ''}`
            : chunksText;
          
          return (
            <StatusIndicator type={errorCount > 0 ? "warning" : "success"}>
              Completed ({statusText})
            </StatusIndicator>
          );
        case 'failed':
          return (
            <StatusIndicator type="error">
              Failed: {processingStatus.errorMessage || 'Unknown error'}
            </StatusIndicator>
          );
      }
    }
    
    // Fallback to document status
    switch (document.status) {
      case 'processing':
      case 'in-progress':
        return <StatusIndicator type="in-progress">Processing</StatusIndicator>;
      case 'completed':
        return <StatusIndicator type="success">Completed</StatusIndicator>;
      case 'failed':
        return <StatusIndicator type="error">Failed</StatusIndicator>;
      default:
        return <StatusIndicator type="pending">Unknown</StatusIndicator>;
    }
  };

  return (
    <Table
      columnDefinitions={[
        {
          id: 'fileName',
          header: 'File Name',
          cell: (item) => item.fileName,
          sortingField: 'fileName',
        },
        {
          id: 'uploadDate',
          header: 'Upload Date',
          cell: (item) => formatDate(item.uploadDate),
          sortingField: 'uploadDate',
        },
        {
          id: 'pageCount',
          header: 'Pages',
          cell: (item) => item.pageCount || '-',
          sortingField: 'pageCount',
        },
        {
          id: 'fileSize',
          header: 'Size',
          cell: (item) => formatFileSize(item.fileSize),
          sortingField: 'fileSize',
        },
        {
          id: 'status',
          header: 'Status',
          cell: (item) => getStatusIndicator(item),
          sortingField: 'status',
        },
      ]}
      items={documents}
      loading={loading}
      loadingText="Loading documents..."
      selectionType="single"
      selectedItems={selectedItems}
      onSelectionChange={({ detail }) => {
        setSelectedItems(detail.selectedItems);
        if (detail.selectedItems.length > 0) {
          onDocumentSelect?.(detail.selectedItems[0]);
        }
      }}
      empty={
        <Box textAlign="center" color="inherit">
          <SpaceBetween size="m">
            <b>No documents</b>
            <Box variant="p" color="inherit">
              Upload a document to get started
            </Box>
          </SpaceBetween>
        </Box>
      }
      header={
        <Header
          actions={
            <Button
              iconName="refresh"
              onClick={fetchDocuments}
              loading={loading}
            >
              Refresh
            </Button>
          }
        >
          Documents
        </Header>
      }
    />
  );
};
