# S3 Vectors API Usage

This document describes how the project uses the AWS S3 Vectors API via boto3.

## Overview

Amazon S3 Vectors is a preview feature that provides native vector storage and similarity search capabilities in S3. The project uses the `s3vectors` boto3 client to interact with vector buckets and indexes.

## Client Initialization

```python
import boto3

# Create S3 Vectors client
s3vectors_client = boto3.client('s3vectors', region_name='us-east-1')
```

## Key Operations

### 1. PutVectors - Store Vectors

Store vectors with metadata in a vector index:

```python
s3vectors_client.put_vectors(
    indexArn='arn:aws:s3:region:account:vector-index/bucket/index',
    vectors=[
        {
            'key': 'doc-id#chunk-0',
            'data': {'float32': embedding_vector},  # List[float]
            'metadata': {
                'docId': 'doc-id',
                'pageRange': '1-10',
                'uploadTimestamp': 1234567890,
                'textChunk': 'Original text content...'
            }
        }
    ]
)
```

**Limits:**
- Max 500 vectors per request
- Vectors must be float32 format
- Max 40 KB metadata per vector

### 2. QueryVectors - Semantic Search

Query vectors with similarity search and metadata filtering:

```python
response = s3vectors_client.query_vectors(
    indexArn='arn:aws:s3:region:account:vector-index/bucket/index',
    queryVector={'float32': query_embedding},
    topK=5,  # Max 30
    filter={'docId': 'doc-id'},  # Metadata filter
    returnDistance=True,
    returnMetadata=True
)

# Response structure
{
    'distanceMetric': 'cosine',  # or 'euclidean'
    'vectors': [
        {
            'key': 'doc-id#chunk-0',
            'distance': 0.123,
            'metadata': {...}
        }
    ]
}
```

**Distance Metrics:**
- **Cosine**: 0 = identical, 2 = opposite
- **Euclidean**: Smaller = more similar

### 3. DeleteVectors - Remove Vectors

Delete vectors by key:

```python
s3vectors_client.delete_vectors(
    indexArn='arn:aws:s3:region:account:vector-index/bucket/index',
    keys=['doc-id#chunk-0', 'doc-id#chunk-1']
)
```

**Limits:**
- Max 500 keys per request

### 4. ListVectors - List All Vectors

List vectors in an index:

```python
response = s3vectors_client.list_vectors(
    indexArn='arn:aws:s3:region:account:vector-index/bucket/index',
    maxResults=1000,
    returnData=False,
    returnMetadata=False,
    nextToken='...'  # For pagination
)

# Response structure
{
    'vectors': [
        {'key': 'doc-id#chunk-0'},
        {'key': 'doc-id#chunk-1'}
    ],
    'nextToken': '...'  # If more results
}
```

## Implementation Details

### Document Processor (vector_store.py)

The `VectorStore` class wraps S3 Vectors operations for storing document embeddings:

- **put_vector()**: Store single vector
- **put_vectors_batch()**: Store multiple vectors (batches of 500)
- **delete_vector()**: Delete single vector
- **delete_vectors_by_doc_id()**: Delete all vectors for a document

### Insight Extractor (vector_query.py)

The `VectorQuery` class handles semantic search for insight extraction:

- **generate_query_embedding()**: Create query embedding with Titan V2
- **query_vectors()**: Search vectors with metadata filtering
- **get_text_chunks()**: Convenience method to get text content only

## Metadata Strategy

### Filterable Metadata
Used for query filtering (stored in index):
- `docId`: Document identifier
- `pageRange`: Page range (e.g., "1-10")
- `uploadTimestamp`: Unix timestamp

### Non-Filterable Metadata
Used for context retrieval (stored with vector):
- `textChunk`: Original text content

**Note:** All metadata is stored together in S3 Vectors. The distinction is conceptual for our application logic.

## Performance Characteristics

- **Query Latency**: Sub-second (typically < 1s)
- **Average Recall**: 90%+ for most datasets
- **Throughput**: 5 write requests/second per index
- **Scalability**: Up to 50 million vectors per index

## Cost Optimization

1. **Batch Operations**: Always use batch APIs (500 vectors/request)
2. **Metadata Size**: Keep metadata under 40 KB per vector
3. **Query Frequency**: Ideal for infrequent queries (use cache)
4. **ARM64 Lambda**: 10% cost reduction vs x86_64

## IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3vectors:PutVectors",
        "s3vectors:QueryVectors",
        "s3vectors:DeleteVectors",
        "s3vectors:ListVectors",
        "s3vectors:GetVectors"
      ],
      "Resource": "arn:aws:s3:region:account:vector-index/bucket/index"
    }
  ]
}
```

## References

- [S3 Vectors Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html)
- [QueryVectors API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_QueryVectors.html)
- [PutVectors API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_PutVectors.html)
- [DeleteVectors API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_DeleteVectors.html)
