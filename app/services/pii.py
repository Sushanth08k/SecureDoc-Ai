from typing import Dict, Any, List, Set, Optional, Union, Tuple
import re
import logging
import json
from pathlib import Path
import os

# Try to import spaCy and Presidio with graceful fallback
try:
    import spacy
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    SPACY_AVAILABLE = True
    PRESIDIO_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    PRESIDIO_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class PIIDetectionService:
    """
    Service for Personally Identifiable Information (PII) detection
    
    This service identifies sensitive information in document text,
    such as:
    - Social Security Numbers
    - Credit Card Numbers
    - Phone Numbers
    - Email Addresses
    - Physical Addresses
    - Names
    - Dates of Birth
    - And other sensitive information
    """
    
    # Simple regex patterns for PII detection as fallback
    PII_PATTERNS = {
        "SSN": r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',
        "CREDIT_CARD": r'\b(?:\d{4}[-]?\d{4}[-]?\d{4}[-]?\d{4}|\d{4}[-]?\d{6}[-]?\d{5})\b',
        "PHONE_NUMBER": r'\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "EMAIL_ADDRESS": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        "DATE": r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b',
        "IP_ADDRESS": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        "US_DRIVER_LICENSE": r'\b[A-Z]\d{7}\b'
    }
    
    # Singleton instances
    _nlp = None
    _analyzer = None
    _anonymizer = None
    
    @classmethod
    def _initialize_presidio(cls):
        """Initialize Presidio analyzer with spaCy model"""
        if not PRESIDIO_AVAILABLE or not SPACY_AVAILABLE:
            logger.warning("Presidio or spaCy not available, falling back to regex patterns")
            return False
        
        try:
            # Check if we already have the spaCy model
            if not spacy.util.is_package("en_core_web_sm"):
                logger.info("Downloading spaCy model (en_core_web_sm)...")
                spacy.cli.download("en_core_web_sm")
            
            # Initialize NLP engine with spaCy
            provider = NlpEngineProvider(nlp_engine_name="spacy")
            nlp_engine = provider.create_engine()
            
            # Initialize analyzer with default recognizers
            registry = RecognizerRegistry()
            cls._analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                registry=registry
            )
            
            # Initialize anonymizer
            cls._anonymizer = AnonymizerEngine()
            
            logger.info("Presidio PII detection initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Presidio: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def detect_pii(text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text using Presidio Analyzer or fallback to regex
        
        Args:
            text: The text to analyze
            
        Returns:
            List of entities like: [{"entity": "NAME", "text": "John Doe", "start": 0, "end": 8}]
        """
        results = []
        
        # Try using Presidio first
        if PRESIDIO_AVAILABLE and SPACY_AVAILABLE:
            if PIIDetectionService._analyzer is None:
                success = PIIDetectionService._initialize_presidio()
                if not success:
                    logger.warning("Failed to initialize Presidio, falling back to regex")
            
            if PIIDetectionService._analyzer is not None:
                try:
                    # Analyze text with Presidio
                    analyzer_results = PIIDetectionService._analyzer.analyze(
                        text=text,
                        language="en"
                    )
                    
                    # Convert results to our format
                    for result in analyzer_results:
                        entity = {
                            "entity": result.entity_type,
                            "text": text[result.start:result.end],
                            "start": result.start,
                            "end": result.end,
                            "score": result.score
                        }
                        results.append(entity)
                    
                    logger.info(f"Presidio detected {len(results)} PII entities")
                    
                    # If Presidio found results, return them
                    if results:
                        return results
                        
                except Exception as e:
                    logger.error(f"Presidio analysis error: {str(e)}", exc_info=True)
                    # Continue to fallback regex if Presidio fails
        
        # Fallback to regex patterns
        logger.info("Using regex patterns for PII detection")
        
        for entity_type, pattern in PIIDetectionService.PII_PATTERNS.items():
            matches = re.finditer(pattern, text)
            
            for match in matches:
                entity = {
                    "entity": entity_type,
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "score": 1.0  # High confidence for regex matches
                }
                results.append(entity)
        
        logger.info(f"Regex detected {len(results)} PII entities")
        return results
    
    @staticmethod
    def _create_char_to_word_map(text: str, words: List[Dict[str, Any]]) -> Dict[int, int]:
        """
        Create a mapping from character positions to word indices
        
        Args:
            text: The full text
            words: List of words with bounding boxes
            
        Returns:
            Dictionary mapping character positions to word indices
        """
        char_to_word = {}
        
        # Simple implementation - assumes words are in order in the text
        char_pos = 0
        for i, word in enumerate(words):
            word_text = word.get('word', '')
            if not word_text:
                continue
                
            # Find this word in the text, starting from the current position
            word_pos = text.find(word_text, char_pos)
            if word_pos != -1:
                # Map each character position to this word index
                for j in range(word_pos, word_pos + len(word_text)):
                    char_to_word[j] = i
                
                # Update current position
                char_pos = word_pos + len(word_text)
        
        return char_to_word
    
    @staticmethod
    def _map_entity_to_words(entity: Dict[str, Any], 
                           char_to_word_map: Dict[int, int],
                           words: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Map a detected entity to its corresponding words and bounding boxes
        
        Args:
            entity: The detected entity
            char_to_word_map: Mapping from character positions to word indices
            words: List of words with bounding boxes
            
        Returns:
            Entity with added bounding box information
        """
        start_char = entity['start']
        end_char = entity['end']
        
        # Find the words that contain this entity
        word_indices = set()
        for char_pos in range(start_char, end_char):
            if char_pos in char_to_word_map:
                word_indices.add(char_to_word_map[char_pos])
        
        if not word_indices:
            # Could not map to words
            return entity
        
        # Get the bounding boxes for these words
        min_x = float('inf')
        min_y = float('inf')
        max_x = 0
        max_y = 0
        
        word_indices = sorted(word_indices)
        entity_words = []
        
        for idx in word_indices:
            if idx < len(words):
                word = words[idx]
                if 'bbox' in word and len(word['bbox']) == 4:
                    x, y, w, h = word['bbox']
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x + w)
                    max_y = max(max_y, y + h)
                    entity_words.append(word.get('word', ''))
        
        # Add bounding box to entity
        if min_x < float('inf'):
            entity['bbox'] = [min_x, min_y, max_x - min_x, max_y - min_y]
            entity['words'] = entity_words
        
        return entity
    
    @staticmethod
    def detect_pii_in_doc(ocr_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect PII across all pages of a document
        
        Args:
            ocr_results: List of OCR results, one per page
            
        Returns:
            List of page results with detected PII entities
        """
        if not ocr_results:
            return [{
                "page_num": 0,
                "status": "error",
                "message": "No OCR results provided"
            }]
        
        pii_results = []
        
        for page_num, page_ocr in enumerate(ocr_results):
            try:
                if page_ocr.get("status") != "success":
                    logger.warning(f"Skipping PII detection for page {page_num+1} due to OCR errors")
                    pii_results.append({
                        "page_num": page_num + 1,
                        "status": "error",
                        "message": f"OCR failed for this page: {page_ocr.get('message', 'Unknown error')}"
                    })
                    continue
                
                # Extract text from OCR result
                text = page_ocr.get("text", "")
                
                if not text.strip():
                    logger.warning(f"No text found in OCR results for page {page_num+1}")
                    pii_results.append({
                        "page_num": page_num + 1,
                        "status": "warning",
                        "message": "No text found in OCR results"
                    })
                    continue
                
                # Detect PII in text
                pii_entities = PIIDetectionService.detect_pii(text)
                
                # Map PII positions back to word bounding boxes if available
                words = page_ocr.get("words", [])
                mapped_entities = []
                
                if words:
                    # Create a mapping from character positions to words
                    char_to_word_map = PIIDetectionService._create_char_to_word_map(text, words)
                    
                    # Map each entity to its corresponding words and bounding boxes
                    for entity in pii_entities:
                        mapped_entity = PIIDetectionService._map_entity_to_words(
                            entity, char_to_word_map, words
                        )
                        if mapped_entity:
                            mapped_entities.append(mapped_entity)
                else:
                    # If no word bounding boxes, just use the entities as is
                    mapped_entities = pii_entities
                
                pii_results.append({
                    "page_num": page_num + 1,
                    "status": "success",
                    "entities": mapped_entities,
                    "entity_count": len(mapped_entities)
                })
                
            except Exception as e:
                logger.error(f"Error in PII detection for page {page_num+1}: {str(e)}", exc_info=True)
                pii_results.append({
                    "page_num": page_num + 1,
                    "status": "error",
                    "message": f"PII detection error: {str(e)}"
                })
        
        return pii_results
    
    @staticmethod
    def process_document(ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document's OCR results for PII detection
        
        Args:
            ocr_results: OCR results dictionary
            
        Returns:
            Dictionary with PII detection results
        """
        if ocr_results.get("status") != "success":
            return {
                "status": "error",
                "message": "Cannot process document due to OCR errors"
            }
        
        # Extract the list of page results
        page_results = ocr_results.get("results", [])
        
        # Detect PII across all pages
        pii_page_results = PIIDetectionService.detect_pii_in_doc(page_results)
        
        # Calculate sensitivity based on PII findings
        total_entities = sum(page.get("entity_count", 0) for page in pii_page_results 
                            if page.get("status") == "success")
        
        entity_types = set()
        for page in pii_page_results:
            if page.get("status") == "success":
                for entity in page.get("entities", []):
                    entity_types.add(entity.get("entity"))
        
        # Determine sensitivity level
        if total_entities == 0:
            sensitivity = "low"
        elif total_entities < 5:
            sensitivity = "medium"
        else:
            sensitivity = "high"
        
        return {
            "status": "success",
            "pages": len(pii_page_results),
            "results": pii_page_results,
            "sensitivity": sensitivity,
            "entity_count": total_entities,
            "entity_types": list(entity_types)
        }
