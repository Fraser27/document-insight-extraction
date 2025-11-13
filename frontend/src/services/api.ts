import axios from 'axios';
import type { AxiosInstance, AxiosError } from 'axios';
import { getIdToken } from './auth';

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || '';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_ENDPOINT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authentication token
apiClient.interceptors.request.use(
  async (config) => {
    try {
      const token = await getIdToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Failed to get auth token:', error);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Unauthorized - redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Types
export interface PresignedUrlRequest {
  fileName: string;
  fileSize: number;
  contentType: string;
}

export interface PresignedUrlResponse {
  url: string;
  fields: {
    key: string;
    [key: string]: string;
  };
  docId: string;
  expiresIn: number;
}

export interface Document {
  docId: string;
  fileName: string;
  uploadDate: string;
  pageCount?: number;
  status: 'processing' | 'completed' | 'failed';
  fileSize: number;
}

export interface InsightRequest {
  docId: string;
  prompt: string;
}

export interface InsightResponse {
  insights: {
    summary?: string;
    keyPoints?: string[];
    entities?: Array<{
      name: string;
      type: string;
      context: string;
    }>;
    metadata?: {
      confidence?: number;
      processingTime?: number;
    };
    [key: string]: any;
  };
  source: 'cache' | 'generated';
  chunkCount?: number;
  timestamp: number;
}

export interface CachedInsight {
  docId: string;
  extractionTimestamp: number;
  prompt: string;
  insights: any;
  modelId: string;
  expiresAt: number;
}

// API Functions

/**
 * Get a presigned POST URL for uploading a document to S3
 */
export const getPresignedUrl = async (
  request: PresignedUrlRequest
): Promise<PresignedUrlResponse> => {
  const response = await apiClient.post<PresignedUrlResponse>(
    '/documents/presigned-url',
    request
  );
  return response.data;
};

/**
 * Upload a file directly to S3 using presigned POST URL
 */
export const uploadToS3 = async (
  presignedUrl: PresignedUrlResponse,
  file: File
): Promise<void> => {
  const formData = new FormData();
  
  // Add all fields from presigned URL
  Object.entries(presignedUrl.fields).forEach(([key, value]) => {
    formData.append(key, value);
  });
  
  // Add the file last
  formData.append('file', file);

  // Upload to S3 (no auth headers needed for presigned URL)
  await axios.post(presignedUrl.url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

/**
 * List all documents for the current user
 */
export const listDocuments = async (): Promise<Document[]> => {
  const response = await apiClient.get<Document[]>('/documents');
  return response.data;
};

/**
 * Extract insights from a document using a natural language prompt
 */
export const extractInsights = async (
  request: InsightRequest
): Promise<InsightResponse> => {
  const response = await apiClient.post<InsightResponse>(
    '/insights/extract',
    request
  );
  return response.data;
};

/**
 * Get cached insights for a specific document
 */
export const getInsights = async (docId: string): Promise<CachedInsight[]> => {
  const response = await apiClient.get<CachedInsight[]>(`/insights/${docId}`);
  return response.data;
};

/**
 * Delete a document
 */
export const deleteDocument = async (docId: string): Promise<void> => {
  await apiClient.delete(`/documents/${docId}`);
};

export default apiClient;
