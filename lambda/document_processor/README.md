# Document Processing Lambda Function

This Lambda function processes PDF documents by extracting text, performing OCR on images, generating vector embeddings, and storing them in S3 Vectors for semantic search.

## Features

- **PDF Text Extraction**: Extracts text from each page using PyPDF2
- **Image Detection & OCR**: Detects images in PDF pages and performs OCR using Amazon Bedrock
- **Text Chunking**: Splits text into optimal chunks (8192 tokens with 10% overlap)
- **Embedding Generation**: Generates 1024-dimensional embeddings using Amazon Titan V2
- **Vector Storage**: Stores embeddings in S3 Vectors with metadata filtering
- **Real-time Progress**: Sends WebSocket notifications during processing
- **Automatic Cleanup**: Removes vectors when documents are deleted

## Architecture

```
S3 Event (ObjectCreated) → Lambda → Process Document
                                   ↓
                            Extract Text (PyPDF2)
                                   ↓
                            Detect Images → OCR (Bedrock)
                                   ↓
                            Chunk Text (8192 tokens)
                                   ↓
                            Generate Embeddings (Titan V2)
                                   ↓
                            Store Vectors (S3 Vectors)
                                   ↓
                            Send Progress (WebSocket)
```

## Modules

### pdf_extractor.py
Extracts text from PDF pages using PyPDF2.

**Key Functions:**
- `extract_text_from_pdf(pdf_bytes)`: Extract text from all pages
- `get_page_count(pdf_bytes)`: Get total page count
- `has_text_content(page_text)`: Check if page has text

### image_detector.py
Detects and extracts images from PDF pages.

**Key Functions:**
- `has_images(pdf_bytes, page_num)`: Check if page has images
- `extract_images(pdf_bytes, page_num)`: Extract image data

### ocr_processor.py
Performs OCR on images using Amazon Bedrock (Claude 3).

**Key Functions:**
- `perform_ocr(image_data, image_format)`: OCR single image
- `process_images(images)`: Process multiple images

### text_chunker.py
Splits text into chunks with overlap using recursive character splitting.

**Key Functions:**
- `chunk_text(text, page_range, doc_id)`: Create chunks with metadata
- `estimate_token_count(text)`: Estimate token count

**Configuration:**
- Chunk size: 8192 tokens (~32,768 characters)
- Overlap: 819 tokens (~3,276 characters, 10%)

### embedding_generator.py
Generates vector embeddings using Amazon Titan V2.

**Key Functions:**
- `generate_embedding(text)`: Generate single embedding
- `generate_embeddings_batch(texts)`: Generate multiple embeddings

**Specifications:**
- Model: amazon.titan-embed-text-v2:0
- Input: Max 8192 tokens
- Output: 1024 dimensions
- Normalization: Enabled (for cosine similarity)

### vector_store.py
Wrapper for S3 Vectors API operations.

**Key Functions:**
- `put_vector(key, vector, filterable_metadata, non_filterable_metadata)`: Store vector
- `put_vectors_batch(vectors)`: Store multiple vectors
- `delete_vectors_by_doc_id(doc_id)`: Delete all vectors for document
- `query_vectors(query_vector, top_k, metadata_filter)`: Query vectors

**Metadata Schema:**
- Filterable: docId, pageRange, uploadTimestamp
- Non-filterable: textChunk

### websocket_notifier.py
Sends real-time progress updates via WebSocket API Gateway.

**Key Functions:**
- `send_processing_started(connection_id, doc_id, total_pages)`
- `send_progress(connection_id, doc_id, pages_processed, total_pages)`
- `send_processing_complete(connection_id, doc_id, total_chunks)`
- `send_error(connection_id, doc_id, error_code, error_message)`

### document_processor.py
Main Lambda handler that orchestrates the document processing pipeline.

**Event Types:**
- `ObjectCreated:*`: Process new document
- `ObjectRemoved:Delete`: Clean up vectors

**Processing Flow:**
1. Download PDF from S3
2. Extract text from each page
3. Detect images and perform OCR
4. Process pages in batches of 10
5. Chunk text and generate embeddings
6. Store vectors in S3 Vectors
7. Send progress updates via WebSocket

## Environment Variables

Required environment variables:

- `VECTOR_BUCKET_NAME`: S3 Vector bucket name
- `VECTOR_INDEX_ARN`: S3 Vector index ARN
- `EMBED_MODEL_ID`: Bedrock embedding model ID (default: amazon.titan-embed-text-v2:0)
- `WSS_URL`: WebSocket API URL
- `REGION`: AWS region
- `LOG_LEVEL`: Logging level (default: INFO)

## IAM Permissions

The Lambda function requires the following permissions:

- **S3**: GetObject, DeleteObject on documents bucket
- **S3 Vectors**: PutVectors, DeleteVectors, QueryVectors on vector index
- **Bedrock**: InvokeModel for Titan V2 and Claude 3
- **API Gateway**: ManageConnections for WebSocket
- **CloudWatch Logs**: CreateLogGroup, CreateLogStream, PutLogEvents

## Configuration

### Lambda Settings
- Runtime: Python 3.12
- Architecture: x86_64 (for PyPDF2 compatibility)
- Memory: 3008 MB
- Timeout: 600 seconds (10 minutes)
- Layers: pypdf-layer, boto3-layer

### Processing Settings
- Batch size: 10 pages
- Chunk size: 8192 tokens
- Chunk overlap: 819 tokens (10%)
- Progress updates: Every 10 pages

## Error Handling

The function implements robust error handling:

1. **Page-level errors**: Continue processing remaining pages
2. **Batch-level errors**: Log and skip failed batches
3. **WebSocket errors**: Continue processing even if notifications fail
4. **Recoverable errors**: Send error notification but continue
5. **Fatal errors**: Send error notification and fail

## Monitoring

Key metrics to monitor:

- Lambda invocations and errors
- Processing duration per document
- Memory usage
- Bedrock API calls and throttling
- S3 Vectors storage operations
- WebSocket connection failures

## Testing

To test the function locally:

```python
import json
from document_processor import handler

# Create test event
event = {
    "Records": [{
        "eventName": "ObjectCreated:Put",
        "s3": {
            "bucket": {"name": "test-bucket"},
            "object": {"key": "test-document.pdf"}
        }
    }]
}

# Invoke handler
response = handler(event, None)
print(response)
```

## Deployment

The function is deployed via CDK using the LambdaFunctionStack:

```python
from infrastructure.lambda_function_stack import LambdaFunctionStack

lambda_stack = LambdaFunctionStack(
    app, "LambdaStack",
    env_name="dev",
    config=config
)

lambda_stack.create_document_processor_lambda(
    documents_bucket=s3_stack.documents_bucket,
    vector_bucket_name=s3_stack.vector_bucket_name,
    vector_index_arn=s3_stack.vector_index_arn,
    websocket_url=websocket_stack.get_websocket_url(),
    pypdf_layer_arn="arn:aws:lambda:...",
    boto3_layer_arn="arn:aws:lambda:..."
)
```

## Troubleshooting

### Common Issues

1. **PyPDF2 import error**: Ensure pypdf layer is attached
2. **Bedrock throttling**: Implement exponential backoff
3. **Memory errors**: Increase Lambda memory allocation
4. **Timeout errors**: Process documents in smaller batches
5. **WebSocket connection gone**: Handle GoneException gracefully

### Logs

Check CloudWatch Logs for detailed processing information:

```bash
aws logs tail /aws/lambda/document-insight-document-processor-dev --follow
```

## Future Enhancements

- [ ] Parallel page processing
- [ ] Batch embedding generation
- [ ] Checkpointing for long documents
- [ ] Support for other document formats (DOCX, PPTX)
- [ ] Advanced OCR with Amazon Textract
- [ ] Custom embedding models
