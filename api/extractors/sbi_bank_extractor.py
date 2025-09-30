#!/usr/bin/env python3
"""
SBI Bank PDF Statement Extractor - Optimized for SBI PDF Format
Designed specifically for State Bank of India's tabular format with multi-line transaction handling

This extractor handles SBI-specific patterns:
- Multi-line transaction descriptions
- DR/CR balance notation (e.g., "62761.09 CR")
- DD-MM-YY date format
- UPI transaction patterns
- Transaction table with columns: Txn Date, Value Date, Description, Ref/Cheque No., Debit, Credit, Balance

Author: Claude Code Assistant
Version: 1.0.0
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import InvalidOperation
from dateutil import parser as date_parser

# PDF processing library
try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required for SBI Bank PDF extraction. Install with: pip install pdfplumber")

from .base_extractor import BaseBankExtractor
from .shared import HybridMetadataExtractor, get_bank_field_config, get_bank_regions
from .shared.pdf_utils import preprocess_pdf_text

logger = logging.getLogger(__name__)


class SBIBankExtractor(BaseBankExtractor):
    """
    SBI Bank Statement Extractor - Optimized for SBI PDF Format

    Handles SBI-specific patterns:
    - Multi-line transaction descriptions that span multiple rows
    - DR/CR suffix notation for balances
    - DD-MM-YY date format (different from DD-MM-YYYY)
    - UPI transaction patterns with detailed descriptions
    - Account metadata extraction from header sections
    """

    # ============================================================================
    # CONFIGURATION (Uses Shared Enterprise Extraction System)
    # ============================================================================
    # Note: Field configurations and regions are now managed by the shared module
    # at api/extractors/shared/field_configs.py
    # This eliminates code duplication and provides consistent extraction across banks

    # Statement period pattern - case insensitive, flexible date format
    PERIOD_PATTERN = re.compile(r'(?i)from\s+(.+?)\s+to\s+(.+?)(?:\s|$)', re.IGNORECASE)

    # Balance patterns for DR/CR notation
    BALANCE_DR_CR_PATTERN = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(DR|CR)')
    OPENING_BALANCE_PATTERN = re.compile(r'Opening\s*Balance\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(DR|CR)?')
    CLOSING_BALANCE_PATTERN = re.compile(r'Closing\s*Balance\s*[:\-]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(DR|CR)?')

    # Transaction patterns
    DATE_PATTERN = re.compile(r'^(\d{2}-\d{2}-\d{2,4})')
    UPI_PATTERN = re.compile(r'UPI/(\w+)')

    def __init__(self):
        # Set attributes before calling super().__init__()
        self._bank_name = "State Bank of India"
        self._version = "1.0.0"
        self._capabilities = [
            "account_metadata",
            "balance_calculation",
            "financial_summary",
            "multi_page",
            "password_protected",
            "statement_period",
            "transactions",
            "transaction_types",
            "multi_line_transactions",
            "upi_transactions"
        ]
        super().__init__()
        self.transactions = []
        self.statement_metadata = {}

        # Initialize shared hybrid metadata extractor
        self.metadata_extractor = HybridMetadataExtractor('sbi')

        # Performance optimization: Cache for extracted data
        self._page_text_cache = {}
        self._tables_cache = {}

    def get_bank_name(self) -> str:
        return self._bank_name

    def get_version(self) -> str:
        return self._version

    def get_supported_capabilities(self) -> List[str]:
        return self._capabilities

    # ============================================================================
    # NOTE: Enterprise extraction methods have been moved to shared module
    # ============================================================================
    # The following methods are now available from the shared module:
    # - preprocess_pdf_text() -> from .shared.pdf_utils import preprocess_pdf_text
    # - extract_from_region() -> from .shared.pdf_utils import extract_from_region
    # - extract_field_hybrid() -> HybridMetadataExtractor.extract_field()
    #
    # This eliminates code duplication and provides consistent extraction
    # across all bank extractors. See api/extractors/shared/ for implementation.

    def extract_complete_statement(self, pdf_path: str, password: Optional[str] = None) -> Dict:
        """
        Extract complete statement data optimized for SBI Bank's format.

        IMPORTANT: Transactions are always extracted even if metadata extraction fails.
        Extraction errors are captured and returned for database storage.
        """
        extraction_errors = []

        try:
            # Open PDF with pdfplumber (handles password automatically)
            with pdfplumber.open(pdf_path, password=password) as pdf:
                logger.info("Processing SBI Bank statement with %d pages", len(pdf.pages))

                # Step 1: Extract metadata from header sections
                # CRITICAL: Wrap in try-except to ensure transactions are still extracted if metadata fails
                try:
                    self.statement_metadata, metadata_errors = self._extract_metadata_sbi(pdf)
                    if metadata_errors:
                        extraction_errors.extend(metadata_errors)
                        logger.warning("Metadata extraction had %d errors", len(metadata_errors))
                except Exception as e:
                    error_msg = f"Metadata extraction failed completely: {str(e)}"
                    logger.error(error_msg)
                    extraction_errors.append({
                        "stage": "metadata",
                        "error_type": "complete_failure",
                        "error_message": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    # Initialize with defaults so processing can continue
                    self.statement_metadata = {
                        "customer_name": "Not Found",
                        "account_number": "Not Found",
                        "account_type": "SAVINGS ACCOUNT",
                        "statement_period": {"from_date": "Not Found", "to_date": "Not Found"}
                    }

                # Step 2: Extract transactions with multi-line handling
                # CRITICAL: Always attempt transaction extraction regardless of metadata status
                try:
                    self.transactions = self._extract_transactions_sbi(pdf)
                    logger.info("Successfully extracted %d transactions", len(self.transactions))
                except Exception as e:
                    error_msg = f"Transaction extraction failed: {str(e)}"
                    logger.error(error_msg)
                    extraction_errors.append({
                        "stage": "transactions",
                        "error_type": "complete_failure",
                        "error_message": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.transactions = []

                # Step 3: Calculate financial summary with DR/CR handling
                try:
                    financial_summary = self._calculate_financial_summary_sbi()
                except Exception as e:
                    error_msg = f"Financial summary calculation failed: {str(e)}"
                    logger.error(error_msg)
                    extraction_errors.append({
                        "stage": "financial_summary",
                        "error_type": "calculation_failure",
                        "error_message": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    financial_summary = {
                        'opening_balance': 0.0,
                        'closing_balance': 0.0,
                        'total_credits': 0.0,
                        'total_debits': 0.0,
                        'net_change': 0.0,
                        'transaction_count': len(self.transactions),
                        'balance_verified': False
                    }

                # Step 4: Determine statement period from transactions if not found in metadata
                if (self.statement_metadata.get("statement_period", {}).get("from_date") == "Not Found" and
                    self.transactions):
                    first_date = self.transactions[0].get("Date", "")
                    last_date = self.transactions[-1].get("Date", "")
                    if first_date and last_date:
                        self.statement_metadata["statement_period"] = {
                            "from_date": first_date,
                            "to_date": last_date
                        }

                # Prepare final result with processed timestamp
                # Include all extracted metadata fields dynamically
                statement_meta = {
                    "bank_name": self._bank_name,
                    "customer_name": self.statement_metadata.get("customer_name", "Not Found"),
                    "account_number": self.statement_metadata.get("account_number", "Not Found"),
                    "account_type": self.statement_metadata.get("account_type", "SAVINGS ACCOUNT"),
                    "statement_period": self.statement_metadata.get("statement_period", {}),
                    "currency": "INR"
                }

                # Add optional metadata fields if they exist
                optional_fields = ['ifsc_code', 'micr_code', 'cif_number', 'branch_name',
                                 'customer_email', 'customer_phone', 'opening_balance']
                for field in optional_fields:
                    if field in self.statement_metadata:
                        statement_meta[field] = self.statement_metadata[field]

                result = {
                    "total_transactions": len(self.transactions),
                    "processed_at": datetime.now().isoformat(),
                    "statement_metadata": statement_meta,
                    "financial_summary": financial_summary,
                    "transactions": self.transactions,
                    "extractor_metadata": self.get_extraction_metadata(),
                    "extraction_errors": extraction_errors,  # NEW: For database storage
                    "extraction_status": "partial" if extraction_errors else "complete"  # NEW: Overall status
                }

                if extraction_errors:
                    logger.warning("SBI Bank extraction completed WITH ERRORS: %d transactions, %d errors",
                                 len(self.transactions), len(extraction_errors))
                else:
                    logger.info("SBI Bank extraction completed successfully: %d transactions, Balance verified: %s",
                              len(self.transactions), financial_summary.get("balance_verified", False))

                return result

        except Exception as e:
            # Critical failure - PDF couldn't be opened or processed at all
            error_msg = f"Critical failure extracting SBI Bank statement from {pdf_path}: {str(e)}"
            logger.error(error_msg)

            # Return partial result with error information for database storage
            return {
                "total_transactions": 0,
                "processed_at": datetime.now().isoformat(),
                "statement_metadata": {
                    "bank_name": self._bank_name,
                    "customer_name": "Not Found",
                    "account_number": "Not Found",
                    "account_type": "SAVINGS ACCOUNT",
                    "statement_period": {"from_date": "Not Found", "to_date": "Not Found"},
                    "currency": "INR"
                },
                "financial_summary": {
                    'opening_balance': 0.0,
                    'closing_balance': 0.0,
                    'total_credits': 0.0,
                    'total_debits': 0.0,
                    'net_change': 0.0,
                    'transaction_count': 0,
                    'balance_verified': False
                },
                "transactions": [],
                "extractor_metadata": self.get_extraction_metadata(),
                "extraction_errors": [{
                    "stage": "critical",
                    "error_type": "pdf_processing_failure",
                    "error_message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }],
                "extraction_status": "failed"
            }
        finally:
            # Clear caches to free memory
            self._clear_cache()

    def _extract_metadata_sbi(self, pdf) -> Tuple[Dict, List[Dict]]:
        """
        Extract metadata specific to SBI Bank format using hybrid extraction.

        Uses enterprise-grade field mapping configuration and hybrid extraction
        methods (key-value, position-based, region scan) with automatic fallback.

        Returns:
            Tuple of (metadata_dict, errors_list) where errors_list contains details
            about any fields that failed to extract
        """
        metadata = {
            "customer_name": "Not Found",
            "account_number": "Not Found",
            "account_type": "SAVINGS ACCOUNT",
            "statement_period": {"from_date": "Not Found", "to_date": "Not Found"}
        }
        errors = []

        try:
            # Get first page for metadata extraction
            if not pdf.pages:
                error_msg = "PDF has no pages"
                logger.error(error_msg)
                errors.append({
                    "field": "all",
                    "error_type": "no_pages",
                    "error_message": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
                return metadata, errors

            # ====================================================================
            # USE SHARED HYBRID METADATA EXTRACTOR FOR STANDARD FIELDS
            # ====================================================================
            # Extract all standard metadata fields (account number, IFSC, MICR, CIF, etc.)
            try:
                extracted_fields = self.metadata_extractor.extract_all_metadata(pdf)
            except Exception as e:
                error_msg = f"Shared metadata extractor failed: {str(e)}"
                logger.error(error_msg)
                errors.append({
                    "field": "shared_extractor",
                    "error_type": "extractor_failure",
                    "error_message": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
                extracted_fields = {}

            # Map extracted fields to metadata structure and track missing required fields
            required_fields = {
                'account_number': 'Account number is required for statement processing',
                'ifsc_code': 'IFSC code is required for bank identification'
            }

            if extracted_fields.get('account_number'):
                metadata["account_number"] = extracted_fields['account_number']
            elif 'account_number' in required_fields:
                errors.append({
                    "field": "account_number",
                    "error_type": "missing_required_field",
                    "error_message": required_fields['account_number'],
                    "timestamp": datetime.now().isoformat()
                })

            if extracted_fields.get('ifsc_code'):
                metadata["ifsc_code"] = extracted_fields['ifsc_code']
            elif 'ifsc_code' in required_fields:
                errors.append({
                    "field": "ifsc_code",
                    "error_type": "missing_required_field",
                    "error_message": required_fields['ifsc_code'],
                    "timestamp": datetime.now().isoformat()
                })

            # Optional fields - don't generate errors if missing
            if extracted_fields.get('micr_code'):
                metadata["micr_code"] = extracted_fields['micr_code']
            if extracted_fields.get('cif_number'):
                metadata["cif_number"] = extracted_fields['cif_number']
            if extracted_fields.get('branch'):
                metadata["branch_name"] = extracted_fields['branch'].strip()
            if extracted_fields.get('email'):
                metadata["customer_email"] = extracted_fields['email']
            if extracted_fields.get('phone'):
                metadata["customer_phone"] = extracted_fields['phone'].strip()

            # ====================================================================
            # SPECIAL HANDLING FOR FIELDS WITH CUSTOM LOGIC
            # ====================================================================

            # Extract text from first 2 pages for special fields
            first_page_text = self._safe_extract_page_text(pdf, 0)
            second_page_text = self._safe_extract_page_text(pdf, 1) if len(pdf.pages) > 1 else ""
            header_text = first_page_text + "\n" + second_page_text

            # Preprocess header text using shared utility
            header_text = preprocess_pdf_text(header_text)

            # Extract customer name - prioritize custom SBI logic, fallback to shared extractor
            # Custom logic handles SBI-specific format where name appears before "Customer Name:" label
            try:
                customer_name = self._extract_customer_name_sbi(first_page_text)
                if customer_name:
                    metadata["customer_name"] = customer_name
                elif extracted_fields.get('customer_name'):
                    # Fallback: Use shared extractor result (handles "Account Name" field)
                    metadata["customer_name"] = extracted_fields['customer_name'].strip()
                else:
                    # Customer name not found - log warning but don't fail
                    logger.warning("Customer name could not be extracted")
            except Exception as e:
                error_msg = f"Customer name extraction failed: {str(e)}"
                logger.warning(error_msg)
                errors.append({
                    "field": "customer_name",
                    "error_type": "extraction_failure",
                    "error_message": error_msg,
                    "timestamp": datetime.now().isoformat()
                })

            # Extract statement period - requires date normalization
            try:
                period_match = self.PERIOD_PATTERN.search(header_text)
                if period_match:
                    from_date_str = period_match.group(1).strip()
                    to_date_str = period_match.group(2).strip()

                    # Normalize dates to DD-MM-YYYY format
                    from_date = self._normalize_date_format(from_date_str)
                    to_date = self._normalize_date_format(to_date_str)

                    metadata["statement_period"] = {
                        "from_date": from_date,
                        "to_date": to_date
                    }
            except Exception as e:
                error_msg = f"Statement period extraction failed: {str(e)}"
                logger.warning(error_msg)
                errors.append({
                    "field": "statement_period",
                    "error_type": "extraction_failure",
                    "error_message": error_msg,
                    "timestamp": datetime.now().isoformat()
                })

            # Extract opening balance - requires DR/CR handling
            try:
                opening_match = self.OPENING_BALANCE_PATTERN.search(header_text)
                if opening_match:
                    amount = float(opening_match.group(1).replace(',', ''))
                    dr_cr = opening_match.group(2) if opening_match.group(2) else 'CR'
                    metadata["opening_balance"] = amount if dr_cr == 'CR' else -amount
            except Exception as e:
                error_msg = f"Opening balance extraction failed: {str(e)}"
                logger.warning(error_msg)
                errors.append({
                    "field": "opening_balance",
                    "error_type": "extraction_failure",
                    "error_message": error_msg,
                    "timestamp": datetime.now().isoformat()
                })

            logger.info("Extracted SBI Bank metadata for account: %s (with %d errors)",
                       metadata.get('account_number', 'Unknown'), len(errors))

        except Exception as e:
            error_msg = f"Unexpected error in metadata extraction: {str(e)}"
            logger.error(error_msg)
            errors.append({
                "field": "metadata_extraction",
                "error_type": "unexpected_error",
                "error_message": error_msg,
                "timestamp": datetime.now().isoformat()
            })

        return metadata, errors

    def _extract_customer_name_sbi(self, page_text: str) -> Optional[str]:
        """Extract customer name from SBI format - typically after 'STATEMENT OF ACCOUNT'"""
        try:
            lines = page_text.split('\n')

            # Look for customer name after "STATEMENT OF ACCOUNT"
            for i, line in enumerate(lines):
                line = line.strip()
                if 'STATEMENT OF ACCOUNT' in line and i + 1 < len(lines):
                    # Next line should be the customer name
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.endswith(':'):
                        # Remove "Mr.", "Mrs.", etc. prefixes and clean up
                        customer_name = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s*', '', next_line)
                        return customer_name.strip()

                # Alternative pattern: look for lines that look like names (no colons, proper length)
                if (line and len(line) > 10 and len(line) < 50 and
                    not line.endswith(':') and
                    not any(keyword in line.lower() for keyword in
                        ['state bank', 'account', 'statement', 'branch', 'page', 'from', 'to', 'date', 'balance']) and
                    re.match(r'^[A-Z\s\.]+$', line)):
                    # Remove prefixes
                    customer_name = re.sub(r'^(Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s*', '', line)
                    return customer_name.strip()

        except Exception as e:
            logger.debug("Error extracting customer name: %s", e)
        return None

    def _normalize_date_format(self, date_str: str) -> str:
        """
        Convert any valid date to standard DD-MM-YYYY format.
        Handles: DD-MM-YY, DD-MM-YYYY, DD Mon YYYY, DD/MM/YY, DD/MM/YYYY
        """
        try:
            if not date_str or not date_str.strip():
                return date_str

            # Clean whitespace and newlines
            cleaned = ' '.join(date_str.split())

            # Parse date using dateutil
            parsed_date = date_parser.parse(cleaned, dayfirst=True)

            # Return in DD-MM-YYYY format
            return parsed_date.strftime('%d-%m-%Y')
        except (ValueError, date_parser.ParserError, OverflowError):
            # If parsing fails, return original string
            return date_str

    def _extract_transactions_sbi(self, pdf) -> List[Dict]:
        """Extract transactions optimized for SBI Bank's multi-line format"""
        transactions = []

        try:
            logger.info("Starting SBI Bank transaction extraction with multi-line handling")

            # Method 1: Try table-based extraction first
            transactions = self._extract_with_table_parsing_sbi(pdf)
            if transactions:
                logger.info("Table parsing extracted %d transactions", len(transactions))
                return transactions

            # Method 2: Fallback to text-based parsing with multi-line handling
            logger.info("Falling back to text parsing with multi-line support")
            transactions = self._extract_with_text_parsing_sbi(pdf)

        except Exception as e:
            logger.error("Error in SBI transaction extraction: %s", e)

        return transactions

    def _extract_with_table_parsing_sbi(self, pdf) -> List[Dict]:
        """Extract using table parsing optimized for SBI format"""
        transactions = []
        sno_counter = 1

        try:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Extract tables from this page
                    tables = self._safe_extract_tables(page, page_num)

                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        # Look for transaction table (should have date columns)
                        header = table[0] if table else []
                        if not any('date' in str(col).lower() for col in header):
                            continue

                        # Process transaction rows with multi-line handling
                        transactions_from_table = self._process_transaction_table_sbi(table, page_num, sno_counter)
                        transactions.extend(transactions_from_table)
                        sno_counter += len(transactions_from_table)

                except Exception as page_error:
                    logger.warning("Error processing page %d: %s", page_num, page_error)
                    continue

        except Exception as e:
            logger.error("Table parsing error: %s", e)
            return []

        return transactions

    def _process_transaction_table_sbi(self, table: List[List], page_num: int, start_sno: int) -> List[Dict]:
        """Process SBI transaction table with multi-line handling"""
        transactions = []
        current_transaction = None
        sno_counter = start_sno

        try:
            for row_idx, row in enumerate(table[1:], 1):  # Skip header
                if not row or len(row) < 3:
                    continue

                row_text = [str(cell).strip() if cell else "" for cell in row]

                # Check if this row starts a new transaction (has a date)
                date_cell = row_text[0]
                if self._is_valid_sbi_date(date_cell):
                    # Save previous transaction if exists
                    if current_transaction and self._validate_transaction_data_sbi(current_transaction):
                        transactions.append(current_transaction)

                    # Start new transaction
                    current_transaction = self._create_transaction_from_sbi_row(row_text, sno_counter, page_num)
                    sno_counter += 1

                elif current_transaction:
                    # This is a continuation row - append to description
                    continuation_text = " ".join(row_text).strip()
                    if continuation_text:
                        current_transaction["Remarks"] += " " + continuation_text

            # Don't forget the last transaction
            if current_transaction and self._validate_transaction_data_sbi(current_transaction):
                transactions.append(current_transaction)

        except Exception as e:
            logger.error("Error processing SBI transaction table: %s", e)

        return transactions

    def _create_transaction_from_sbi_row(self, row: List[str], sno: int, page_num: int) -> Dict:
        """Create transaction from SBI table row"""
        try:
            # SBI format: Txn Date | Value Date | Description | Ref/Cheque No. | Debit | Credit | Balance
            transaction = {
                "S.No": str(sno),
                "Date": self._normalize_date_format(row[0]) if len(row) > 0 else "",
                "Value_Date": self._normalize_date_format(row[1]) if len(row) > 1 else "",
                "Remarks": row[2] if len(row) > 2 else "",
                "Transaction_ID": row[3] if len(row) > 3 else "",
                "Debit": self._clean_amount(row[4]) if len(row) > 4 else "",
                "Credit": self._clean_amount(row[5]) if len(row) > 5 else "",
                "Balance": self._parse_balance_with_dr_cr(row[6]) if len(row) > 6 else "",
                "Page_Number": page_num
            }

            # Determine transaction type
            if transaction["Credit"]:
                transaction["Transaction_Type"] = "Credit"
            else:
                transaction["Transaction_Type"] = "Debit"

            return transaction

        except Exception as e:
            logger.warning("Error creating transaction from SBI row: %s", e)
            return {}

    def _extract_with_text_parsing_sbi(self, pdf) -> List[Dict]:
        """Fallback text parsing for SBI format with multi-line support"""
        transactions = []
        sno_counter = 1

        try:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = self._safe_extract_page_text(pdf, page_num - 1)
                lines = page_text.split('\n')

                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        i += 1
                        continue

                    # Check if line starts with a date
                    if self._is_valid_sbi_date(line.split()[0] if line.split() else ""):
                        # Parse this transaction with multi-line support
                        transaction, lines_consumed = self._parse_multiline_transaction_sbi(
                            lines[i:], sno_counter, page_num
                        )
                        if transaction:
                            transactions.append(transaction)
                            sno_counter += 1
                        i += max(1, lines_consumed)
                    else:
                        i += 1

        except Exception as e:
            logger.error("Error in SBI text parsing: %s", e)

        return transactions

    def _parse_multiline_transaction_sbi(self, lines: List[str], sno: int, page_num: int) -> Tuple[Optional[Dict], int]:
        """Parse a potentially multi-line SBI transaction"""
        try:
            if not lines:
                return None, 0

            first_line = lines[0].strip()
            parts = re.split(r'\s{2,}', first_line)  # Split on multiple spaces

            if len(parts) < 3:
                return None, 1

            # Extract date
            date = self._normalize_date_format(parts[0])

            # Initialize transaction data
            transaction = {
                "S.No": str(sno),
                "Date": date,
                "Value_Date": "",
                "Remarks": "",
                "Transaction_ID": "",
                "Debit": "",
                "Credit": "",
                "Balance": "",
                "Transaction_Type": "",
                "Page_Number": page_num
            }

            # Parse first line components
            description_parts = []
            amounts = []

            for part in parts[1:]:
                part = part.strip()
                if self._is_amount(part):
                    amounts.append(part)
                else:
                    description_parts.append(part)

            # Look for continuation lines
            lines_consumed = 1
            for i in range(1, min(len(lines), 5)):  # Check up to 4 more lines
                next_line = lines[i].strip()
                if not next_line:
                    break

                # If next line starts with date, stop
                if self._is_valid_sbi_date(next_line.split()[0] if next_line.split() else ""):
                    break

                # If line contains amounts, it might be part of current transaction
                line_parts = re.split(r'\s{2,}', next_line)
                has_amounts = any(self._is_amount(part) for part in line_parts)

                if has_amounts:
                    # Add amounts and continue description
                    for part in line_parts:
                        part = part.strip()
                        if self._is_amount(part):
                            amounts.append(part)
                        else:
                            description_parts.append(part)
                    lines_consumed += 1
                else:
                    # Pure description line
                    description_parts.append(next_line)
                    lines_consumed += 1

            # Assign parsed data
            transaction["Remarks"] = " ".join(description_parts)

            # Process amounts - last is usually balance, second-to-last is transaction amount
            if len(amounts) >= 2:
                balance_str = amounts[-1]
                transaction["Balance"] = self._parse_balance_with_dr_cr(balance_str)

                # Transaction amount
                trans_amount = self._clean_amount(amounts[-2])
                if self._is_credit_transaction_sbi(transaction["Remarks"]):
                    transaction["Credit"] = trans_amount
                    transaction["Transaction_Type"] = "Credit"
                else:
                    transaction["Debit"] = trans_amount
                    transaction["Transaction_Type"] = "Debit"
            elif len(amounts) == 1:
                transaction["Balance"] = self._parse_balance_with_dr_cr(amounts[0])

            return transaction, lines_consumed

        except Exception as e:
            logger.warning("Error parsing multi-line SBI transaction: %s", e)
            return None, 1

    def _is_valid_sbi_date(self, date_str: str) -> bool:
        """
        Check if string is a valid SBI date using advanced date parsing.
        Supports: DD-MM-YY, DD-MM-YYYY, DD Mon YYYY, DD/MM/YY, DD/MM/YYYY
        """
        if not date_str or not date_str.strip():
            return False

        try:
            # Clean whitespace and newlines (e.g., "31 Mar\n2025" -> "31 Mar 2025")
            cleaned = ' '.join(date_str.split())

            # Parse date - handles multiple formats automatically
            # dayfirst=True ensures DD-MM-YYYY interpretation
            parsed_date = date_parser.parse(cleaned, dayfirst=True)

            # Validate reasonable date range for bank statements (1970-2100)
            if 1970 <= parsed_date.year <= 2100:
                return True
            return False
        except (ValueError, date_parser.ParserError, OverflowError):
            return False

    def _is_amount(self, text: str) -> bool:
        """Check if text represents a monetary amount"""
        try:
            text = text.strip()
            # Check for amount pattern with optional DR/CR
            if re.match(r'^\d{1,3}(,\d{3})*(\.\d{2})?\s*(DR|CR)?$', text):
                return True
            return False
        except Exception:
            return False

    def _clean_amount(self, amount_str: str) -> str:
        """Clean amount string for consistent formatting"""
        try:
            if not amount_str or amount_str.strip() == "":
                return ""

            # Remove commas and extract numeric part
            clean = re.sub(r'[^\d.]', '', amount_str)
            if clean and clean.replace('.', '').isdigit():
                return clean
            return ""
        except Exception:
            return ""

    def _parse_balance_with_dr_cr(self, balance_str: str) -> str:
        """Parse balance with DR/CR notation"""
        try:
            if not balance_str:
                return ""

            # Look for DR/CR pattern
            match = self.BALANCE_DR_CR_PATTERN.search(balance_str)
            if match:
                amount = match.group(1).replace(',', '')
                dr_cr = match.group(2)

                # Convert to signed amount
                amount_float = float(amount)
                if dr_cr == 'DR':
                    return "-%s" % amount
                else:
                    return amount

            # Fallback - just clean the amount
            return self._clean_amount(balance_str)

        except Exception as e:
            logger.debug("Error parsing balance '%s': %s", balance_str, e)
            return ""

    def _is_credit_transaction_sbi(self, description: str) -> bool:
        """Determine if SBI transaction is credit based on description"""
        description_upper = description.upper()

        # SBI-specific credit patterns
        credit_patterns = [
            'UPI-CR', 'NEFT CR', 'RTGS CR', 'IMPS CR', 'CREDIT',
            'SALARY', 'INTEREST', 'DIVIDEND', 'REFUND', 'DEPOSIT',
            'TRANSFER CREDIT', 'CASH DEPOSIT', 'CHEQUE DEPOSIT'
        ]

        # SBI-specific debit patterns
        debit_patterns = [
            'UPI-DR', 'NEFT DR', 'ATM', 'POS', 'DEBIT', 'WITHDRAWAL',
            'PURCHASE', 'PAYMENT', 'CHARGES', 'FEE', 'TRANSFER DEBIT',
            'CASH WITHDRAWAL', 'CHEQUE'
        ]

        # Check for credit patterns
        if any(pattern in description_upper for pattern in credit_patterns):
            return True

        # Check for debit patterns
        if any(pattern in description_upper for pattern in debit_patterns):
            return False

        # Default assumption for unclear cases
        return False

    def _calculate_financial_summary_sbi(self) -> Dict:
        """Calculate financial summary with SBI-specific DR/CR handling"""
        summary = {
            'opening_balance': 0.0,
            'closing_balance': 0.0,
            'total_credits': 0.0,
            'total_debits': 0.0,
            'net_change': 0.0,
            'transaction_count': len(self.transactions),
            'balance_verified': False
        }

        try:
            # Calculate transaction totals
            for transaction in self.transactions:
                try:
                    credit = transaction.get('Credit', '')
                    debit = transaction.get('Debit', '')

                    if credit:
                        credit_amount = float(credit.replace(',', ''))
                        summary['total_credits'] += credit_amount

                    if debit:
                        debit_amount = float(debit.replace(',', ''))
                        summary['total_debits'] += debit_amount

                except (ValueError, AttributeError) as e:
                    logger.debug("Error processing transaction amounts: %s", e)

            # Calculate net change
            summary['net_change'] = summary['total_credits'] - summary['total_debits']

            # Extract opening balance from metadata
            opening_balance = self.statement_metadata.get('opening_balance', 0.0)
            summary['opening_balance'] = opening_balance

            # Calculate expected closing balance
            expected_closing = opening_balance + summary['net_change']

            # Get actual closing balance from last transaction or metadata
            if self.transactions:
                last_balance = self.transactions[-1].get('Balance', '')
                if last_balance:
                    try:
                        # Handle negative balances (DR notation)
                        if last_balance.startswith('-'):
                            actual_closing = float(last_balance.replace(',', ''))
                        else:
                            actual_closing = float(last_balance.replace(',', ''))
                        summary['closing_balance'] = actual_closing

                        # Verify balance calculation
                        difference = abs(expected_closing - actual_closing)
                        if difference < 1.0:  # Within 1 rupee tolerance
                            summary['balance_verified'] = True

                    except (ValueError, AttributeError):
                        logger.warning("Could not parse closing balance from transactions")
                        summary['closing_balance'] = expected_closing
            else:
                summary['closing_balance'] = expected_closing

        except Exception as e:
            logger.error("Error calculating SBI financial summary: %s", e)

        return summary

    def _validate_transaction_data_sbi(self, transaction: Dict) -> bool:
        """Validate SBI transaction data"""
        try:
            # Check required fields
            required_fields = ['Date', 'Remarks']
            for field in required_fields:
                if not transaction.get(field):
                    return False

            # Validate date format
            date_str = transaction['Date']
            if not self._is_valid_sbi_date(date_str.split()[0] if date_str.split() else ""):
                return False

            # Check that transaction has some meaningful content
            if not transaction.get('Remarks', '').strip():
                return False

            return True

        except Exception as e:
            logger.debug("Transaction validation error: %s", e)
            return False

    def _safe_extract_page_text(self, pdf, page_index: int) -> str:
        """Safely extract text from PDF page with caching"""
        try:
            if page_index in self._page_text_cache:
                return self._page_text_cache[page_index]

            if 0 <= page_index < len(pdf.pages):
                text = pdf.pages[page_index].extract_text()
                extracted_text = text if text else ""
                self._page_text_cache[page_index] = extracted_text
                return extracted_text
            else:
                return ""
        except Exception as e:
            logger.error("Error extracting text from page %d: %s", page_index, e)
            return ""

    def _safe_extract_tables(self, page, page_num: int) -> List:
        """Safely extract tables from PDF page with caching"""
        try:
            cache_key = page_num
            if cache_key in self._tables_cache:
                return self._tables_cache[cache_key]

            tables = page.extract_tables()
            extracted_tables = tables if tables else []
            self._tables_cache[cache_key] = extracted_tables
            return extracted_tables
        except Exception as e:
            logger.debug("Error extracting tables from page %s: %s", page_num, e)
            return []

    def _clear_cache(self):
        """Clear extraction caches to free memory"""
        self._page_text_cache.clear()
        self._tables_cache.clear()
        logger.debug("Cleared SBI extraction caches")

    def get_extraction_metadata(self) -> Dict:
        """Get metadata about the SBI extraction process"""
        return {
            'extractor_name': self.__class__.__name__,
            'bank_name': self.bank_name,
            'version': self.version,
            'extraction_method': 'table_and_text_parsing_with_multiline_support',
            'capabilities': self.get_supported_capabilities(),
            'total_pages_processed': len(set(tx.get('Page_Number', 1) for tx in self.transactions)) if self.transactions else 1,
            'extraction_timestamp': datetime.now().isoformat(),
            'optimization_notes': 'Optimized for SBI multi-line transactions and DR/CR balance notation'
        }


def extract_sbi_bank_statement(pdf_path: str, password: Optional[str] = None) -> Dict:
    """
    Convenience function to extract SBI Bank statement data
    """
    extractor = SBIBankExtractor()
    return extractor.extract_complete_statement(pdf_path, password)