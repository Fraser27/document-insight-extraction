"""
Insight Generation Module

This module provides functionality to generate structured insights from
document chunks using Amazon Bedrock (Claude 3 Sonnet).
"""
import logging
import json
import boto3
from typing import List, Dict, Any
from decimal import Decimal
logger = logging.getLogger(__name__)


class InsightGenerator:
    """Generate structured insights using Amazon Bedrock."""
    
    def __init__(self, region: str, model_id: str):
        """
        Initialize insight generator.
        
        Args:
            region: AWS region for Bedrock service
            model_id: Bedrock model ID (e.g., Claude 3 Sonnet)
        """
        self.logger = logging.getLogger(__name__)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = model_id
        
        # Model configuration
        self.max_tokens = 4096
        self.temperature = 0.0  # Deterministic for consistent results
    
    def generate_insights(
        self,
        user_query: str,
        context_chunks: List[str]
    ) -> Dict[str, Any]:
        """
        Generate structured insights from context chunks.
        
        Args:
            user_query: User's query/prompt
            context_chunks: Retrieved text chunks from vector search
            
        Returns:
            Structured insights as JSON dictionary
        """
        try:
            # Format prompt with context
            prompt = self._format_prompt(user_query, context_chunks)
            
            print(
                f"Generating insights with {len(context_chunks)} chunks, "
                f"prompt length: {len(prompt)} chars"
            )
            
            # Call Bedrock model
            response = self._invoke_bedrock(prompt)
            
            # Parse and validate JSON response
            insights = self._parse_response(response)
            
            print("Successfully generated insights")
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")
            raise
    
    def _format_prompt(
        self,
        user_query: str,
        context_chunks: List[str]
    ) -> str:
        """
        Format prompt with user query and retrieved context.
        
        Args:
            user_query: User's query
            context_chunks: Retrieved text chunks
            
        Returns:
            Formatted prompt string
        """
        # Combine context chunks
        context = "\n\n---\n\n".join([
            f"Context Chunk {i+1}:\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Create structured prompt
        prompt = f"""You are an AI assistant that extracts structured insights from documents.

Given the following context from a document and a user query, extract relevant information and provide a structured JSON response.

USER QUERY:
{user_query}

DOCUMENT CONTEXT:
{context}

INSTRUCTIONS:
1. Analyze the context carefully to answer the user's query
2. Extract key information, entities, and insights
3. Provide a clear summary
4. Return your response as valid JSON with the following structure:
{{
    "summary": "A concise summary of the findings",
    "keyPoints": ["List", "of", "key", "points"],
    "entities": [
        {{
            "name": "Entity name",
            "type": "Entity type (person, organization, location, date, etc.)",
            "context": "Brief context about this entity"
        }}
    ],
    "answer": "Direct answer to the user's query",
    "confidence": 0.95,
    "metadata": {{
        "chunksAnalyzed": {len(context_chunks)},
        "relevance": "high/medium/low"
    }}
}}

IMPORTANT:
- Return ONLY valid JSON, no additional text
- If information is not found in the context, indicate this in the answer
- Be precise and factual, do not make up information
- Extract entities only if they are clearly mentioned in the context

JSON Response:"""
        
        return prompt
    
    def _invoke_bedrock(self, prompt: str) -> str:
        """
        Invoke Bedrock model with prompt.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Model response text
        """
        try:
            # Prepare request based on model type
            if "claude" in self.model_id.lower():
                # Claude 3 format
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            else:
                # Generic format
                request_body = {
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature
                }
            
            # Invoke model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text based on model type
            if "claude" in self.model_id.lower():
                # Claude 3 response format
                if 'content' in response_body and len(response_body['content']) > 0:
                    response_text = response_body['content'][0]['text']
                else:
                    raise ValueError("No content in Claude response")
            else:
                # Generic response format
                response_text = response_body.get('completion', '')
            
            self.logger.debug(
                f"Received response: {len(response_text)} chars"
            )
            
            return response_text
            
        except Exception as e:
            self.logger.error(f"Error invoking Bedrock: {str(e)}")
            raise
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate JSON response from model.
        
        Args:
            response_text: Model response text
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try to extract JSON from response
            # Sometimes models include extra text before/after JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_text = response_text[json_start:json_end]
            
            # Parse JSON
            insights = json.loads(json_text)
            
            # Validate schema
            self._validate_insights_schema(insights)
            
            return insights
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in response: {str(e)}")
            self.logger.debug(f"Response text: {response_text[:500]}")
            
            # Return error structure
            return {
                "summary": "Error parsing model response",
                "keyPoints": [],
                "entities": [],
                "answer": "Unable to parse insights from model response",
                "confidence": 0.0,
                "metadata": {
                    "error": str(e),
                    "relevance": "unknown"
                }
            }
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            raise
    
    def _validate_insights_schema(self, insights: Dict[str, Any]) -> None:
        """
        Validate insights JSON schema.
        
        Args:
            insights: Parsed insights dictionary
            
        Raises:
            ValueError: If schema is invalid
        """
        required_fields = ['summary', 'keyPoints', 'entities', 'answer']
        
        for field in required_fields:
            if field not in insights:
                self.logger.warning(f"Missing required field: {field}")
                # Add default value
                if field == 'keyPoints':
                    insights[field] = []
                elif field == 'entities':
                    insights[field] = []
                else:
                    insights[field] = ""
        
        # Validate types
        if not isinstance(insights.get('keyPoints', []), list):
            insights['keyPoints'] = []
        
        if not isinstance(insights.get('entities', []), list):
            insights['entities'] = []
        
        # Ensure metadata exists
        if 'metadata' not in insights:
            insights['metadata'] = {}
        
        # Ensure confidence exists
        if 'confidence' not in insights:
            insights['confidence'] = 0.5
        
        self.logger.debug("Insights schema validated")
