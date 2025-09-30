#!/usr/bin/env python3
"""
Standard Field Configurations for Indian Bank Statement Extraction

Provides standardized field definitions for common metadata fields found in
Indian bank statements. Supports bank-specific overrides while maintaining
consistency across extractors.

Author: Claude Code Assistant
Version: 1.0.0
"""

from typing import Dict, List, Optional


# Standard metadata fields common to all Indian bank statements
STANDARD_METADATA_FIELDS = {
    'account_number': {
        'labels': ['Account Number', 'Account No', 'A/c Number', 'Acct Number'],
        'pattern': r'(\d{10,})',  # 10+ digits for account numbers
        'required': True,
        'description': 'Bank account number'
    },
    'ifsc_code': {
        'labels': ['IFSC', 'IFS Code', 'IFSC Code'],
        'pattern': r'([A-Z]{4}0[A-Z0-9]{6})',  # Standard IFSC format
        'required': True,
        'description': 'Indian Financial System Code'
    },
    'micr_code': {
        'labels': ['MICR', 'MICR Code'],
        'pattern': r'(\d{9})',  # 9-digit MICR code
        'required': False,
        'description': 'Magnetic Ink Character Recognition code'
    },
    'cif_number': {
        'labels': ['CIF', 'CIF No', 'CIF Number'],
        'pattern': r'(\d+)',  # Variable length CIF
        'required': False,
        'description': 'Customer Information File number'
    },
    'customer_name': {
        'labels': ['Account Name', 'Customer Name'],
        'pattern': r'((?:Mr\.|Mrs\.|Ms\.|Dr\.)?\s*[A-Z][A-Z\s\.]+?)(?:\s*$|\s*\n)',  # Name with optional title, stop at newline
        'required': False,
        'description': 'Customer or account holder name'
    },
    'branch': {
        'labels': ['Branch', 'Branch Name'],
        'pattern': r'([A-Z\s\(\)]+)',  # Branch names in uppercase
        'required': False,
        'description': 'Branch name'
    },
    'address': {
        'labels': ['Address'],
        'pattern': r'([^\n]+)',  # Address until newline
        'required': False,
        'description': 'Customer address'
    },
    'email': {
        'labels': ['Email', 'E-mail'],
        'pattern': r'([^\s]+@[^\s]+)',  # Email format
        'required': False,
        'description': 'Email address'
    },
    'phone': {
        'labels': ['Mobile', 'Phone', 'Contact'],
        'pattern': r'([\d\-\+\s]+)',  # Phone with formatting
        'required': False,
        'description': 'Phone/mobile number'
    }
}


# Standard page region definitions
# Metadata typically in top 40%, transactions in bottom 60%
STANDARD_REGIONS = {
    'metadata': {
        'y_start': 0.0,
        'y_end': 0.4,
        'description': 'Header/metadata region (top 40% of page)'
    },
    'transactions': {
        'y_start': 0.4,
        'y_end': 1.0,
        'description': 'Transaction table region (bottom 60% of page)'
    },
    'header': {
        'y_start': 0.0,
        'y_end': 0.15,
        'description': 'Top header region (top 15% of page)'
    },
    'footer': {
        'y_start': 0.90,
        'y_end': 1.0,
        'description': 'Bottom footer region (bottom 10% of page)'
    }
}


# Bank-specific field configuration overrides
# Note: Currently no banks require overrides from standard config.
# All Indian banks use standard patterns for account numbers (10+ digits),
# IFSC codes, and other fields defined in STANDARD_METADATA_FIELDS.
#
# This dictionary is kept for future extensibility if a bank requires
# truly different patterns or additional custom fields.
#
# Example of when to add an override:
#   'future_bank': {
#       'fields': {
#           'account_number': {
#               'pattern': r'custom_pattern_different_from_standard',
#           }
#       },
#       'regions': {
#           'metadata': {'y_start': 0.0, 'y_end': 0.5}  # Different layout
#       }
#   }
BANK_SPECIFIC_CONFIGS = {}


def get_bank_field_config(bank_id: str) -> Dict:
    """
    Get field configuration for a specific bank.

    Returns standard fields with optional bank-specific overrides if defined.
    Currently all Indian banks use the same standard patterns.

    Args:
        bank_id: Bank identifier ('sbi', 'axis', 'union', etc.)

    Returns:
        Complete field configuration for the bank

    Example:
        >>> config = get_bank_field_config('sbi')
        >>> account_field = config['account_number']
        >>> # Returns standard config since no SBI-specific overrides exist
    """
    bank_id = bank_id.lower()

    # Start with standard fields (works for all Indian banks)
    config = STANDARD_METADATA_FIELDS.copy()

    # Apply bank-specific overrides if they exist (currently empty)
    if bank_id in BANK_SPECIFIC_CONFIGS:
        bank_config = BANK_SPECIFIC_CONFIGS[bank_id]

        if 'fields' in bank_config:
            for field_name, field_config in bank_config['fields'].items():
                if field_name in config:
                    # Merge with existing field config
                    config[field_name].update(field_config)
                else:
                    # Add new field
                    config[field_name] = field_config

    return config


def get_bank_regions(bank_id: str) -> Dict:
    """
    Get region configuration for a specific bank.

    Returns standard regions with optional bank-specific overrides if defined.
    Currently all Indian banks use the same standard page layout.

    Args:
        bank_id: Bank identifier ('sbi', 'axis', 'union', etc.)

    Returns:
        Region configuration for the bank

    Example:
        >>> regions = get_bank_regions('sbi')
        >>> metadata_region = regions['metadata']
        >>> # Returns standard regions since no SBI-specific overrides exist
    """
    bank_id = bank_id.lower()

    # Check for bank-specific regions (currently none defined)
    if bank_id in BANK_SPECIFIC_CONFIGS:
        bank_config = BANK_SPECIFIC_CONFIGS[bank_id]
        if 'regions' in bank_config:
            return bank_config['regions']

    # Return standard regions (works for all Indian banks)
    return STANDARD_REGIONS


def get_field_labels(field_name: str, bank_id: Optional[str] = None) -> List[str]:
    """
    Get label variations for a specific field.

    Args:
        field_name: Name of the field ('account_number', 'ifsc_code', etc.)
        bank_id: Optional bank identifier for bank-specific labels

    Returns:
        List of label variations for the field

    Example:
        >>> labels = get_field_labels('account_number', 'sbi')
        >>> # Returns: ['Account Number', 'Account No']
    """
    if bank_id:
        config = get_bank_field_config(bank_id)
    else:
        config = STANDARD_METADATA_FIELDS

    if field_name in config and 'labels' in config[field_name]:
        return config[field_name]['labels']

    return []


def is_required_field(field_name: str, bank_id: Optional[str] = None) -> bool:
    """
    Check if a field is required for extraction.

    Args:
        field_name: Name of the field
        bank_id: Optional bank identifier

    Returns:
        True if field is required, False otherwise
    """
    if bank_id:
        config = get_bank_field_config(bank_id)
    else:
        config = STANDARD_METADATA_FIELDS

    if field_name in config:
        return config[field_name].get('required', False)

    return False