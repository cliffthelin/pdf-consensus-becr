# src/compareblocks/gbg/orientation.py
"""
Orientation and deskew detection using OpenCV for rotation detection.
Implements projection profile analysis and Hough line detection.
"""

import numpy as np
from typing import Tuple, Optional
from .types import OrientationHints

try:
    import cv2
except ImportError:
    cv2 = None


class OrientationDetector:
    """Detects page orientation and text block skew using OpenCV."""
    
    def __init__(self):
        if cv2 is None:
            raise ImportError("OpenCV is required for orientation detection. Install with: pip install opencv-python")
    
    def detect_page_orientation(self, image: np.ndarray) -> OrientationHints:
        """
        Detect page-level orientation using projection profile analysis.
        
        Args:
            image: Grayscale image array
            
        Returns:
            OrientationHints with page rotation and confidence
        """
        if len(image.shape) != 2:
            raise ValueError("Image must be grayscale")
        
        # Calculate projection profiles for different rotations
        rotations = [0, 90, 180, 270]
        profile_variances = []
        
        for rotation in rotations:
            rotated = self._rotate_image(image, rotation)
            
            # Calculate horizontal projection (sum of pixels in each row)
            h_projection = np.sum(rotated, axis=1)
            
            # Calculate variance - higher variance indicates better text alignment
            variance = np.var(h_projection)
            profile_variances.append(variance)
        
        # Find rotation with maximum variance (best text alignment)
        best_rotation_idx = np.argmax(profile_variances)
        best_rotation = rotations[best_rotation_idx]
        
        # Calculate confidence based on variance difference
        max_variance = profile_variances[best_rotation_idx]
        avg_variance = np.mean(profile_variances)
        confidence = min(1.0, (max_variance - avg_variance) / max_variance) if max_variance > 0 else 0.0
        
        return OrientationHints(
            page_rotation=float(best_rotation),
            confidence=confidence
        )
    
    def detect_block_skew(self, image: np.ndarray, bbox_region: Optional[np.ndarray] = None) -> OrientationHints:
        """
        Detect individual text block skew using Hough line detection.
        
        Args:
            image: Grayscale image array
            bbox_region: Optional cropped region for the specific block
            
        Returns:
            OrientationHints with block skew angle and confidence
        """
        if len(image.shape) != 2:
            raise ValueError("Image must be grayscale")
        
        # Use provided region or full image
        region = bbox_region if bbox_region is not None else image
        
        # Edge detection
        edges = cv2.Canny(region, 50, 150, apertureSize=3)
        
        # Hough line detection
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is None or len(lines) == 0:
            return OrientationHints(block_skew=0.0, confidence=0.0)
        
        # Extract angles from detected lines
        angles = []
        for line in lines:
            rho, theta = line[0]
            # Convert to degrees and normalize to [-45, 45] range
            angle_deg = np.degrees(theta) - 90
            if angle_deg > 45:
                angle_deg -= 90
            elif angle_deg < -45:
                angle_deg += 90
            angles.append(angle_deg)
        
        # Find dominant angle using histogram
        hist, bin_edges = np.histogram(angles, bins=18, range=(-45, 45))
        dominant_bin = np.argmax(hist)
        dominant_angle = (bin_edges[dominant_bin] + bin_edges[dominant_bin + 1]) / 2
        
        # Calculate confidence based on how many lines support the dominant angle
        total_lines = len(angles)
        supporting_lines = hist[dominant_bin]
        confidence = supporting_lines / total_lines if total_lines > 0 else 0.0
        
        # Detect vertical text (angles close to ±90 degrees)
        is_vertical = abs(dominant_angle) > 60
        
        return OrientationHints(
            block_skew=float(dominant_angle),
            is_vertical=is_vertical,
            confidence=confidence
        )
    
    def detect_combined_orientation(self, image: np.ndarray, bbox_region: Optional[np.ndarray] = None) -> OrientationHints:
        """
        Combine page-level and block-level orientation detection.
        
        Args:
            image: Full page grayscale image
            bbox_region: Optional cropped region for specific block
            
        Returns:
            Combined OrientationHints
        """
        # Detect page-level orientation
        page_hints = self.detect_page_orientation(image)
        
        # Detect block-level skew
        block_hints = self.detect_block_skew(image, bbox_region)
        
        # Combine results with weighted confidence
        combined_confidence = (page_hints.confidence + block_hints.confidence) / 2
        
        return OrientationHints(
            page_rotation=page_hints.page_rotation,
            block_skew=block_hints.block_skew,
            is_vertical=block_hints.is_vertical,
            confidence=combined_confidence
        )
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image by specified angle.
        
        Args:
            image: Input image
            angle: Rotation angle in degrees
            
        Returns:
            Rotated image
        """
        if angle == 0:
            return image
        
        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        
        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calculate new dimensions to avoid cropping
        cos_angle = abs(rotation_matrix[0, 0])
        sin_angle = abs(rotation_matrix[0, 1])
        new_width = int((height * sin_angle) + (width * cos_angle))
        new_height = int((height * cos_angle) + (width * sin_angle))
        
        # Adjust translation
        rotation_matrix[0, 2] += (new_width / 2) - center[0]
        rotation_matrix[1, 2] += (new_height / 2) - center[1]
        
        # Perform rotation
        rotated = cv2.warpAffine(image, rotation_matrix, (new_width, new_height), 
                                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, 
                                borderValue=255)
        
        return rotated


class ProjectionProfileAnalyzer:
    """Analyzes projection profiles for text orientation detection."""
    
    @staticmethod
    def calculate_horizontal_projection(image: np.ndarray) -> np.ndarray:
        """Calculate horizontal projection profile (sum of pixels per row)."""
        return np.sum(image, axis=1)
    
    @staticmethod
    def calculate_vertical_projection(image: np.ndarray) -> np.ndarray:
        """Calculate vertical projection profile (sum of pixels per column)."""
        return np.sum(image, axis=0)
    
    @staticmethod
    def analyze_projection_variance(projection: np.ndarray) -> float:
        """Calculate variance of projection profile."""
        return float(np.var(projection))
    
    @staticmethod
    def find_text_lines(horizontal_projection: np.ndarray, threshold_ratio: float = 0.1) -> list[Tuple[int, int]]:
        """
        Find text line boundaries from horizontal projection.
        
        Args:
            horizontal_projection: Horizontal projection array
            threshold_ratio: Ratio of max value to use as threshold
            
        Returns:
            List of (start, end) tuples for text lines
        """
        max_val = np.max(horizontal_projection)
        threshold = max_val * threshold_ratio
        
        # Find regions above threshold
        above_threshold = horizontal_projection > threshold
        
        # Find start and end points of continuous regions
        lines = []
        start = None
        
        for i, is_above in enumerate(above_threshold):
            if is_above and start is None:
                start = i
            elif not is_above and start is not None:
                lines.append((start, i - 1))
                start = None
        
        # Handle case where last line extends to end
        if start is not None:
            lines.append((start, len(horizontal_projection) - 1))
        
        return lines