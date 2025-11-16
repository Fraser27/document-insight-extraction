export interface Document {
  docId: string;
  fileName: string;
  uploadDate: string;
  pageCount?: number;
  status: 'processing' | 'completed' | 'failed' | 'in-progress';
  fileSize: number;
}

export interface UploadProgress {
  docId: string;
  fileName: string;
  totalPages?: number;
  pagesProcessed?: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  errorMessage?: string;
}
