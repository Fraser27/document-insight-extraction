"""
DynamoDB Cache Manager Module

This module provides functionality to check and store insights in DynamoDB cache
with 24-hour TTL for cost optimization.
"""
import logging
import time
import boto3
from typing import Dict, Any, Optional
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage DynamoDB cache for document insights."""
    
    def __init__(self, region: str, table_name: str):
        """
        Initialize cache manager.
        
        Args:
            region: AWS region for DynamoDB
            table_name: DynamoDB table name
        """
        self.logger = logging.getLogger(__name__)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self.table_name = table_name
        
        # TTL configuration
        self.ttl_hours = 24
    
    def check_cache(self, doc_id: str, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Check cache for existing insights.
        
        Queries DynamoDB by docId and filters by prompt and TTL.
        Returns the most recent cached result if found.
        
        Args:
            doc_id: Document identifier
            prompt: User's query prompt
            
        Returns:
            Cached insights dictionary or None if not found
        """
        try:
            current_time = int(time.time())
            
            # Query by docId (partition key)
            response = self.table.query(
                KeyConditionExpression=Key('docId').eq(doc_id),
                FilterExpression=(
                    Attr('prompt').eq(prompt) & 
                    Attr('expiresAt').gt(current_time)
                ),
                ScanIndexForward=False,  # Sort by extractionTimestamp descending
                Limit=1  # Get most recent only
            )
            
            if response['Items']:
                cached_item = response['Items'][0]
                self.logger.info(
                    f"Cache hit for docId={doc_id}, prompt='{prompt[:50]}...'"
                )
                return cached_item
            else:
                self.logger.info(
                    f"Cache miss for docId={doc_id}, prompt='{prompt[:50]}...'"
                )
                return None
                
        except Exception as e:
            self.logger.error(f"Error checking cache: {str(e)}")
            # Return None on error to allow fallback to generation
            return None
    
    def store_in_cache(
        self,
        doc_id: str,
        prompt: str,
        insights: Dict[str, Any],
        model_id: str,
        chunk_count: int
    ) -> bool:
        """
        Store insights in cache with 24-hour TTL.
        
        Args:
            doc_id: Document identifier
            prompt: User's query prompt
            insights: Extracted insights dictionary
            model_id: Bedrock model ID used for extraction
            chunk_count: Number of chunks retrieved
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            timestamp = int(time.time())
            expires_at = timestamp + (self.ttl_hours * 3600)
            
            # Prepare item
            item = {
                'docId': doc_id,
                'extractionTimestamp': timestamp,
                'prompt': prompt,
                'insights': insights,
                'modelId': model_id,
                'chunkCount': chunk_count,
                'expiresAt': expires_at
            }
            
            # Store in DynamoDB
            self.table.put_item(Item=item)
            
            self.logger.info(
                f"Stored insights in cache: docId={doc_id}, "
                f"prompt='{prompt[:50]}...', expires in {self.ttl_hours}h"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing in cache: {str(e)}")
            return False
    
    def get_all_insights(self, doc_id: str) -> list:
        """
        Retrieve all non-expired insights for a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            List of insight items sorted by timestamp descending
        """
        try:
            current_time = int(time.time())
            
            # Query by docId
            response = self.table.query(
                KeyConditionExpression=Key('docId').eq(doc_id),
                FilterExpression=Attr('expiresAt').gt(current_time),
                ScanIndexForward=False  # Sort by extractionTimestamp descending
            )
            
            items = response['Items']
            
            self.logger.info(
                f"Retrieved {len(items)} non-expired insights for docId={doc_id}"
            )
            
            return items
            
        except Exception as e:
            self.logger.error(f"Error retrieving insights: {str(e)}")
            return []
    
    def invalidate_cache(self, doc_id: str) -> int:
        """
        Invalidate all cache entries for a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Number of items deleted
        """
        try:
            # Query all items for this document
            response = self.table.query(
                KeyConditionExpression=Key('docId').eq(doc_id)
            )
            
            items = response['Items']
            deleted_count = 0
            
            # Delete each item
            for item in items:
                self.table.delete_item(
                    Key={
                        'docId': item['docId'],
                        'extractionTimestamp': item['extractionTimestamp']
                    }
                )
                deleted_count += 1
            
            self.logger.info(
                f"Invalidated {deleted_count} cache entries for docId={doc_id}"
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {str(e)}")
            return 0
