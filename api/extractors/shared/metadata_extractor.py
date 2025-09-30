#!/usr/bin/env python3
"""
Hybrid Metadata Extractor with 3-Tier Fallback Mechanism

Provides enterprise-grade metadata extraction with automatic fallback:
1. Key-value parsing (fastest, most reliable)
2. Position-based word extraction (fallback)
3. Region scan (last resort)

Designed for high reliability across varying PDF formats.

Author: Claude Code Assistant
Version: 1.0.0
"""

import re
import logging
from typing import Dict, Optional

from .pdf_utils import preprocess_pdf_text, extract_from_region

logger = logging.getLogger(__name__)


class HybridMetadataExtractor:
    """
    Enterprise-grade metadata extractor with hybrid extraction strategy.

    Implements 3-tier extraction with automatic fallback to maximize
    reliability across different PDF formats.

    Example:
        >>> from extractors.shared import HybridMetadataExtractor, get_bank_field_config
        >>> extractor = HybridMetadataExtractor('sbi')
        >>> with pdfplumber.open(pdf_path) as pdf:
        >>>     metadata = extractor.extract_all_metadata(pdf)
    """

    def __init__(self, bank_id: str, field_config: Optional[Dict] = None, regions: Optional[Dict] = None):
        """
        Initialize the hybrid metadata extractor.

        Args:
            bank_id: Bank identifier ('sbi', 'axis', etc.)
            field_config: Optional custom field configuration (uses standard if not provided)
            regions: Optional custom region configuration (uses standard if not provided)
        """
        self.bank_id = bank_id.lower()

        # Import here to avoid circular dependencies
        from .field_configs import get_bank_field_config, get_bank_regions

        self.field_config = field_config or get_bank_field_config(self.bank_id)
        self.regions = regions or get_bank_regions(self.bank_id)

        logger.info(f"Initialized HybridMetadataExtractor for {self.bank_id} with {len(self.field_config)} fields")

    def extract_field(self, page, field_name: str) -> Optional[str]:
        """
        Extract single field using hybrid approach with automatic fallback.

        Implements 3-tier extraction strategy:
        1. Key-value parsing from preprocessed text (fastest, most reliable)
        2. Position-based word extraction using PDF coordinates
        3. Region scan fallback for long digit sequences

        Args:
            page: pdfplumber page object
            field_name: Name of field to extract

        Returns:
            Extracted field value or None if not found

        Example:
            >>> account = extractor.extract_field(page, 'account_number')
        """
        if field_name not in self.field_config:
            logger.warning(f"Field '{field_name}' not found in configuration")
            return None

        field_config = self.field_config[field_name]

        # ========================================================================
        # Method 1: Key-Value Parsing (Primary - fastest and most reliable)
        # ========================================================================
        try:
            # Extract from metadata region for performance
            text = extract_from_region(page, self.regions['metadata'])

            # Preprocess to remove PDF encoding artifacts
            cleaned_text = preprocess_pdf_text(text)

            # Try each label variation
            for label in field_config['labels']:
                # Build pattern: "Label : pattern"
                search_pattern = f"{label}\\s*:\\s*{field_config['pattern']}"
                match = re.search(search_pattern, cleaned_text, re.IGNORECASE)

                if match:
                    logger.debug(f"Extracted {field_name} using key-value method: {match.group(1)}")
                    return match.group(1).strip()

        except Exception as e:
            logger.debug(f"Key-value extraction failed for {field_name}: {e}")

        # ========================================================================
        # Method 2: Position-Based Word Extraction (Fallback 1)
        # ========================================================================
        try:
            words = page.extract_words()

            # Look for label words in sequence
            for i, word in enumerate(words):
                # Check if current and next word match any label
                for label in field_config['labels']:
                    label_parts = label.split()

                    # Check if words match label
                    if i + len(label_parts) <= len(words):
                        matches = all(
                            words[i + j]['text'].lower() == label_parts[j].lower()
                            for j in range(len(label_parts))
                        )

                        if matches:
                            # Found label, now look for value in next few words
                            for j in range(i + len(label_parts), min(i + len(label_parts) + 5, len(words))):
                                word_text = words[j]['text']

                                # Skip colon or other separators
                                if word_text in [':', '-', '=']:
                                    continue

                                # Try to match the pattern
                                pattern_match = re.match(field_config['pattern'], word_text)
                                if pattern_match:
                                    logger.debug(f"Extracted {field_name} using position-based method: {pattern_match.group(1)}")
                                    return pattern_match.group(1).strip()

        except Exception as e:
            logger.debug(f"Position-based extraction failed for {field_name}: {e}")

        # ========================================================================
        # Method 3: Region Scan Fallback (Last Resort)
        # ========================================================================
        try:
            # For certain field types, scan the region for matching patterns
            if field_name in ['account_number', 'ifsc_code', 'micr_code', 'cif_number']:
                text = extract_from_region(page, self.regions['metadata'])
                cleaned_text = preprocess_pdf_text(text)

                # Find all matches for the pattern
                matches = re.findall(field_config['pattern'], cleaned_text)

                if matches:
                    # For account numbers, prefer longer matches
                    if field_name == 'account_number':
                        result = max(matches, key=len)
                    else:
                        result = matches[0]

                    logger.debug(f"Extracted {field_name} using region scan fallback: {result}")
                    return result.strip()

        except Exception as e:
            logger.debug(f"Region scan failed for {field_name}: {e}")

        # All methods failed
        if field_config.get('required', False):
            logger.warning(f"Required field {field_name} could not be extracted")

        return None

    def extract_all_metadata(self, pdf) -> Dict:
        """
        Extract all configured metadata fields from PDF.

        Args:
            pdf: pdfplumber PDF object

        Returns:
            Dictionary with extracted metadata fields

        Example:
            >>> metadata = extractor.extract_all_metadata(pdf)
            >>> account = metadata.get('account_number')
        """
        metadata = {}

        if not pdf.pages:
            logger.error("PDF has no pages")
            return metadata

        first_page = pdf.pages[0]

        # Extract each configured field
        for field_name, field_config in self.field_config.items():
            value = self.extract_field(first_page, field_name)
            if value:
                metadata[field_name] = value

        logger.info(f"Extracted {len(metadata)}/{len(self.field_config)} metadata fields")
        return metadata

    def validate_extracted_metadata(self, metadata: Dict) -> Dict:
        """
        Validate extracted metadata fields.

        Args:
            metadata: Dictionary of extracted metadata

        Returns:
            Dictionary with validation results
                {
                    'valid': bool,
                    'missing_required': list,
                    'field_status': dict
                }
        """
        validation = {
            'valid': True,
            'missing_required': [],
            'field_status': {}
        }

        for field_name, field_config in self.field_config.items():
            is_required = field_config.get('required', False)
            is_present = field_name in metadata and metadata[field_name]

            validation['field_status'][field_name] = {
                'present': is_present,
                'required': is_required
            }

            if is_required and not is_present:
                validation['valid'] = False
                validation['missing_required'].append(field_name)

        return validation