#!/usr/bin/env python3
"""
PDF Processing Utilities for Bank Statement Extraction

Provides common utilities for processing bank statement PDFs including:
- Text preprocessing (removing PDF encoding artifacts)
- Region-based text extraction
- Performance optimization helpers

These utilities are designed to work across all Indian bank statement formats.

Author: Claude Code Assistant
Version: 1.0.0
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def preprocess_pdf_text(text: str) -> str:
    """
    Remove PDF encoding artifacts for cleaner extraction.

    PDF files often contain font encoding artifacts like (cid:9) for tab characters.
    This preprocessing step removes these artifacts, making subsequent pattern
    matching simpler and more reliable.

    Args:
        text: Raw text extracted from PDF

    Returns:
        Cleaned text with encoding artifacts removed

    Example:
        >>> text = "Account Number :(cid:9)00000020133563509"
        >>> cleaned = preprocess_pdf_text(text)
        >>> print(cleaned)
        "Account Number : 00000020133563509"
    """
    if not text:
        return ""

    # Remove (cid:X) patterns where X is any digits
    cleaned = re.sub(r'\(cid:\d+\)', ' ', text)

    logger.debug(f"Preprocessed {len(text)} characters, removed CID encodings")
    return cleaned


def extract_from_region(page, region_config: dict) -> str:
    """
    Extract text from specific page region for optimized performance.

    By extracting only the relevant region (e.g., top 40% for metadata),
    we reduce processing time and avoid false matches in other areas.

    Args:
        page: pdfplumber page object
        region_config: Region configuration dict with keys:
            - y_start: Starting Y position as fraction of page height (0.0 to 1.0)
            - y_end: Ending Y position as fraction of page height (0.0 to 1.0)
            - description: Optional description of the region

    Returns:
        Text extracted from the specified region

    Raises:
        ValueError: If region_config is invalid or missing required keys
        AttributeError: If page object doesn't support required operations

    Example:
        >>> region = {'y_start': 0.0, 'y_end': 0.4}
        >>> metadata_text = extract_from_region(page, region)
    """
    if not region_config:
        raise ValueError("region_config cannot be None or empty")

    if 'y_start' not in region_config or 'y_end' not in region_config:
        raise ValueError("region_config must contain 'y_start' and 'y_end' keys")

    if not (0 <= region_config['y_start'] <= 1 and 0 <= region_config['y_end'] <= 1):
        raise ValueError("y_start and y_end must be between 0.0 and 1.0")

    if region_config['y_start'] >= region_config['y_end']:
        raise ValueError("y_start must be less than y_end")

    try:
        # Calculate bounding box coordinates
        bbox = (
            0,  # x0: left edge
            region_config['y_start'] * page.height,  # y0: top
            page.width,  # x1: right edge
            region_config['y_end'] * page.height  # y1: bottom
        )

        # Extract text from bounding box
        region = page.within_bbox(bbox)
        text = region.extract_text() or ""

        logger.debug(
            f"Extracted {len(text)} characters from region "
            f"({region_config['y_start']:.1%} to {region_config['y_end']:.1%})"
        )

        return text

    except AttributeError as e:
        logger.error(f"Invalid page object or missing required attributes: {e}")
        raise
    except Exception as e:
        logger.error(f"Error extracting from region: {e}")
        raise


def extract_from_bbox(page, x0: float, y0: float, x1: float, y1: float) -> str:
    """
    Extract text from specific bounding box coordinates.

    Args:
        page: pdfplumber page object
        x0: Left edge X coordinate
        y0: Top edge Y coordinate
        x1: Right edge X coordinate
        y1: Bottom edge Y coordinate

    Returns:
        Text extracted from the specified bounding box

    Example:
        >>> text = extract_from_bbox(page, 0, 0, 300, 200)
    """
    try:
        region = page.within_bbox((x0, y0, x1, y1))
        return region.extract_text() or ""
    except Exception as e:
        logger.error(f"Error extracting from bbox ({x0},{y0},{x1},{y1}): {e}")
        return ""


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text (collapse multiple spaces, trim, etc).

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace

    Example:
        >>> normalize_whitespace("Account    Number  :  12345")
        "Account Number : 12345"
    """
    if not text:
        return ""

    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)

    # Trim leading/trailing whitespace
    text = text.strip()

    return text


def clean_text(text: str, remove_newlines: bool = False) -> str:
    """
    Clean text by removing common PDF artifacts and normalizing.

    Combines preprocessing and whitespace normalization for convenience.

    Args:
        text: Text to clean
        remove_newlines: If True, replace newlines with spaces

    Returns:
        Cleaned text

    Example:
        >>> clean_text("Account:(cid:9)12345\\n\\nBalance")
        "Account: 12345 Balance"
    """
    if not text:
        return ""

    # Preprocess PDF artifacts
    text = preprocess_pdf_text(text)

    # Optionally remove newlines
    if remove_newlines:
        text = text.replace('\n', ' ')

    # Normalize whitespace
    text = normalize_whitespace(text)

    return text