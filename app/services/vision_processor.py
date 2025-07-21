import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
import easyocr
from typing import Dict, List, Any, Tuple
import json

class VisionProcessor:
    """Handles multi-modal analysis of documents using Vision Language Models"""
    
    def __init__(self):
        try:
            self.easyocr_reader = easyocr.Reader(['en'])
        except:
            self.easyocr_reader = None
        
        self.tesseract_config = '--oem 3 --psm 6'
        
        self.clip_model = None
        try:
            import clip
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=device)
            self.clip_device = device
        except:
            pass
    
    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Perform comprehensive visual analysis of a document"""
        
        try:
            image = self._load_image(file_path)
            if image is None:
                return {'error': 'Could not load image'}
            
            analysis_result = {
                'ocr_text': self._extract_text_with_ocr(image),
                'layout_analysis': self._analyze_layout(image),
                'table_detection': self._detect_tables(image),
                'visual_elements': self._detect_visual_elements(image),
                'handwriting_detection': self._detect_handwriting(image),
                'quality_assessment': self._assess_image_quality(image)
            }
            
            return analysis_result
            
        except Exception as e:
            return {'error': f'Vision processing failed: {str(e)}'}
    
    def _load_image(self, file_path: str) -> np.ndarray:
        """Load image from file path"""
        
        if file_path.lower().endswith('.pdf'):
            return self._pdf_to_image(file_path)
        else:
            image = cv2.imread(file_path)
            if image is not None:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            return None
    
    def _pdf_to_image(self, pdf_path: str) -> np.ndarray:
        """Convert first page of PDF to image"""
        
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page = doc[0]  # First page
            pix = page.get_pixmap()
            img_data = pix.tobytes("ppm")
            
            from io import BytesIO
            img = Image.open(BytesIO(img_data))
            return np.array(img)
            
        except ImportError:
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(pdf_path, first_page=1, last_page=1)
                if images:
                    return np.array(images[0])
            except ImportError:
                pass
        
        return None
    
    def _extract_text_with_ocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text using multiple OCR engines"""
        
        ocr_results = {}
        
        try:
            pil_image = Image.fromarray(image)
            tesseract_text = pytesseract.image_to_string(pil_image, config=self.tesseract_config)
            tesseract_data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
            
            ocr_results['tesseract'] = {
                'text': tesseract_text,
                'confidence': np.mean([int(conf) for conf in tesseract_data['conf'] if int(conf) > 0]),
                'word_count': len([word for word in tesseract_data['text'] if word.strip()])
            }
        except Exception as e:
            ocr_results['tesseract'] = {'error': str(e)}
        
        if self.easyocr_reader:
            try:
                easyocr_results = self.easyocr_reader.readtext(image)
                easyocr_text = ' '.join([result[1] for result in easyocr_results])
                easyocr_confidence = np.mean([result[2] for result in easyocr_results])
                
                ocr_results['easyocr'] = {
                    'text': easyocr_text,
                    'confidence': easyocr_confidence,
                    'word_count': len(easyocr_results)
                }
            except Exception as e:
                ocr_results['easyocr'] = {'error': str(e)}
        
        best_text = ""
        best_confidence = 0
        
        for engine, result in ocr_results.items():
            if 'confidence' in result and result['confidence'] > best_confidence:
                best_confidence = result['confidence']
                best_text = result['text']
        
        return {
            'combined_text': best_text,
            'best_confidence': best_confidence,
            'engine_results': ocr_results
        }
    
    def _analyze_layout(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze document layout and structure"""
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        text_regions = self._detect_text_regions(gray)
        
        columns = self._detect_columns(gray)
        
        headers_footers = self._detect_headers_footers(gray)
        
        return {
            'text_regions': text_regions,
            'column_count': len(columns),
            'columns': columns,
            'headers_footers': headers_footers,
            'layout_type': self._classify_layout(text_regions, columns)
        }
    
    def _detect_text_regions(self, gray_image: np.ndarray) -> List[Dict]:
        """Detect text regions in the image"""
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        
        _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        text_regions = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w > 20 and h > 10:
                text_regions.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'area': int(w * h)
                })
        
        return sorted(text_regions, key=lambda r: r['y'])  # Sort by vertical position
    
    def _detect_columns(self, gray_image: np.ndarray) -> List[Dict]:
        """Detect column structure in the document"""
        
        height, width = gray_image.shape
        
        horizontal_projection = np.sum(gray_image < 128, axis=0)
        
        valleys = []
        threshold = np.mean(horizontal_projection) * 0.3
        
        for i in range(1, len(horizontal_projection) - 1):
            if (horizontal_projection[i] < threshold and 
                horizontal_projection[i] < horizontal_projection[i-1] and 
                horizontal_projection[i] < horizontal_projection[i+1]):
                valleys.append(i)
        
        columns = []
        if valleys:
            boundaries = [0] + valleys + [width]
            
            for i in range(len(boundaries) - 1):
                columns.append({
                    'start_x': boundaries[i],
                    'end_x': boundaries[i + 1],
                    'width': boundaries[i + 1] - boundaries[i]
                })
        else:
            columns.append({
                'start_x': 0,
                'end_x': width,
                'width': width
            })
        
        return columns
    
    def _detect_headers_footers(self, gray_image: np.ndarray) -> Dict[str, Any]:
        """Detect headers and footers in the document"""
        
        height, width = gray_image.shape
        
        header_region = gray_image[:int(height * 0.1), :]
        footer_region = gray_image[int(height * 0.9):, :]
        
        header_text_density = np.sum(header_region < 128) / header_region.size
        footer_text_density = np.sum(footer_region < 128) / footer_region.size
        
        return {
            'has_header': header_text_density > 0.05,
            'has_footer': footer_text_density > 0.05,
            'header_text_density': float(header_text_density),
            'footer_text_density': float(footer_text_density)
        }
    
    def _classify_layout(self, text_regions: List[Dict], columns: List[Dict]) -> str:
        """Classify the document layout type"""
        
        if len(columns) == 1:
            return "single_column"
        elif len(columns) == 2:
            return "two_column"
        elif len(columns) > 2:
            return "multi_column"
        else:
            return "unknown"
    
    def _detect_tables(self, image: np.ndarray) -> List[Dict]:
        """Detect tables in the document"""
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        horizontal_lines = self._detect_horizontal_lines(gray)
        vertical_lines = self._detect_vertical_lines(gray)
        
        tables = self._find_table_intersections(horizontal_lines, vertical_lines, gray.shape)
        
        return tables
    
    def _detect_horizontal_lines(self, gray_image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect horizontal lines in the image"""
        
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        
        _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
        
        contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lines = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 50:  # Minimum line length
                lines.append((x, y, x + w, y + h))
        
        return lines
    
    def _detect_vertical_lines(self, gray_image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect vertical lines in the image"""
        
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)
        
        contours, _ = cv2.findContours(vertical_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        lines = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if h > 50:  # Minimum line length
                lines.append((x, y, x + w, y + h))
        
        return lines
    
    def _find_table_intersections(self, h_lines: List, v_lines: List, image_shape: Tuple) -> List[Dict]:
        """Find table structures from line intersections"""
        
        tables = []
        
        if len(h_lines) >= 2 and len(v_lines) >= 2:
            for i, h1 in enumerate(h_lines[:-1]):
                for j, h2 in enumerate(h_lines[i+1:], i+1):
                    for k, v1 in enumerate(v_lines[:-1]):
                        for l, v2 in enumerate(v_lines[k+1:], k+1):
                            table_region = {
                                'top': min(h1[1], h2[1]),
                                'bottom': max(h1[1], h2[1]),
                                'left': min(v1[0], v2[0]),
                                'right': max(v1[0], v2[0])
                            }
                            
                            width = table_region['right'] - table_region['left']
                            height = table_region['bottom'] - table_region['top']
                            
                            if width > 100 and height > 50:
                                tables.append({
                                    'region': table_region,
                                    'width': width,
                                    'height': height,
                                    'confidence': 0.8
                                })
        
        return tables
    
    def _detect_visual_elements(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect various visual elements like charts, diagrams, etc."""
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
                                  param1=50, param2=30, minRadius=10, maxRadius=100)
        
        circle_count = len(circles[0]) if circles is not None else 0
        
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        line_count = len(lines) if lines is not None else 0
        
        return {
            'circles_detected': circle_count,
            'lines_detected': line_count,
            'has_diagrams': circle_count > 0 or line_count > 10,
            'visual_complexity': 'high' if (circle_count + line_count) > 20 else 'low'
        }
    
    def _detect_handwriting(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect if the document contains handwritten content"""
        
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        edges = cv2.Canny(gray, 50, 150)
        
        edge_density = np.sum(edges > 0) / edges.size
        
        horizontal_projection = np.sum(gray < 128, axis=1)
        line_variance = np.var(horizontal_projection)
        
        handwriting_score = (edge_density * 1000 + line_variance / 1000) / 2
        
        is_handwritten = handwriting_score > 5.0  # Threshold to be tuned
        
        return {
            'is_handwritten': is_handwritten,
            'handwriting_score': float(handwriting_score),
            'edge_density': float(edge_density),
            'line_variance': float(line_variance)
        }
    
    def _assess_image_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Assess the quality of the document image"""
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        contrast = gray.std()
        
        brightness = gray.mean()
        
        quality_score = min(100, (laplacian_var / 100 + contrast / 50 + (255 - abs(brightness - 128)) / 255) * 33.33)
        
        return {
            'sharpness': float(laplacian_var),
            'contrast': float(contrast),
            'brightness': float(brightness),
            'quality_score': float(quality_score),
            'quality_rating': 'high' if quality_score > 70 else 'medium' if quality_score > 40 else 'low'
        }
