#!/usr/bin/env python3
"""
Shared Metadata Extraction Infrastructure for Bank Statement Extractors

This package provides reusable, enterprise-grade components for extracting metadata
from bank statement PDFs. Designed to eliminate code duplication and provide
consistent, high-quality extraction across all bank extractors.

Modules:
    - pdf_utils: PDF preprocessing and region-based extraction utilities
    - field_configs: Standard field configurations for Indian banks
    - metadata_extractor: Hybrid metadata extractor with 3-tier fallback

Usage:
    from extractors.shared import HybridMetadataExtractor, STANDARD_METADATA_FIELDS
    from extractors.shared.pdf_utils import preprocess_pdf_text

Author: Claude Code Assistant
Version: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Claude Code Assistant"

# Import main classes and functions for easy access
from .metadata_extractor import HybridMetadataExtractor
from .field_configs import (
    STANDARD_METADATA_FIELDS,
    STANDARD_REGIONS,
    get_bank_field_config,
    get_bank_regions
)
from .pdf_utils import (
    preprocess_pdf_text,
    extract_from_region
)

__all__ = [
    'HybridMetadataExtractor',
    'STANDARD_METADATA_FIELDS',
    'STANDARD_REGIONS',
    'get_bank_field_config',
    'get_bank_regions',
    'preprocess_pdf_text',
    'extract_from_region'
]