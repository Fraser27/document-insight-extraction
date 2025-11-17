"""
Image Insights Lambda Handler

Handles HTTP API requests for image analysis:
- POST /image-insights/analyze - Analyze image with Claude vision model
"""
import os
import logging
import json
import base64
import boto3
from typing import Dict, Any, List, Optional, Tuple
from botocore.exceptions import ClientError
from decimal import Decimal
from io import BytesIO
import pyzbar

print(f"pyzbar.__version__ {pyzbar.__version__}")

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
REGION = os.environ.get('REGION', 'us-east-1')
VISION_MODEL_ID = os.environ.get('VISION_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

# Import Pillow for QR code processing
try:
    from PIL import Image
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        PYZBAR_AVAILABLE = True
    except ImportError:
        logger.warning("pyzbar not available - QR code decoding will be limited")
        PYZBAR_AVAILABLE = False
    PILLOW_AVAILABLE = True
except ImportError:
    logger.warning("Pillow not available - QR code decoding will be disabled")
    PILLOW_AVAILABLE = False
    PYZBAR_AVAILABLE = False


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if float(obj).is_integer():
                return int(float(obj))
            else:
                return float(obj)
        return super(CustomJsonEncoder, self).default(obj)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for image insights API requests.
    
    Handles:
    - POST /image-insights/analyze - Analyze image with Claude
    
    Args:
        event: API Gateway proxy event
        context: Lambda context
        
    Returns:
        API Gateway response dictionary
    """
    logger.info(f"Received event: {json.dumps(event, default=str)}")

    try:
        # Extract HTTP method and path
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'POST'))
        path = event.get('path', event.get('rawPath', ''))
        
        logger.info(f"Processing {http_method} {path}")
        
        # Route to appropriate handler
        if http_method == 'POST' and path == '/image-insights/analyze':
            return handle_analyze_image(event)
        else:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        logger.error(f"Error in handler: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }


def handle_analyze_image(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle POST /image-insights/analyze request.
    
    Analyzes an image using Claude vision model to:
    1. Validate the image
    2. Extract key insights (Name, Age, etc.)
    3. Detect potential forgery or deepfakes
    4. Detect QR codes with bounding boxes
    
    Args:
        event: API Gateway event
        
    Returns:
        API Gateway response
    """
    try:
        # Get user ID from Cognito claims
        user_id = get_user_id_from_event(event)
        if not user_id:
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        image_base64 = body.get('image')
        prompt = body.get('prompt', '')
        
        # Validate input
        if not image_base64:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'image (base64) is required'})
            }
        
        logger.info(f"Analyzing image for user: {user_id}")
        
        # Analyze image with Claude
        analysis_result = analyze_image_with_claude(image_base64, prompt)
        
        # If QR code detected, decode it
        if analysis_result.get('qr_code_detected') and analysis_result.get('qr_bounding_box'):
            qr_data = decode_qr_code(image_base64, analysis_result['qr_bounding_box'])
            if qr_data:
                analysis_result['qr_code_data'] = qr_data
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(analysis_result, cls=CustomJsonEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': 'Failed to analyze image'})
        }


def analyze_image_with_claude(image_base64: str, user_prompt: str = '') -> Dict[str, Any]:
    """
    Analyze image using Claude vision model.
    
    Args:
        image_base64: Base64 encoded image
        user_prompt: Optional user-provided prompt for additional analysis
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Remove data URL prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Build the prompt
        system_prompt = """You are an expert image analyst. Analyze the provided image and return a JSON response with the following structure:

{
  "is_valid_image": true/false,
  "validation_message": "Brief explanation of validity",
  "key_insights": {
    "name": "Extracted name if visible, otherwise null",
    "age": "Estimated age or age range if person visible, otherwise null",
    "document_type": "Type of document if applicable (ID, passport, etc.)",
    "other_details": ["List of other notable details"]
  },
  "forgery_detection": {
    "suspicious": true/false,
    "confidence": 0.0-1.0,
    "indicators": ["List of forgery indicators if any"]
  },
  "qr_code_detected": true/false,
  "qr_bounding_box": {
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0
  }
}

IMPORTANT INSTRUCTIONS:
- Be thorough but concise in your analysis
- For QR codes: Provide pixel coordinates relative to the image dimensions. The bounding box should tightly fit the QR code.
- If no QR code is detected, set qr_code_detected to false and qr_bounding_box to null
- For forgery detection: Look for inconsistencies in lighting, shadows, edges, text alignment, or digital artifacts
- Confidence should be between 0.0 (no confidence) and 1.0 (very confident)

CRITICAL: Return ONLY valid JSON in the exact structure shown above, with no additional text before or after the JSON.

JSON Response:"""

        if user_prompt:
            system_prompt += f"\n\nAdditional user request: {user_prompt}"
        
        # Prepare the request
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": system_prompt
                        }
                    ]
                }
            ]
        }
        
        # Invoke Bedrock
        logger.info(f"Invoking Claude vision model: {VISION_MODEL_ID}")
        response = bedrock_runtime.invoke_model(
            modelId=VISION_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        logger.info(f"Claude response: {json.dumps(response_body, default=str)}")
        
        # Extract the text content
        content = response_body.get('content', [])
        if not content:
            raise ValueError("No content in Claude response")
        
        # Get the text from the first content block
        text_content = content[0].get('text', '')
        
        # Try to parse as JSON (following insight_generator.py pattern)
        try:
            # Try to extract JSON from response
            # Sometimes models include extra text before/after JSON
            json_start = text_content.find('{')
            json_end = text_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                # No JSON found - return raw response wrapped
                logger.warning("No JSON found in Claude response, wrapping in structure")
                analysis_result = _wrap_raw_response(text_content)
            else:
                json_text = text_content[json_start:json_end]
                
                # Parse JSON
                analysis_result = json.loads(json_text)
                
                # Validate and add defaults for missing fields
                if 'is_valid_image' not in analysis_result:
                    analysis_result['is_valid_image'] = True
                if 'validation_message' not in analysis_result:
                    analysis_result['validation_message'] = "Analysis completed"
                if 'key_insights' not in analysis_result:
                    analysis_result['key_insights'] = {}
                if 'forgery_detection' not in analysis_result:
                    analysis_result['forgery_detection'] = {
                        "suspicious": False,
                        "confidence": 0.0,
                        "indicators": []
                    }
                if 'qr_code_detected' not in analysis_result:
                    analysis_result['qr_code_detected'] = False
                if 'qr_bounding_box' not in analysis_result:
                    analysis_result['qr_bounding_box'] = None
                    
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed, wrapping raw response: {str(e)}")
            logger.debug(f"Response text: {text_content[:500]}")
            analysis_result = _wrap_raw_response(text_content)
        
        return analysis_result
        
    except ClientError as e:
        logger.error(f"Bedrock API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error analyzing image with Claude: {str(e)}", exc_info=True)
        raise


def decode_qr_code(image_base64: str, bounding_box: Optional[Dict[str, int]]) -> Optional[str]:
    """
    Decode QR code from image using Pillow and pyzbar.
    
    Based on AWS sample: https://github.com/aws-samples/barcode-qr-decoder-lambda
    
    Args:
        image_base64: Base64 encoded image
        bounding_box: Optional dictionary with x, y, width, height for cropping
        
    Returns:
        Decoded QR code data or None
    """
    if not PILLOW_AVAILABLE:
        logger.warning("Pillow not available, cannot decode QR code")
        return None
    
    if not PYZBAR_AVAILABLE:
        logger.warning("pyzbar not available, cannot decode QR code")
        return None
    
    try:
        # Remove data URL prefix if present
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Decode base64 to image
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Crop to bounding box if provided and valid
        if bounding_box and all(k in bounding_box for k in ['x', 'y', 'width', 'height']):
            x = int(bounding_box['x'])
            y = int(bounding_box['y'])
            width = int(bounding_box['width'])
            height = int(bounding_box['height'])
            
            # Validate bounding box is within image dimensions
            img_width, img_height = image.size
            if x >= 0 and y >= 0 and (x + width) <= img_width and (y + height) <= img_height:
                # Crop the image to the bounding box
                image = image.crop((x, y, x + width, y + height))
                logger.info(f"Cropped image to bounding box: ({x}, {y}, {width}, {height})")
            else:
                logger.warning(f"Invalid bounding box coordinates, using full image")
        
        # Decode QR codes using pyzbar (following AWS sample pattern)
        decoded_objects = pyzbar_decode(image)
        
        if decoded_objects:
            # Return all decoded QR codes (could be multiple)
            qr_codes = []
            for code in decoded_objects:
                try:
                    qr_data = code.data.decode('utf-8')
                    qr_codes.append(qr_data)
                    logger.info(f"Successfully decoded QR/barcode: {qr_data}")
                except Exception as e:
                    logger.warning(f"Could not decode QR code data: {str(e)}")
            
            # Return the first QR code found, or join multiple if found
            if qr_codes:
                return qr_codes[0] if len(qr_codes) == 1 else ', '.join(qr_codes)
        
        logger.info("No QR code or barcode detected in image")
        return None
        
    except Exception as e:
        logger.error(f"Error processing QR code: {str(e)}", exc_info=True)
        return None


def _wrap_raw_response(response_text: str) -> Dict[str, Any]:
    """
    Wrap raw (non-JSON) response in a structured format.
    This handles cases where Claude doesn't return valid JSON.
    
    Args:
        response_text: Raw response text from Claude
        
    Returns:
        Structured dictionary with raw response
    """
    return {
        "is_valid_image": True,
        "validation_message": "Analysis completed (raw response)",
        "key_insights": {
            "raw_analysis": response_text
        },
        "forgery_detection": {
            "suspicious": False,
            "confidence": 0.0,
            "indicators": []
        },
        "qr_code_detected": False,
        "qr_bounding_box": None,
        "raw_response": response_text
    }


def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user ID from Cognito JWT claims in API Gateway event.
    
    Args:
        event: API Gateway event
        
    Returns:
        User ID string or None if not found
    """
    try:
        # Try to get from authorizer context (API Gateway v1)
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # Check for Cognito claims
        claims = authorizer.get('claims', {})
        if claims:
            # Try different claim fields
            user_id = claims.get('sub') or claims.get('cognito:username') or claims.get('username')
            if user_id:
                return user_id
        
        # Try to get from JWT token directly (API Gateway v2)
        jwt = authorizer.get('jwt', {})
        if jwt:
            jwt_claims = jwt.get('claims', {})
            user_id = jwt_claims.get('sub') or jwt_claims.get('cognito:username') or jwt_claims.get('username')
            if user_id:
                return user_id
        
        logger.warning("Could not extract user ID from event")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting user ID: {str(e)}")
        return None


def get_cors_headers() -> Dict[str, str]:
    """
    Get CORS headers for API Gateway response.
    
    Returns:
        Dictionary of CORS headers
    """
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
