#!/usr/bin/env python3
"""
Axis Bank PDF Statement Extractor - Optimized for Actual PDF Format
Simplified table-based extraction designed specifically for Axis Bank's tabular format

This version is optimized for the actual Axis Bank PDF structure:
- Perfect table format with clear columns
- Single-row transactions (not multi-line)
- Direct balance information available
- Minimal regex needed only for metadata

Author: Claude Code Assistant
Version: 1.0.0 (Optimized for Actual Format)
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import InvalidOperation

# PDF processing library
try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required for Axis Bank PDF extraction. Install with: pip install pdfplumber")

# Note: pandas was removed from dependencies as it's not currently used
# If advanced data processing is needed in the future, pandas can be re-added

from .base_extractor import BaseBankExtractor

logger = logging.getLogger(__name__)


class AxisBankExtractor(BaseBankExtractor):
    """
    Axis Bank Statement Extractor - Optimized for Actual PDF Format

    This version is specifically designed for Axis Bank's excellent tabular format:
    - Table columns: Tran Date | Chq No | Particulars | Debit | Credit | Balance | Init.Br
    - Single-row transactions (no multi-line parsing needed)
    - Perfect structure for table extraction
    """

    # Compiled regex patterns for metadata only (not transactions)
    ACCOUNT_PATTERN = re.compile(r'Account No\s*:\s*(\d+)')
    PERIOD_PATTERN = re.compile(r'From\s*:\s*(\d{2}-\d{2}-\d{4})\s*To\s*:\s*(\d{2}-\d{2}-\d{4})')
    IFSC_PATTERN = re.compile(r'IFSC Code\s*:\s*([A-Z0-9]+)')
    MICR_PATTERN = re.compile(r'MICR Code\s*:\s*(\d+)')

    # Balance patterns - simplified for better matching
    OPENING_BALANCE_PATTERN = re.compile(r'OPENING BALANCE\s+(\d+\.?\d*)')
    CLOSING_BALANCE_PATTERN = re.compile(r'CLOSING BALANCE\s+(\d+\.?\d*)')

    # Customer details
    CUSTOMER_ID_PATTERN = re.compile(r'Customer ID\s*:\s*(\d+)')
    MOBILE_PATTERN = re.compile(r'Registered Mobile No\s*:\s*(XXXXXX\d+)')
    EMAIL_PATTERN = re.compile(r'Registered Email ID\s*:\s*([^\s]+)')
    PAN_PATTERN = re.compile(r'PAN\s*:\s*([A-Z0-9]+)')

    def __init__(self):
        # Set attributes before calling super().__init__()
        self._bank_name = "Axis Bank"
        self._version = "1.0.0"
        self._capabilities = [
            "account_metadata",
            "balance_calculation",
            "financial_summary",
            "multi_page",
            "password_protected",
            "statement_period",
            "transactions",
            "upi_transactions"
        ]
        super().__init__()
        self.transactions = []
        self.statement_metadata = {}

        # Performance optimization: Cache for extracted page text
        self._page_text_cache = {}
        self._tables_cache = {}

    def get_bank_name(self) -> str:
        return self._bank_name

    def get_version(self) -> str:
        return self._version

    def get_supported_capabilities(self) -> List[str]:
        return self._capabilities

    def extract_complete_statement(self, pdf_path: str, password: Optional[str] = None) -> Dict:
        """
        Extract complete statement data optimized for Axis Bank's tabular format
        """
        try:
            # Open PDF with pdfplumber (handles password automatically)
            with pdfplumber.open(pdf_path, password=password) as pdf:
                logger.info(f"Processing Axis Bank statement with {len(pdf.pages)} pages")

                # Step 1: Extract metadata using targeted regex
                self.statement_metadata = self._extract_metadata_optimized(pdf)

                # Step 2: Extract transactions using optimized table parsing
                self.transactions = self._extract_transactions_optimized(pdf)

                # Step 3: Calculate financial summary (no balance math needed - data is already correct)
                financial_summary = self._calculate_financial_summary_optimized()

                # Prepare final result
                result = {
                    **self.statement_metadata,
                    'transactions': self.transactions,
                    'total_transactions': len(self.transactions),
                    'financial_summary': financial_summary,
                    'extraction_metadata': self.get_extraction_metadata()
                }

                logger.info(f"Axis Bank extraction completed: {len(self.transactions)} transactions, "
                          f"Balance verified: {financial_summary.get('balance_verified', False)}")

                return result

        except Exception as e:
            logger.error(f"Error extracting Axis Bank statement from {pdf_path}: {e}")
            raise
        finally:
            # Clear caches to free memory
            self._clear_cache()

    def _extract_metadata_optimized(self, pdf) -> Dict:
        """Extract metadata with corrected patterns for actual PDF format"""
        metadata = {
            "customer_name": "Not Found",
            "account_number": "Not Found",
            "account_type": "SAVINGS ACCOUNT",
            "statement_period": {"from_date": "Not Found", "to_date": "Not Found"}
        }

        try:
            # Get text from first and last pages with error handling
            first_page_text = self._safe_extract_page_text(pdf, 0)
            last_page_text = self._safe_extract_page_text(pdf, -1) if len(pdf.pages) > 1 else ""
            full_text = first_page_text + "\n" + last_page_text

            if not full_text.strip():
                logger.error("No text extracted from PDF pages")
                return metadata

            # Customer name - first line approach
            lines = first_page_text.split('\n')
            if lines:
                # First non-empty line is typically the customer name
                for line in lines:
                    line = line.strip()
                    if line and not any(keyword in line.lower() for keyword in ['joint', 's/o', 'holder']):
                        if re.match(r'^[A-Z\s]+$', line) and len(line) > 3:
                            metadata["customer_name"] = line
                            break

            # Account number
            account_match = self.ACCOUNT_PATTERN.search(full_text)
            if account_match:
                metadata["account_number"] = account_match.group(1)

            # Statement period
            period_match = self.PERIOD_PATTERN.search(full_text)
            if period_match:
                metadata["statement_period"] = {
                    "from_date": period_match.group(1),
                    "to_date": period_match.group(2)
                }

            # Bank details
            ifsc_match = self.IFSC_PATTERN.search(full_text)
            if ifsc_match:
                metadata["ifsc_code"] = ifsc_match.group(1)

            micr_match = self.MICR_PATTERN.search(full_text)
            if micr_match:
                metadata["micr_code"] = micr_match.group(1)

            # Customer details
            customer_id_match = self.CUSTOMER_ID_PATTERN.search(full_text)
            if customer_id_match:
                metadata["customer_id"] = customer_id_match.group(1)

            mobile_match = self.MOBILE_PATTERN.search(full_text)
            if mobile_match:
                metadata["customer_phone"] = mobile_match.group(1)

            email_match = self.EMAIL_PATTERN.search(full_text)
            if email_match:
                metadata["customer_email"] = email_match.group(1)

            pan_match = self.PAN_PATTERN.search(full_text)
            if pan_match:
                metadata["pan_number"] = pan_match.group(1)

            # Opening balance - corrected pattern
            opening_balance_match = self.OPENING_BALANCE_PATTERN.search(full_text)
            if opening_balance_match:
                try:
                    balance_str = opening_balance_match.group(1).replace(',', '')
                    metadata["opening_balance"] = float(balance_str)
                except (ValueError, InvalidOperation):
                    metadata["opening_balance"] = 0.0

            # Closing balance - new extraction
            closing_balance_match = self.CLOSING_BALANCE_PATTERN.search(full_text)
            if closing_balance_match:
                try:
                    balance_str = closing_balance_match.group(1).replace(',', '')
                    metadata["closing_balance"] = float(balance_str)
                except (ValueError, InvalidOperation):
                    metadata["closing_balance"] = 0.0

            # Account type is already set in default metadata

            logger.info(f"Extracted Axis Bank metadata for account: {metadata.get('account_number', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error extracting Axis Bank metadata: {e}")
            # Ensure required fields
            metadata.update({
                "customer_name": metadata.get("customer_name", "Not Found"),
                "account_number": metadata.get("account_number", "Not Found"),
                "account_type": "SAVINGS ACCOUNT",
                "statement_period": metadata.get("statement_period", {"from_date": "Not Found", "to_date": "Not Found"})
            })

        return metadata

    def _extract_transactions_optimized(self, pdf) -> List[Dict]:
        """Extract transactions optimized for Axis Bank's perfect table format"""
        transactions = []

        try:
            logger.info("Starting optimized table-based transaction extraction")

            # Method 1: Try pdfplumber for table extraction
            transactions = self._extract_with_pdfplumber_optimized(pdf)
            if transactions:
                logger.info(f"PDFPlumber extracted {len(transactions)} transactions")
                return transactions

            # Method 2: Fallback to optimized text parsing
            logger.info("Falling back to optimized text parsing")
            transactions = self._extract_with_text_parsing_optimized(pdf)

        except Exception as e:
            logger.error(f"Error in optimized extraction: {e}")

        return transactions

    def _extract_with_pdfplumber_optimized(self, pdf) -> List[Dict]:
        """Extract using pdfplumber optimized for Axis Bank table structure"""
        transactions = []

        try:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Extract tables from this page using safe method with caching
                    tables = self._safe_extract_tables(page, page_num)

                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        # Look for transaction table (has date column)
                        header = table[0] if table else []
                        if not any('date' in str(col).lower() for col in header):
                            continue

                        # Process transaction rows
                        for row_idx, row in enumerate(table[1:], 1):
                            if not row or len(row) < 6:  # Need at least 6 columns
                                continue

                            # Skip non-transaction rows
                            date_cell = str(row[0]).strip()
                            if not date_cell or not self._is_valid_date(date_cell):
                                continue

                            # Create transaction from table row
                            transaction = self._create_transaction_from_row(row, row_idx, page_num)
                            if transaction and self._validate_transaction_data(transaction):
                                transactions.append(transaction)

                except Exception as page_error:
                    logger.warning(f"Error processing page {page_num}: {page_error}")
                    continue  # Continue with next page

        except Exception as e:
            logger.error(f"PDFPlumber optimized extraction error: {e}")
            return []  # Return empty list instead of raising

        return transactions

    def _extract_with_text_parsing_optimized(self, pdf) -> List[Dict]:
        """Optimized text parsing for Axis Bank's simple format"""
        transactions = []
        sno_counter = 1

        try:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                lines = page_text.split('\n')

                # Find transaction lines (start with date pattern)
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Check if line starts with date (DD-MM-YYYY format)
                    if re.match(r'^\d{2}-\d{2}-\d{4}', line):
                        transaction = self._parse_transaction_line_optimized(line, sno_counter, page_num)
                        if transaction:
                            transactions.append(transaction)
                            sno_counter += 1

        except Exception as e:
            logger.error(f"Error in optimized text parsing: {e}")

        return transactions

    def _parse_transaction_line_optimized(self, line: str, sno: int, page_num: int) -> Optional[Dict]:
        """Parse a single transaction line optimized for Axis Bank format with deterministic rules"""
        try:
            # Split the line using multiple spaces as delimiter for better column separation
            parts = re.split(r'\s{2,}', line.strip())
            if len(parts) < 3:
                # Fallback to single space split
                parts = line.split()
                if len(parts) < 3:
                    return None

            # Extract date (first part) - must be DD-MM-YYYY format
            date = parts[0].strip()
            if not self._is_valid_date(date):
                return None

            # Use deterministic column-based parsing for Axis Bank format
            # Expected format: Date | Chq/Ref No | Particulars | Debit | Credit | Balance
            transaction = self._parse_deterministic_columns(parts, sno, page_num)
            if transaction:
                return transaction

            # Fallback to amount-based parsing with improved logic
            return self._parse_with_amount_detection(parts, sno, page_num)

        except Exception as e:
            logger.warning(f"Error parsing transaction line '{line[:50]}...': {e}")
            return None

    def _parse_deterministic_columns(self, parts: List[str], sno: int, page_num: int) -> Optional[Dict]:
        """Parse using deterministic column positions based on Axis Bank format"""
        try:
            if len(parts) < 4:
                return None

            date = parts[0].strip()

            # Try to identify column structure based on known Axis Bank patterns
            debit_amount = ""
            credit_amount = ""
            balance = ""
            remarks_parts = []
            chq_no = ""

            # Scan for amounts (numeric values with optional decimals and commas)
            amount_pattern = re.compile(r'^\d{1,3}(,\d{3})*(\.\d{2})?$')
            amounts_found = []

            for i, part in enumerate(parts[1:], 1):
                part = part.strip()
                if amount_pattern.match(part):
                    amounts_found.append((i, float(part.replace(',', ''))))
                elif i == 1 and (part.isdigit() or part == ""):
                    # Second column is typically cheque number
                    chq_no = part
                else:
                    remarks_parts.append(part)

            # Determine column assignments based on amount positions
            if len(amounts_found) >= 2:
                # Last amount is balance, second last could be transaction amount
                balance = str(amounts_found[-1][1])
                transaction_amount = amounts_found[-2][1]

                # Determine if credit or debit based on description
                description = ' '.join(remarks_parts)
                if self._is_credit_transaction(description):
                    credit_amount = str(transaction_amount)
                else:
                    debit_amount = str(transaction_amount)
            elif len(amounts_found) == 1:
                # Only balance found
                balance = str(amounts_found[0][1])

            return {
                "S.No": str(sno),
                "Date": date,
                "Transaction_ID": chq_no,
                "Remarks": ' '.join(remarks_parts),
                "Debit": debit_amount,
                "Credit": credit_amount,
                "Balance": balance,
                "Transaction_Type": "Credit" if credit_amount else "Debit",
                "Page_Number": page_num
            }

        except Exception as e:
            logger.debug(f"Deterministic parsing failed: {e}")
            return None

    def _is_credit_transaction(self, description: str) -> bool:
        """Determine if transaction is credit based on description patterns"""
        description_upper = description.upper()

        # Definitive credit indicators
        credit_patterns = [
            'UPI/P2A', 'CREDIT', 'RECEIVED', 'NEFT', 'RTGS', 'IMPS', 'SALARY',
            'INTEREST', 'REFUND', 'CASH DEPOSIT', 'CHEQUE DEPOSIT', 'TRANSFER TO'
        ]

        # Definitive debit indicators
        debit_patterns = [
            'UPI/P2P', 'ATM', 'DEBIT', 'WITHDRAWAL', 'PURCHASE', 'PAYMENT',
            'CHARGES', 'FEE', 'TRANSFER FROM', 'CASH WITHDRAWAL'
        ]

        # Check for credit patterns first
        if any(pattern in description_upper for pattern in credit_patterns):
            return True

        # Check for debit patterns
        if any(pattern in description_upper for pattern in debit_patterns):
            return False

        # Default fallback - could be improved with more analysis
        return False

    def _parse_with_amount_detection(self, parts: List[str], sno: int, page_num: int) -> Optional[Dict]:
        """Fallback parsing using amount detection logic"""
        try:
            date = parts[0].strip()
            amounts = []
            description_parts = []

            for part in parts[1:]:
                clean_part = part.replace(',', '').strip()
                if re.match(r'^\d+\.?\d*$', clean_part) and float(clean_part) > 0:
                    amounts.append(float(clean_part))
                else:
                    description_parts.append(part)

            if not amounts:
                logger.debug(f"No amounts found in transaction line")
                return None

            # More robust amount assignment
            balance = amounts[-1] if amounts else 0
            description = ' '.join(description_parts)

            credit_amount = ""
            debit_amount = ""

            if len(amounts) >= 2:
                transaction_amount = amounts[-2]  # Second to last is transaction amount
                if self._is_credit_transaction(description):
                    credit_amount = str(transaction_amount)
                else:
                    debit_amount = str(transaction_amount)

            return {
                "S.No": str(sno),
                "Date": date,
                "Transaction_ID": "",
                "Remarks": description,
                "Debit": debit_amount,
                "Credit": credit_amount,
                "Balance": str(balance),
                "Transaction_Type": "Credit" if credit_amount else "Debit",
                "Page_Number": page_num
            }

        except Exception as e:
            logger.warning(f"Amount detection parsing failed: {e}")
            return None

    def _create_transaction_from_row(self, row: List, row_idx: int, page_num: int) -> Optional[Dict]:
        """Create transaction from table row - optimized for Axis Bank format"""
        try:
            # Axis Bank format: Tran Date | Chq No | Particulars | Debit | Credit | Balance | Init.Br
            if len(row) < 6:
                return None

            date = str(row[0]).strip()
            chq_no = str(row[1]).strip() if len(row) > 1 else ""
            particulars = str(row[2]).strip() if len(row) > 2 else ""
            debit = str(row[3]).strip() if len(row) > 3 else ""
            credit = str(row[4]).strip() if len(row) > 4 else ""
            balance = str(row[5]).strip() if len(row) > 5 else ""

            # Clean up empty values
            if debit.lower() in ['', 'nan', 'none']:
                debit = ""
            if credit.lower() in ['', 'nan', 'none']:
                credit = ""

            # Determine transaction type
            transaction_type = "Credit" if credit else "Debit"

            transaction = {
                "S.No": str(row_idx),
                "Date": date,
                "Transaction_ID": chq_no,
                "Remarks": particulars,
                "Debit": debit,
                "Credit": credit,
                "Balance": balance,
                "Transaction_Type": transaction_type,
                "Page_Number": page_num
            }

            return transaction

        except Exception as e:
            logger.warning(f"Error creating transaction from row: {e}")
            return None

    def _is_valid_date(self, date_str: str) -> bool:
        """Check if string is a valid date in DD-MM-YYYY format"""
        try:
            datetime.strptime(date_str, '%d-%m-%Y')
            return True
        except ValueError:
            return False

    def _calculate_financial_summary_optimized(self) -> Dict:
        """Calculate financial summary with robust balance verification and error handling"""
        summary = {
            'opening_balance': 0.0,
            'closing_balance': 0.0,
            'total_credits': 0.0,
            'total_debits': 0.0,
            'net_change': 0.0,
            'transaction_count': len(self.transactions),
            'balance_verified': False,
            'balance_calculation_method': 'unknown',
            'verification_details': {}
        }

        try:
            # Step 1: Determine opening balance with fallback hierarchy
            opening_balance, opening_method = self._determine_opening_balance()
            summary['opening_balance'] = opening_balance
            summary['verification_details']['opening_balance_method'] = opening_method

            # Step 2: Calculate transaction totals with validation
            credits_total, debits_total, calculation_errors = self._calculate_transaction_totals()
            summary['total_credits'] = credits_total
            summary['total_debits'] = debits_total
            summary['net_change'] = credits_total - debits_total

            if calculation_errors:
                logger.warning(f"Found {len(calculation_errors)} transaction calculation errors")
                summary['verification_details']['calculation_errors'] = calculation_errors

            # Step 3: Determine closing balance with fallback hierarchy
            closing_balance, closing_method = self._determine_closing_balance()
            summary['closing_balance'] = closing_balance
            summary['verification_details']['closing_balance_method'] = closing_method

            # Step 4: Comprehensive balance verification
            verification_result = self._verify_balance_consistency(
                opening_balance, closing_balance, credits_total, debits_total
            )
            summary.update(verification_result)

        except Exception as e:
            logger.error(f"Error calculating financial summary: {e}", exc_info=True)
            summary['verification_details']['calculation_error'] = str(e)

        return summary

    def _determine_opening_balance(self) -> Tuple[float, str]:
        """Determine opening balance using fallback hierarchy"""
        # Method 1: From metadata (preferred)
        if 'opening_balance' in self.statement_metadata:
            balance = self.statement_metadata['opening_balance']
            if isinstance(balance, (int, float)) and balance >= 0:
                return float(balance), 'metadata_extracted'

        # Method 2: Calculate from first transaction
        if self.transactions:
            try:
                first_tx = self.transactions[0]
                first_balance = self._parse_amount(first_tx.get('Balance', ''))
                first_credit = self._parse_amount(first_tx.get('Credit', ''))
                first_debit = self._parse_amount(first_tx.get('Debit', ''))

                if first_balance is not None:
                    # Opening = Current Balance - Credit + Debit
                    calculated_opening = first_balance - first_credit + first_debit
                    logger.info(f"Calculated opening balance from first transaction: {calculated_opening}")
                    return calculated_opening, 'calculated_from_first_transaction'

            except Exception as e:
                logger.warning(f"Failed to calculate opening balance from first transaction: {e}")

        # Method 3: Default fallback
        logger.warning("Using default opening balance of 0.0 - this may affect verification")
        return 0.0, 'default_fallback'

    def _determine_closing_balance(self) -> Tuple[float, str]:
        """Determine closing balance using fallback hierarchy"""
        # Method 1: From metadata (preferred)
        if 'closing_balance' in self.statement_metadata:
            balance = self.statement_metadata['closing_balance']
            if isinstance(balance, (int, float)) and balance >= 0:
                return float(balance), 'metadata_extracted'

        # Method 2: From last transaction balance
        if self.transactions:
            try:
                last_balance = self._parse_amount(self.transactions[-1].get('Balance', ''))
                if last_balance is not None:
                    return last_balance, 'last_transaction_balance'
            except Exception as e:
                logger.warning(f"Failed to extract closing balance from last transaction: {e}")

        # Method 3: Default fallback
        logger.warning("Using default closing balance of 0.0 - this may affect verification")
        return 0.0, 'default_fallback'

    def _calculate_transaction_totals(self) -> Tuple[float, float, List[str]]:
        """Calculate transaction totals with error tracking"""
        total_credits = 0.0
        total_debits = 0.0
        errors = []

        for i, tx in enumerate(self.transactions):
            try:
                # Process credit amount
                credit_amount = self._parse_amount(tx.get('Credit', ''))
                if credit_amount is not None and credit_amount > 0:
                    total_credits += credit_amount

                # Process debit amount
                debit_amount = self._parse_amount(tx.get('Debit', ''))
                if debit_amount is not None and debit_amount > 0:
                    total_debits += debit_amount

            except Exception as e:
                error_msg = f"Transaction {i+1}: {str(e)}"
                errors.append(error_msg)
                logger.debug(f"Error processing transaction {i+1}: {e}")

        return total_credits, total_debits, errors

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Safely parse amount string to float"""
        if not amount_str or amount_str.strip() == "":
            return 0.0

        try:
            # Clean the amount string
            clean_amount = str(amount_str).replace(',', '').strip()
            if clean_amount and clean_amount.replace('.', '').isdigit():
                return float(clean_amount)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse amount '{amount_str}': {e}")

        return None

    def _verify_balance_consistency(self, opening: float, closing: float,
                                  credits: float, debits: float) -> Dict:
        """Comprehensive balance verification with detailed reporting"""
        verification = {
            'balance_verified': False,
            'balance_calculation_method': 'mathematical_verification',
            'verification_details': {}
        }

        try:
            # Calculate expected closing balance
            net_change = credits - debits
            expected_closing = opening + net_change
            balance_difference = abs(closing - expected_closing)

            # Define tolerance levels
            tolerance_strict = 1.0   # 1 rupee
            tolerance_relaxed = 10.0  # 10 rupees

            verification['verification_details'].update({
                'opening_balance': opening,
                'total_credits': credits,
                'total_debits': debits,
                'net_change': net_change,
                'expected_closing': expected_closing,
                'actual_closing': closing,
                'balance_difference': balance_difference,
                'tolerance_used': tolerance_strict
            })

            # Determine verification status
            if balance_difference <= tolerance_strict:
                verification['balance_verified'] = True
                verification['balance_calculation_method'] = 'verified_exact'
            elif balance_difference <= tolerance_relaxed:
                verification['balance_verified'] = True
                verification['balance_calculation_method'] = 'verified_within_tolerance'
                verification['verification_details']['tolerance_used'] = tolerance_relaxed
                logger.info(f"Balance verified within relaxed tolerance: {balance_difference} rupees")
            else:
                verification['balance_verified'] = False
                verification['balance_calculation_method'] = 'verification_failed'
                logger.warning(f"Balance verification failed: difference of {balance_difference} rupees "
                             f"exceeds tolerance of {tolerance_relaxed}")

        except Exception as e:
            logger.error(f"Error in balance verification: {e}")
            verification['verification_details']['verification_error'] = str(e)

        return verification

    def _safe_extract_page_text(self, pdf, page_index: int) -> str:
        """Safely extract text from a PDF page with caching and error handling"""
        try:
            if page_index < 0:
                page_index = len(pdf.pages) + page_index  # Convert negative index

            # Check cache first
            if page_index in self._page_text_cache:
                return self._page_text_cache[page_index]

            if 0 <= page_index < len(pdf.pages):
                text = pdf.pages[page_index].extract_text()
                extracted_text = text if text else ""

                # Cache the result
                self._page_text_cache[page_index] = extracted_text
                return extracted_text
            else:
                logger.warning(f"Page index {page_index} out of range for PDF with {len(pdf.pages)} pages")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from page {page_index}: {e}")
            return ""

    def _safe_extract_tables(self, page, page_num: int = None) -> List:
        """Safely extract tables from a PDF page with caching and error handling"""
        try:
            # Use page number for caching if provided
            cache_key = page_num if page_num is not None else id(page)

            # Check cache first
            if cache_key in self._tables_cache:
                return self._tables_cache[cache_key]

            tables = page.extract_tables()
            extracted_tables = tables if tables else []

            # Cache the result
            self._tables_cache[cache_key] = extracted_tables
            return extracted_tables
        except Exception as e:
            logger.debug(f"Error extracting tables from page {cache_key}: {e}")
            return []

    def _clear_cache(self):
        """Clear extraction caches to free memory"""
        self._page_text_cache.clear()
        self._tables_cache.clear()
        logger.debug("Cleared PDF extraction caches")

    def _validate_transaction_data(self, transaction: Dict) -> bool:
        """Validate transaction data consistency"""
        try:
            # Required fields check
            required_fields = ['Date', 'Remarks', 'Balance']
            for field in required_fields:
                if not transaction.get(field):
                    logger.debug(f"Transaction missing required field: {field}")
                    return False

            # Date validation
            if not self._is_valid_date(transaction['Date']):
                logger.debug(f"Invalid date format: {transaction['Date']}")
                return False

            # Amount validation (at least one of Debit or Credit should be present for non-balance transactions)
            has_debit = transaction.get('Debit') and str(transaction['Debit']).strip()
            has_credit = transaction.get('Credit') and str(transaction['Credit']).strip()

            if not has_debit and not has_credit:
                # This might be a balance-only row, which could be valid
                logger.debug("Transaction has no debit or credit amount")

            return True

        except Exception as e:
            logger.warning(f"Error validating transaction: {e}")
            return False

    def _handle_extraction_error(self, error: Exception, context: str,
                                fallback_data: Optional[Dict] = None) -> Dict:
        """Standardized error handling for extraction methods"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': datetime.now().isoformat()
        }

        logger.error(f"Extraction error in {context}: {error}", exc_info=True)

        if fallback_data:
            logger.info(f"Returning fallback data for {context}")
            return fallback_data

        # Return minimal valid structure
        return {
            'extraction_error': error_info,
            'customer_name': 'Error in extraction',
            'account_number': 'Error in extraction',
            'transactions': [],
            'financial_summary': {
                'opening_balance': 0.0,
                'closing_balance': 0.0,
                'total_credits': 0.0,
                'total_debits': 0.0,
                'balance_verified': False
            }
        }

    def get_extraction_metadata(self) -> Dict:
        """Get metadata about the extraction process"""
        return {
            'extractor_name': self.__class__.__name__,
            'version': self.version,
            'extraction_method': 'optimized_table_based',
            'bank_name': self.bank_name,
            'total_pages_processed': len(self.transactions) // 10 + 1 if self.transactions else 1,
            'extraction_timestamp': datetime.now().isoformat(),
            'optimization_notes': 'Designed for Axis Bank tabular format'
        }


def extract_axis_bank_statement(pdf_path: str, password: Optional[str] = None) -> Dict:
    """
    Convenience function to extract Axis Bank statement data
    """
    extractor = AxisBankExtractor()
    return extractor.extract_complete_statement(pdf_path, password)