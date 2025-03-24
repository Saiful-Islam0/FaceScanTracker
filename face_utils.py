import logging
import os
import hashlib
import base64

logger = logging.getLogger(__name__)

def extract_face_encoding(image_path):
    """
    Generate a simple image hash for comparison
    
    Args:
        image_path: Path to image file
        
    Returns:
        Image hash for comparison
    """
    try:
        # Load the image
        with open(image_path, 'rb') as f:
            img_data = f.read()
            
        # Create a simple hash of the image data
        # This is not actually face recognition, but a simple proof of concept
        # In a real application, you'd want to use proper face recognition
        hash_obj = hashlib.md5(img_data)
        image_hash = hash_obj.hexdigest()
        
        # Convert a small portion of the image to base64 for display
        # This is for demonstration only, not real face recognition
        thumbnail_data = img_data[:1024] if len(img_data) > 1024 else img_data
        thumbnail = base64.b64encode(thumbnail_data).decode('utf-8')
            
        return {
            'hash': image_hash,
            'thumbnail': thumbnail
        }
    
    except Exception as e:
        logger.exception(f"Error processing image from {image_path}")
        return None

def find_matching_face(face_encoding, enrollments, tolerance=None):
    """
    Find a matching face in the enrollments using image hash
    
    Args:
        face_encoding: Face encoding to match
        enrollments: List of enrollment records
        tolerance: Not used in this implementation
        
    Returns:
        Matching enrollment record or None if no match found
    """
    try:
        if not enrollments or not face_encoding:
            return None
        
        # Get the hash from the encoding
        image_hash = face_encoding.get('hash')
        if not image_hash:
            return None
        
        # Look for an exact match in the enrollments
        for enrollment in enrollments:
            if 'encoding' not in enrollment:
                continue
                
            enrollment_encoding = enrollment['encoding']
            enrollment_hash = enrollment_encoding.get('hash')
            
            if enrollment_hash == image_hash:
                return enrollment
        
        return None
    
    except Exception as e:
        logger.exception("Error finding matching face")
        return None
