import { useEffect, useState } from 'react';
import {
  Table,
  Box,
  SpaceBetween,
  Button,
  StatusIndicator,
  Header,
} from '@cloudscape-design/components';
import { listDocuments } from '../../services/api';
import type { Document } from '../../types/document';

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

  const fetchDocuments = async () => {
    setLoading(true);

    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [refreshTrigger]);

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

  const getStatusIndicator = (status: Document['status']) => {
    switch (status) {
      case 'processing':
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
          cell: (item) => getStatusIndicator(item.status),
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
