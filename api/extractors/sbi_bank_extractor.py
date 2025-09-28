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

# PDF processing library
try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required for SBI Bank PDF extraction. Install with: pip install pdfplumber")

from .base_extractor import BaseBankExtractor

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

    # Compiled regex patterns for metadata extraction
    ACCOUNT_PATTERN = re.compile(r'Account\s*Number\s*[:\-]?\s*(\d+)')
    CUSTOMER_PATTERN = re.compile(r'^([A-Z\s]+)$', re.MULTILINE)
    IFSC_PATTERN = re.compile(r'IFSC\s*[:\-]?\s*([A-Z0-9]+)')
    MICR_PATTERN = re.compile(r'MICR\s*[:\-]?\s*(\d+)')
    CIF_PATTERN = re.compile(r'CIF\s*No\.?\s*[:\-]?\s*(\d+)')
    BRANCH_PATTERN = re.compile(r'Branch\s*[:\-]?\s*([A-Z\s\(\)]+)')
    ADDRESS_PATTERN = re.compile(r'Address\s*[:\-]?\s*([^\n]+)')
    EMAIL_PATTERN = re.compile(r'Email\s*[:\-]?\s*([^\s]+@[^\s]+)')
    PHONE_PATTERN = re.compile(r'Mobile\s*[:\-]?\s*([\d\-\+\s]+)')

    # Statement period pattern for DD-MM-YY format
    PERIOD_PATTERN = re.compile(r'From\s*[:\-]?\s*(\d{2}-\d{2}-\d{2,4})\s*To\s*[:\-]?\s*(\d{2}-\d{2}-\d{2,4})')

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

        # Performance optimization: Cache for extracted data
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
        Extract complete statement data optimized for SBI Bank's format
        """
        try:
            # Open PDF with pdfplumber (handles password automatically)
            with pdfplumber.open(pdf_path, password=password) as pdf:
                logger.info(f"Processing SBI Bank statement with {len(pdf.pages)} pages")

                # Step 1: Extract metadata from header sections
                self.statement_metadata = self._extract_metadata_sbi(pdf)

                # Step 2: Extract transactions with multi-line handling
                self.transactions = self._extract_transactions_sbi(pdf)

                # Step 3: Calculate financial summary with DR/CR handling
                financial_summary = self._calculate_financial_summary_sbi()

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
                result = {
                    "total_transactions": len(self.transactions),
                    "processed_at": datetime.now().isoformat(),
                    "statement_metadata": {
                        "bank_name": self._bank_name,
                        "customer_name": self.statement_metadata.get("customer_name", "Not Found"),
                        "account_number": self.statement_metadata.get("account_number", "Not Found"),
                        "account_type": self.statement_metadata.get("account_type", "SAVINGS ACCOUNT"),
                        "statement_period": self.statement_metadata.get("statement_period", {}),
                        "currency": "INR"
                    },
                    "financial_summary": financial_summary,
                    "transactions": self.transactions,
                    "extractor_metadata": self.get_extraction_metadata()
                }

                logger.info(f"SBI Bank extraction completed: {len(self.transactions)} transactions, "
                          f'Balance verified: {financial_summary.get("balance_verified", False)}')

                return result

        except Exception as e:
            logger.error(f"Error extracting SBI Bank statement from {pdf_path}: {e}")
            raise
        finally:
            # Clear caches to free memory
            self._clear_cache()

    def _extract_metadata_sbi(self, pdf) -> Dict:
        """Extract metadata specific to SBI Bank format"""
        metadata = {
            "customer_name": "Not Found",
            "account_number": "Not Found",
            "account_type": "SAVINGS ACCOUNT",
            "statement_period": {"from_date": "Not Found", "to_date": "Not Found"}
        }

        try:
            # Extract text from first 2 pages for metadata
            first_page_text = self._safe_extract_page_text(pdf, 0)
            second_page_text = self._safe_extract_page_text(pdf, 1) if len(pdf.pages) > 1 else ""
            header_text = first_page_text + "\n" + second_page_text

            if not header_text.strip():
                logger.error("No text extracted from PDF header pages")
                return metadata

            # Extract customer name - typically at the top of the first page
            customer_name = self._extract_customer_name_sbi(first_page_text)
            if customer_name:
                metadata["customer_name"] = customer_name

            # Extract account number
            account_match = self.ACCOUNT_PATTERN.search(header_text)
            if account_match:
                metadata["account_number"] = account_match.group(1)

            # Extract statement period with DD-MM-YY format handling
            period_match = self.PERIOD_PATTERN.search(header_text)
            if period_match:
                from_date = self._normalize_date_format(period_match.group(1))
                to_date = self._normalize_date_format(period_match.group(2))
                metadata["statement_period"] = {
                    "from_date": from_date,
                    "to_date": to_date
                }

            # Extract additional metadata
            ifsc_match = self.IFSC_PATTERN.search(header_text)
            if ifsc_match:
                metadata["ifsc_code"] = ifsc_match.group(1)

            micr_match = self.MICR_PATTERN.search(header_text)
            if micr_match:
                metadata["micr_code"] = micr_match.group(1)

            cif_match = self.CIF_PATTERN.search(header_text)
            if cif_match:
                metadata["cif_number"] = cif_match.group(1)

            branch_match = self.BRANCH_PATTERN.search(header_text)
            if branch_match:
                metadata["branch_name"] = branch_match.group(1).strip()

            email_match = self.EMAIL_PATTERN.search(header_text)
            if email_match:
                metadata["customer_email"] = email_match.group(1)

            phone_match = self.PHONE_PATTERN.search(header_text)
            if phone_match:
                metadata["customer_phone"] = phone_match.group(1).strip()

            # Extract opening balance with DR/CR handling
            opening_match = self.OPENING_BALANCE_PATTERN.search(header_text)
            if opening_match:
                amount = float(opening_match.group(1).replace(',', ''))
                dr_cr = opening_match.group(2) if opening_match.group(2) else 'CR'
                metadata["opening_balance"] = amount if dr_cr == 'CR' else -amount

            logger.info(f"Extracted SBI Bank metadata for account: {metadata.get('account_number', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error extracting SBI Bank metadata: {e}")

        return metadata

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
            logger.debug(f"Error extracting customer name: {e}")
        return None

    def _normalize_date_format(self, date_str: str) -> str:
        """Convert DD-MM-YY to DD-MM-YYYY format"""
        try:
            # Handle both YY and YYYY formats
            if re.match(r'\d{2}-\d{2}-\d{2}$', date_str):
                # Convert YY to YYYY (assume 20XX for years 00-50, 19XX for 51-99)
                day, month, year = date_str.split('-')
                year_int = int(year)
                if year_int <= 50:
                    full_year = f"20{year}"
                else:
                    full_year = f"19{year}"
                return f"{day}-{month}-{full_year}"
            return date_str
        except Exception:
            return date_str

    def _extract_transactions_sbi(self, pdf) -> List[Dict]:
        """Extract transactions optimized for SBI Bank's multi-line format"""
        transactions = []

        try:
            logger.info("Starting SBI Bank transaction extraction with multi-line handling")

            # Method 1: Try table-based extraction first
            transactions = self._extract_with_table_parsing_sbi(pdf)
            if transactions:
                logger.info(f"Table parsing extracted {len(transactions)} transactions")
                return transactions

            # Method 2: Fallback to text-based parsing with multi-line handling
            logger.info("Falling back to text parsing with multi-line support")
            transactions = self._extract_with_text_parsing_sbi(pdf)

        except Exception as e:
            logger.error(f"Error in SBI transaction extraction: {e}")

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
                    logger.warning(f"Error processing page {page_num}: {page_error}")
                    continue

        except Exception as e:
            logger.error(f"Table parsing error: {e}")
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
            logger.error(f"Error processing SBI transaction table: {e}")

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
            logger.warning(f"Error creating transaction from SBI row: {e}")
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
            logger.error(f"Error in SBI text parsing: {e}")

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
            logger.warning(f"Error parsing multi-line SBI transaction: {e}")
            return None, 1

    def _is_valid_sbi_date(self, date_str: str) -> bool:
        """Check if string is a valid SBI date (DD-MM-YY or DD-MM-YYYY)"""
        try:
            # Try DD-MM-YY format first
            if re.match(r'^\d{2}-\d{2}-\d{2}$', date_str):
                return True
            # Try DD-MM-YYYY format
            if re.match(r'^\d{2}-\d{2}-\d{4}$', date_str):
                return True
            return False
        except Exception:
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
                    return f"-{amount}"
                else:
                    return amount

            # Fallback - just clean the amount
            return self._clean_amount(balance_str)

        except Exception as e:
            logger.debug(f"Error parsing balance '{balance_str}': {e}")
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
                    logger.debug(f"Error processing transaction amounts: {e}")

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
            logger.error(f"Error calculating SBI financial summary: {e}")

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
            logger.debug(f"Transaction validation error: {e}")
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
            logger.error(f"Error extracting text from page {page_index}: {e}")
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
            logger.debug(f"Error extracting tables from page {page_num}: {e}")
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