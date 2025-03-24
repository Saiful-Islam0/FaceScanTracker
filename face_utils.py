import logging
import os
import hashlib
import base64
from PIL import Image, ImageFilter, ImageOps
import io
import math

logger = logging.getLogger(__name__)

def extract_face_encoding(image_path):
    """
    Generate a simplified image representation for comparison
    
    Args:
        image_path: Path to image file
        
    Returns:
        Image hash and features for comparison
    """
    try:
        # Load the image with PIL
        img = Image.open(image_path)
        if not img:
            logger.error(f"Failed to load image from {image_path}")
            return None
            
        # Convert to grayscale for simpler processing
        gray = img.convert('L')
        
        # Resize to a standard size to ensure consistent comparison
        resized = gray.resize((100, 100))
        
        # Apply Gaussian blur to reduce noise and minor differences
        blurred = resized.filter(ImageFilter.GaussianBlur(radius=2))
        
        # Create a perceptual hash (pHash) based on DCT
        # This is a simplified approach - divide image to 8x8 blocks and get avg values
        simplified = blurred.resize((8, 8), Image.Resampling.LANCZOS)
        
        # Get pixel data
        pixels = list(simplified.getdata())
        avg_value = sum(pixels) / len(pixels)
        
        # Create a 64-bit hash based on whether pixel value is above average
        perceptual_hash = ""
        for pixel in pixels:
            perceptual_hash += "1" if pixel > avg_value else "0"
            
        # Also calculate average values in different regions of the image
        # Divide into 4x4 grid and calculate average intensity in each cell
        width, height = blurred.size
        cell_width, cell_height = width // 4, height // 4
        region_values = []
        
        for y in range(0, height, cell_height):
            for x in range(0, width, cell_width):
                # Get region
                region = blurred.crop((x, y, min(x + cell_width, width), min(y + cell_height, height)))
                region_pixels = list(region.getdata())
                avg = sum(region_pixels) / len(region_pixels) if region_pixels else 0
                region_values.append(avg)
        
        # Create features for comparison
        features = {
            'phash': perceptual_hash,
            'regions': region_values
        }
        
        # Also include a traditional hash
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        hash_obj = hashlib.md5(img_bytes.getvalue())
        image_hash = hash_obj.hexdigest()
        
        # Create a small thumbnail for reference
        small_img = img.resize((50, 50))
        thumbnail_bytes = io.BytesIO()
        small_img.save(thumbnail_bytes, format='JPEG')
        thumbnail = base64.b64encode(thumbnail_bytes.getvalue()).decode('utf-8')
            
        return {
            'hash': image_hash,
            'thumbnail': thumbnail,
            'features': features
        }
    
    except Exception as e:
        logger.exception(f"Error processing image from {image_path}")
        return None

def calculate_hamming_distance(hash1, hash2):
    """Calculate Hamming distance between two binary strings"""
    if len(hash1) != len(hash2):
        return -1
    
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))

def calculate_region_similarity(regions1, regions2):
    """Calculate similarity between region features using Euclidean distance"""
    if len(regions1) != len(regions2):
        return 0
    
    # Calculate Euclidean distance
    sq_diff_sum = sum((r1 - r2) ** 2 for r1, r2 in zip(regions1, regions2))
    euclidean_dist = math.sqrt(sq_diff_sum)
    
    # Convert to similarity score (0-1 range, where 1 is identical)
    # Normalize based on max possible distance in the space
    max_possible_dist = math.sqrt(len(regions1) * (255 ** 2))  # assuming 0-255 range
    similarity = 1 - (euclidean_dist / max_possible_dist)
    
    return similarity

def find_matching_face(face_encoding, enrollments, tolerance=0.70):
    """
    Find a matching face in the enrollments using image features
    
    Args:
        face_encoding: Face encoding to match
        enrollments: List of enrollment records
        tolerance: Similarity threshold (0-1), higher means more lenient
        
    Returns:
        Matching enrollment record or None if no match found
    """
    try:
        if not enrollments or not face_encoding:
            return None
        
        # Get the features from the encoding
        if 'features' not in face_encoding:
            logger.warning("No features found in face encoding")
            return None
            
        query_features = face_encoding['features']
        query_phash = query_features.get('phash')
        query_regions = query_features.get('regions', [])
        
        if not query_phash:
            logger.warning("No perceptual hash found in encoding")
            return None
        
        best_match = None
        best_score = 0
        
        # Compare with all enrollments
        for enrollment in enrollments:
            if 'encoding' not in enrollment or 'features' not in enrollment['encoding']:
                continue
                
            enrollment_features = enrollment['encoding']['features']
            
            # Check for required features
            if 'phash' not in enrollment_features:
                continue
                
            enroll_phash = enrollment_features['phash']
            enroll_regions = enrollment_features.get('regions', [])
            
            # Calculate hamming distance for perceptual hash (smaller is better)
            hamming_dist = calculate_hamming_distance(query_phash, enroll_phash)
            if hamming_dist < 0:  # invalid comparison
                continue
                
            # Convert to similarity score (0-1 range, where 1 is identical)
            # For 64-bit hash, max distance is 64
            phash_similarity = 1 - (hamming_dist / 64)
            
            # Calculate region similarity (if available)
            region_similarity = 0
            if query_regions and enroll_regions:
                region_similarity = calculate_region_similarity(query_regions, enroll_regions)
            
            # Combine scores (weighted average)
            # Weight perceptual hash more heavily as it's more reliable
            combined_score = (0.7 * phash_similarity) + (0.3 * region_similarity)
            
            logger.debug(f"Comparing with {enrollment['name']}: score {combined_score:.4f}")
            
            # If this is the best match so far and it meets our threshold
            if combined_score > best_score and combined_score > tolerance:
                best_score = combined_score
                best_match = enrollment
        
        if best_match:
            logger.info(f"Found match: {best_match['name']} with score {best_score:.4f}")
        else:
            logger.info(f"No match found. Best score was {best_score:.4f}")
            
        return best_match
    
    except Exception as e:
        logger.exception("Error finding matching face")
        return None
