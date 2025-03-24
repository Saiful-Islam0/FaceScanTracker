import logging
import os
import hashlib
import base64
import math

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
        # Load the image data
        with open(image_path, 'rb') as f:
            img_data = f.read()
        
        # Calculate a hash of chunks of the image data (simulating regions)
        # This is a very simplistic approach but doesn't require external libraries
        chunk_size = len(img_data) // 16  # Divide into 16 chunks
        if chunk_size < 1:
            chunk_size = 1
            
        chunks = []
        region_values = []
        
        # Calculate hash for each chunk
        for i in range(0, len(img_data), chunk_size):
            chunk = img_data[i:i+chunk_size]
            chunk_hash = hashlib.md5(chunk).hexdigest()
            chunks.append(chunk_hash)
            
            # For region values, use the average byte value
            avg_val = sum(byte for byte in chunk) / len(chunk) if chunk else 0
            region_values.append(avg_val)
        
        # Create a simulated perceptual hash from these chunks
        perceptual_hash = ""
        for chunk_hash in chunks[:8]:  # Use first 8 chunks
            # Take first 8 bits of each chunk hash
            for c in chunk_hash[:2]:  # First 2 hex chars = 8 bits
                # Convert hex char to binary representation
                bin_val = bin(int(c, 16))[2:].zfill(4)  # Get 4 bits
                perceptual_hash += bin_val
        
        # Ensure we have a 64-bit hash (if fewer chunks, repeat)
        perceptual_hash = perceptual_hash[:64].ljust(64, '0')
        
        # Create a traditional hash
        hash_obj = hashlib.md5(img_data)
        image_hash = hash_obj.hexdigest()
        
        # Create a small thumbnail for reference (use base64 of first part of image)
        thumbnail_data = img_data[:4096] if len(img_data) > 4096 else img_data
        thumbnail = base64.b64encode(thumbnail_data).decode('utf-8')
        
        # Create features for comparison
        features = {
            'phash': perceptual_hash,
            'regions': region_values[:16]  # Limit to 16 regions
        }
            
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

def find_matching_face(face_encoding, enrollments, tolerance=0.60):
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
            # Adjust weights to give even more importance to perceptual hash
            # and also use the traditional hash as a fallback
            
            # Check if traditional hash matches exactly - if so, boost the score
            hash_boost = 0.0
            if face_encoding.get('hash') == enrollment['encoding'].get('hash'):
                hash_boost = 0.2  # Big boost for exact match
                
            # Calculate combined score with adjusted weights and potential boost
            combined_score = (0.8 * phash_similarity) + (0.2 * region_similarity) + hash_boost
            
            logger.debug(f"Comparing with {enrollment['name']}: score {combined_score:.4f}")
            
            # If this is the best match so far and it meets our threshold
            if combined_score > best_score and combined_score > tolerance:
                best_score = combined_score
                best_match = enrollment
        
        if best_match:
            logger.info(f"Found match: {best_match['name']} with score {best_score:.4f}")
        else:
            # Find the closest match for debugging purposes
            closest_name = "none"
            closest_score = 0
            
            for enrollment in enrollments:
                if 'encoding' not in enrollment:
                    continue
                    
                name = enrollment.get('name', 'unknown')
                query_phash = face_encoding['features'].get('phash', '')
                
                if 'features' in enrollment['encoding'] and 'phash' in enrollment['encoding']['features']:
                    enroll_phash = enrollment['encoding']['features']['phash']
                    # Quick hamming distance check
                    hamming_dist = calculate_hamming_distance(query_phash, enroll_phash)
                    if hamming_dist >= 0:
                        score = 1 - (hamming_dist / 64)
                        if score > closest_score:
                            closest_score = score
                            closest_name = name
            
            logger.info(f"No match found. Best score was {best_score:.4f}, closest was {closest_name} with raw pHash score {closest_score:.4f}")
            
        return best_match
    
    except Exception as e:
        logger.exception("Error finding matching face")
        return None
