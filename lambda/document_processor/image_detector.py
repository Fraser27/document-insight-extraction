"""
Image Detection Module

This module provides functionality to detect images in PDF pages.
"""
import logging
from typing import List, Dict
from io import BytesIO
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class ImageDetector:
    """Detect images in PDF pages."""
    
    def __init__(self):
        """Initialize image detector."""
        self.logger = logging.getLogger(__name__)
    
    def has_images(self, pdf_bytes: bytes, page_num: int) -> bool:
        """
        Check if a PDF page contains images.
        
        Args:
            pdf_bytes: PDF file content as bytes
            page_num: Page number (0-indexed)
            
        Returns:
            True if page contains images, False otherwise
        """
        try:
            pdf_file = BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
            
            if page_num >= len(reader.pages):
                self.logger.warning(f"Page {page_num} does not exist")
                return False
            
            page = reader.pages[page_num]
            
            # Check if page has XObject resources (images)
            if '/Resources' in page:
                resources = page['/Resources']
                if '/XObject' in resources:
                    xobjects = resources['/XObject']
                    if xobjects:
                        # Check if any XObject is an image
                        for obj_name in xobjects:
                            obj = xobjects[obj_name]
                            if obj.get('/Subtype') == '/Image':
                                self.logger.debug(f"Page {page_num} contains images")
                                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error detecting images on page {page_num}: {str(e)}")
            return False
    
    def extract_images(self, pdf_bytes: bytes, page_num: int) -> List[Dict[str, any]]:
        """
        Extract images from a PDF page.
        
        Args:
            pdf_bytes: PDF file content as bytes
            page_num: Page number (0-indexed)
            
        Returns:
            List of dictionaries containing image data:
            [
                {
                    "name": "image_name",
                    "data": b"image_bytes",
                    "format": "JPEG" or "PNG" or other
                },
                ...
            ]
        """
        images = []
        
        try:
            pdf_file = BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
            
            if page_num >= len(reader.pages):
                self.logger.warning(f"Page {page_num} does not exist")
                return images
            
            page = reader.pages[page_num]
            
            # Extract images from XObject resources
            if '/Resources' in page:
                resources = page['/Resources']
                if '/XObject' in resources:
                    xobjects = resources['/XObject']
                    
                    for obj_name in xobjects:
                        obj = xobjects[obj_name]
                        
                        # Check if XObject is an image
                        if obj.get('/Subtype') == '/Image':
                            try:
                                # Get image data
                                image_data = obj.get_data()
                                
                                # Determine image format
                                image_format = "UNKNOWN"
                                if '/Filter' in obj:
                                    filter_type = obj['/Filter']
                                    if filter_type == '/DCTDecode':
                                        image_format = "JPEG"
                                    elif filter_type == '/FlateDecode':
                                        image_format = "PNG"
                                    elif filter_type == '/JPXDecode':
                                        image_format = "JPEG2000"
                                
                                images.append({
                                    "name": str(obj_name),
                                    "data": image_data,
                                    "format": image_format
                                })
                                
                                self.logger.debug(
                                    f"Extracted image {obj_name} ({image_format}) "
                                    f"from page {page_num}"
                                )
                                
                            except Exception as e:
                                self.logger.warning(
                                    f"Error extracting image {obj_name} from page {page_num}: {str(e)}"
                                )
            
            self.logger.info(f"Extracted {len(images)} images from page {page_num}")
            return images
            
        except Exception as e:
            self.logger.error(f"Error extracting images from page {page_num}: {str(e)}")
            return images
