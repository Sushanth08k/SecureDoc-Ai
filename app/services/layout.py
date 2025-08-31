from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import math
from collections import defaultdict

# Configure logging
logger = logging.getLogger(__name__)

class LayoutAnalysisService:
    """
    Service for document layout analysis and field detection
    
    This service processes document images to detect:
    - Document structure
    - Form fields
    - Tables
    - Headers and footers
    - Other document elements
    """
    
    @staticmethod
    def analyze_layout(ocr_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze document layout and structure from OCR results
        
        Args:
            ocr_results: List of OCR results, one per page
            
        Returns:
            Dictionary with layout analysis results
        """
        if not ocr_results:
            return {
                "status": "error",
                "message": "No OCR results provided for layout analysis"
            }
        
        layout_results = []
        
        for page_num, page_ocr in enumerate(ocr_results):
            try:
                if page_ocr.get("status") != "success":
                    logger.warning(f"Skipping layout analysis for page {page_num+1} due to OCR errors")
                    layout_results.append({
                        "page_num": page_num + 1,
                        "status": "error",
                        "message": f"OCR failed for this page: {page_ocr.get('message', 'Unknown error')}"
                    })
                    continue
                
                # Extract words with bounding boxes
                words = page_ocr.get("words", [])
                
                if not words:
                    logger.warning(f"No words found in OCR results for page {page_num+1}")
                    layout_results.append({
                        "page_num": page_num + 1,
                        "status": "warning",
                        "message": "No words found in OCR results"
                    })
                    continue
                
                # Identify form fields (key-value pairs)
                form_fields = LayoutAnalysisService._detect_form_fields(words)
                
                # Identify table structures
                tables = LayoutAnalysisService._detect_tables(words)
                
                # Identify text blocks
                text_blocks = LayoutAnalysisService._detect_text_blocks(words)
                
                layout_results.append({
                    "page_num": page_num + 1,
                    "status": "success",
                    "forms": form_fields,
                    "tables": tables,
                    "text_blocks": text_blocks
                })
                
            except Exception as e:
                logger.error(f"Error in layout analysis for page {page_num+1}: {str(e)}", exc_info=True)
                layout_results.append({
                    "page_num": page_num + 1,
                    "status": "error",
                    "message": f"Layout analysis error: {str(e)}"
                })
        
        return {
            "status": "success",
            "pages": len(layout_results),
            "results": layout_results
        }
    
    @staticmethod
    def _detect_form_fields(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect form fields (key-value pairs) from OCR words
        
        Args:
            words: List of words with bounding boxes from OCR
            
        Returns:
            List of detected form fields
        """
        form_fields = []
        
        # Simple heuristic: look for words with a colon followed by other words on same line
        # This is a simplified stub implementation
        
        # Group words by their approximate y-coordinate (line)
        lines = defaultdict(list)
        for word in words:
            # Get the middle y-coordinate of the word
            if 'bbox' in word and len(word['bbox']) == 4:
                y_middle = word['bbox'][1] + (word['bbox'][3] / 2)
                # Round to nearest 10 pixels to group words on the same line
                line_key = int(y_middle / 10) * 10
                lines[line_key].append(word)
        
        # Sort words in each line by x-coordinate
        for line_key in lines:
            lines[line_key].sort(key=lambda w: w['bbox'][0])
        
        # Look for potential form fields
        for line_key, line_words in lines.items():
            for i, word in enumerate(line_words):
                # Look for words ending with colon or other field indicators
                if word['word'].endswith(':') or word['word'].lower() in ['name', 'address', 'phone', 'email', 'date', 'id']:
                    # If this is a field label, the rest of the line might be the value
                    if i < len(line_words) - 1:
                        field_name = word['word'].rstrip(':')
                        # Combine the rest of the words on this line as the value
                        field_value = ' '.join(w['word'] for w in line_words[i+1:])
                        
                        # Calculate bounding box covering field name and value
                        x1 = word['bbox'][0]
                        y1 = min(w['bbox'][1] for w in line_words[i:])
                        x2 = line_words[-1]['bbox'][0] + line_words[-1]['bbox'][2]
                        y2 = max(w['bbox'][1] + w['bbox'][3] for w in line_words[i:])
                        
                        form_fields.append({
                            "field": field_name,
                            "value": field_value,
                            "bbox": [x1, y1, x2 - x1, y2 - y1]
                        })
        
        return form_fields
    
    @staticmethod
    def _detect_tables(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect tables from OCR words
        
        Args:
            words: List of words with bounding boxes from OCR
            
        Returns:
            List of detected tables
        """
        # This is a simplified stub implementation
        # In a real implementation, we would look for grid-like structures
        
        # Look for evenly spaced words that might indicate table cells
        tables = []
        
        # Group words by their approximate y-coordinate (potential table rows)
        potential_rows = defaultdict(list)
        for word in words:
            if 'bbox' in word and len(word['bbox']) == 4:
                y_middle = word['bbox'][1] + (word['bbox'][3] / 2)
                # Round to nearest 5 pixels for tighter grouping
                row_key = int(y_middle / 5) * 5
                potential_rows[row_key].append(word)
        
        # Look for 3+ rows with similar word counts and alignment
        row_keys = sorted(potential_rows.keys())
        potential_tables = []
        
        for i in range(len(row_keys) - 2):  # Need at least 3 rows
            row1 = potential_rows[row_keys[i]]
            row2 = potential_rows[row_keys[i+1]]
            row3 = potential_rows[row_keys[i+2]]
            
            # Check if the rows have similar number of words (potential table cells)
            if (abs(len(row1) - len(row2)) <= 1 and 
                abs(len(row2) - len(row3)) <= 1 and
                len(row1) >= 2):  # At least 2 columns
                
                # Sort words in each row by x-coordinate
                row1.sort(key=lambda w: w['bbox'][0])
                row2.sort(key=lambda w: w['bbox'][0])
                row3.sort(key=lambda w: w['bbox'][0])
                
                # Check if words are roughly aligned in columns
                aligned = True
                for j in range(min(len(row1), len(row2), len(row3))):
                    if j < len(row1) and j < len(row2) and j < len(row3):
                        x1 = row1[j]['bbox'][0]
                        x2 = row2[j]['bbox'][0]
                        x3 = row3[j]['bbox'][0]
                        
                        # Check if the x-coordinates are within a reasonable range
                        if max(x1, x2, x3) - min(x1, x2, x3) > 50:  # 50 pixel threshold
                            aligned = False
                            break
                
                if aligned:
                    # Calculate table bounds
                    min_x = min(min(w['bbox'][0] for w in row1),
                               min(w['bbox'][0] for w in row2),
                               min(w['bbox'][0] for w in row3))
                    
                    max_x = max(max(w['bbox'][0] + w['bbox'][2] for w in row1),
                               max(w['bbox'][0] + w['bbox'][2] for w in row2),
                               max(w['bbox'][0] + w['bbox'][2] for w in row3))
                    
                    min_y = min(min(w['bbox'][1] for w in row1),
                               min(w['bbox'][1] for w in row2),
                               min(w['bbox'][1] for w in row3))
                    
                    max_y = max(max(w['bbox'][1] + w['bbox'][3] for w in row1),
                               max(w['bbox'][1] + w['bbox'][3] for w in row2),
                               max(w['bbox'][1] + w['bbox'][3] for w in row3))
                    
                    # Look for more rows above and below
                    top_row_idx = i
                    bottom_row_idx = i + 2
                    
                    # Check rows above
                    for j in range(i-1, -1, -1):
                        row = potential_rows[row_keys[j]]
                        if abs(len(row) - len(row1)) <= 1:
                            top_row_idx = j
                        else:
                            break
                            
                    # Check rows below
                    for j in range(i+3, len(row_keys)):
                        row = potential_rows[row_keys[j]]
                        if abs(len(row) - len(row3)) <= 1:
                            bottom_row_idx = j
                        else:
                            break
                    
                    # Recalculate bounds with all rows
                    all_table_rows = []
                    for j in range(top_row_idx, bottom_row_idx + 1):
                        row = potential_rows[row_keys[j]]
                        row.sort(key=lambda w: w['bbox'][0])
                        all_table_rows.append(row)
                        
                        # Update bounds
                        if row:
                            row_min_x = min(w['bbox'][0] for w in row)
                            row_max_x = max(w['bbox'][0] + w['bbox'][2] for w in row)
                            row_min_y = min(w['bbox'][1] for w in row)
                            row_max_y = max(w['bbox'][1] + w['bbox'][3] for w in row)
                            
                            min_x = min(min_x, row_min_x)
                            max_x = max(max_x, row_max_x)
                            min_y = min(min_y, row_min_y)
                            max_y = max(max_y, row_max_y)
                    
                    # Create table cells
                    cells = []
                    for row_idx, row in enumerate(all_table_rows):
                        for col_idx, word in enumerate(row):
                            cells.append({
                                "row": row_idx,
                                "col": col_idx,
                                "text": word['word'],
                                "bbox": word['bbox']
                            })
                    
                    tables.append({
                        "bbox": [min_x, min_y, max_x - min_x, max_y - min_y],
                        "rows": len(all_table_rows),
                        "cols": max(len(row) for row in all_table_rows),
                        "cells": cells
                    })
                    
                    # Skip the rows we've already processed
                    i = bottom_row_idx
        
        return tables
    
    @staticmethod
    def _detect_text_blocks(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect text blocks from OCR words
        
        Args:
            words: List of words with bounding boxes from OCR
            
        Returns:
            List of detected text blocks
        """
        if not words:
            return []
            
        # Group words into lines based on y-coordinate
        lines = defaultdict(list)
        for word in words:
            if 'bbox' in word and len(word['bbox']) == 4:
                y_middle = word['bbox'][1] + (word['bbox'][3] / 2)
                # Round to nearest 5 pixels for tighter grouping
                line_key = int(y_middle / 5) * 5
                lines[line_key].append(word)
        
        # Sort lines by y-coordinate
        sorted_line_keys = sorted(lines.keys())
        
        # Group adjacent lines into paragraphs/blocks
        blocks = []
        current_block = []
        current_block_lines = []
        
        for i, line_key in enumerate(sorted_line_keys):
            line_words = sorted(lines[line_key], key=lambda w: w['bbox'][0])
            
            # Skip empty lines
            if not line_words:
                continue
                
            # If this is the first line or it's close to the previous line
            if not current_block or (line_key - sorted_line_keys[i-1] < 20):  # 20 pixel threshold
                current_block.extend(line_words)
                current_block_lines.append(line_words)
            else:
                # We've found a new block, save the current one
                if current_block:
                    # Calculate block bounds
                    min_x = min(w['bbox'][0] for w in current_block)
                    min_y = min(w['bbox'][1] for w in current_block)
                    max_x = max(w['bbox'][0] + w['bbox'][2] for w in current_block)
                    max_y = max(w['bbox'][1] + w['bbox'][3] for w in current_block)
                    
                    # Reconstruct text
                    text = " ".join([" ".join(w['word'] for w in line) for line in current_block_lines])
                    
                    # Determine if this might be a heading based on font size or position
                    is_heading = False
                    if len(current_block_lines) == 1:  # Single line
                        # Check if font size is larger than average
                        avg_height = sum(w['bbox'][3] for w in current_block) / len(current_block)
                        avg_height_all = sum(w['bbox'][3] for w in words) / len(words)
                        
                        if avg_height > avg_height_all * 1.2:  # 20% larger than average
                            is_heading = True
                    
                    blocks.append({
                        "text": text,
                        "bbox": [min_x, min_y, max_x - min_x, max_y - min_y],
                        "type": "heading" if is_heading else "paragraph",
                        "line_count": len(current_block_lines),
                        "word_count": len(current_block)
                    })
                
                # Start a new block
                current_block = line_words
                current_block_lines = [line_words]
        
        # Don't forget the last block
        if current_block:
            min_x = min(w['bbox'][0] for w in current_block)
            min_y = min(w['bbox'][1] for w in current_block)
            max_x = max(w['bbox'][0] + w['bbox'][2] for w in current_block)
            max_y = max(w['bbox'][1] + w['bbox'][3] for w in current_block)
            
            text = " ".join([" ".join(w['word'] for w in line) for line in current_block_lines])
            
            # Determine if this might be a heading
            is_heading = False
            if len(current_block_lines) == 1:  # Single line
                avg_height = sum(w['bbox'][3] for w in current_block) / len(current_block)
                avg_height_all = sum(w['bbox'][3] for w in words) / len(words)
                
                if avg_height > avg_height_all * 1.2:  # 20% larger than average
                    is_heading = True
            
            blocks.append({
                "text": text,
                "bbox": [min_x, min_y, max_x - min_x, max_y - min_y],
                "type": "heading" if is_heading else "paragraph",
                "line_count": len(current_block_lines),
                "word_count": len(current_block)
            })
        
        return blocks
    
    @staticmethod
    def process_document(ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document's OCR results for layout analysis
        
        Args:
            ocr_results: OCR results dictionary
            
        Returns:
            Dictionary with layout analysis results
        """
        if ocr_results.get("status") != "success":
            return {
                "status": "error",
                "message": "Cannot process document due to OCR errors"
            }
        
        # Extract the list of page results
        page_results = ocr_results.get("results", [])
        
        # Analyze layout across all pages
        layout_results = LayoutAnalysisService.analyze_layout(page_results)
        
        # Count document elements
        form_fields_count = 0
        tables_count = 0
        text_blocks_count = 0
        
        for page in layout_results.get("results", []):
            if page.get("status") == "success":
                form_fields_count += len(page.get("forms", []))
                tables_count += len(page.get("tables", []))
                text_blocks_count += len(page.get("text_blocks", []))
        
        return {
            "status": "success",
            "pages": len(layout_results.get("results", [])),
            "results": layout_results.get("results", []),
            "summary": {
                "form_fields": form_fields_count,
                "tables": tables_count,
                "text_blocks": text_blocks_count
            }
        }
        
        # Group words by their approximate y-coordinate (line)
        lines = defaultdict(list)
        for word in words:
            if 'bbox' in word and len(word['bbox']) == 4:
                y_middle = word['bbox'][1] + (word['bbox'][3] / 2)
                # Round to nearest 10 pixels to group words on the same line
                line_key = int(y_middle / 10) * 10
                lines[line_key].append(word)
        
        # Sort lines by y-coordinate
        sorted_lines = sorted(lines.keys())
        
        # Group adjacent lines into blocks
        current_block = []
        current_block_lines = []
        
        for i, line_key in enumerate(sorted_lines):
            line_words = sorted(lines[line_key], key=lambda w: w['bbox'][0])
            
            # Start a new block if this is the first line or there's a gap
            if not current_block or line_key - sorted_lines[i-1] > 30:  # 30 pixel gap threshold
                # Save the previous block if it exists
                if current_block:
                    # Calculate block bounds
                    min_x = min(w['bbox'][0] for w in current_block)
                    max_x = max(w['bbox'][0] + w['bbox'][2] for w in current_block)
                    min_y = min(w['bbox'][1] for w in current_block)
                    max_y = max(w['bbox'][1] + w['bbox'][3] for w in current_block)
                    
                    # Reconstruct text with line breaks
                    text = "\n".join(" ".join(w['word'] for w in line) for line in current_block_lines)
                    
                    text_blocks.append({
                        "text": text,
                        "bbox": [min_x, min_y, max_x - min_x, max_y - min_y],
                        "lines": len(current_block_lines)
                    })
                
                # Start new block
                current_block = line_words
                current_block_lines = [line_words]
            else:
                # Continue current block
                current_block.extend(line_words)
                current_block_lines.append(line_words)
        
        # Add the last block
        if current_block:
            # Calculate block bounds
            min_x = min(w['bbox'][0] for w in current_block)
            max_x = max(w['bbox'][0] + w['bbox'][2] for w in current_block)
            min_y = min(w['bbox'][1] for w in current_block)
            max_y = max(w['bbox'][1] + w['bbox'][3] for w in current_block)
            
            # Reconstruct text with line breaks
            text = "\n".join(" ".join(w['word'] for w in line) for line in current_block_lines)
            
            text_blocks.append({
                "text": text,
                "bbox": [min_x, min_y, max_x - min_x, max_y - min_y],
                "lines": len(current_block_lines)
            })
        
        return text_blocks
    
    @staticmethod
    def process_document(ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document's OCR results for layout analysis
        
        Args:
            ocr_results: OCR results dictionary
            
        Returns:
            Dictionary with layout analysis results
        """
        if ocr_results.get("status") != "success":
            return {
                "status": "error",
                "message": "Cannot process document due to OCR errors"
            }
        
        # Extract the list of page results
        page_results = ocr_results.get("results", [])
        
        # Analyze layout
        layout_result = LayoutAnalysisService.analyze_layout(page_results)
        
        return layout_result
