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
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from decimal import Decimal, InvalidOperation

# PDF processing library
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    raise ImportError("pdfplumber is required for Axis Bank PDF extraction. Install with: pip install pdfplumber")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

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
    CUSTOMER_PATTERN = re.compile(r'^([A-Z\s]+)\n', re.MULTILINE)
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
        self.supported_formats = ["PDF"]
        self.transactions = []
        self.statement_metadata = {}

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
                self.transactions = self._extract_transactions_optimized(pdf_path, pdf)

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

    def _extract_metadata_optimized(self, pdf) -> Dict:
        """Extract metadata with corrected patterns for actual PDF format"""
        metadata = {}

        try:
            # Get text from first and last pages
            first_page_text = pdf.pages[0].extract_text()
            last_page_text = pdf.pages[-1].extract_text() if len(pdf.pages) > 1 else ""
            full_text = first_page_text + "\n" + last_page_text

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

            # Set defaults
            if "account_type" not in metadata:
                metadata["account_type"] = "SAVINGS ACCOUNT"

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

    def _extract_transactions_optimized(self, pdf_path: str, pdf) -> List[Dict]:
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
                # Extract tables from this page
                tables = page.extract_tables()

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
                        if transaction:
                            transactions.append(transaction)

        except Exception as e:
            logger.error(f"PDFPlumber optimized extraction error: {e}")
            raise

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
        """Parse a single transaction line optimized for Axis Bank format"""
        try:
            # Split the line into components
            parts = line.split()
            if len(parts) < 3:
                return None

            # Extract date (first part)
            date = parts[0]
            if not self._is_valid_date(date):
                return None

            # Find amounts (last few parts that are numeric)
            amounts = []
            description_parts = []

            for part in parts[1:]:  # Skip date
                # Check if this part looks like an amount
                clean_part = part.replace(',', '')
                if re.match(r'^\d+\.?\d*$', clean_part):
                    amounts.append(float(clean_part))
                else:
                    description_parts.append(part)

            if not amounts:
                return None

            # Determine debit/credit and balance
            balance = amounts[-1] if amounts else 0  # Last amount is typically balance

            # For Axis Bank, we need to look at transaction description patterns
            description = ' '.join(description_parts)
            credit_amount = ""
            debit_amount = ""

            # Simple heuristic: if only one amount besides balance, it's transaction amount
            if len(amounts) == 2:  # Transaction amount + balance
                transaction_amount = amounts[0]
                # Determine if credit or debit based on description patterns
                if any(keyword in description.upper() for keyword in ['UPI/P2A', 'CREDIT', 'RECEIVED']):
                    credit_amount = str(transaction_amount)
                else:
                    debit_amount = str(transaction_amount)
            elif len(amounts) >= 3:  # Might have debit, credit, balance
                if len(amounts) >= 3:
                    # Assume: debit, credit, balance (adjust based on actual format)
                    debit_amount = str(amounts[0]) if amounts[0] > 0 else ""
                    credit_amount = str(amounts[1]) if len(amounts) > 1 and amounts[1] > 0 else ""

            transaction = {
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

            return transaction

        except Exception as e:
            logger.warning(f"Error parsing transaction line: {e}")
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
        """Calculate financial summary - no complex balance math needed"""
        summary = {
            'total_credits': 0.0,
            'total_debits': 0.0,
            'net_change': 0.0,
            'opening_balance': self.statement_metadata.get('opening_balance', 0.0),
            'closing_balance': 0.0,
            'balance_verified': False
        }

        try:
            # Calculate totals from transactions
            for tx in self.transactions:
                if tx.get('Credit') and tx['Credit'].replace(',', '').replace('.', '').isdigit():
                    summary['total_credits'] += float(tx['Credit'].replace(',', ''))
                if tx.get('Debit') and tx['Debit'].replace(',', '').replace('.', '').isdigit():
                    summary['total_debits'] += float(tx['Debit'].replace(',', ''))

            summary['net_change'] = summary['total_credits'] - summary['total_debits']

            # Get closing balance from metadata or last transaction
            if 'closing_balance' in self.statement_metadata:
                summary['closing_balance'] = self.statement_metadata['closing_balance']
            elif self.transactions:
                last_balance = self.transactions[-1].get('Balance', '')
                if last_balance:
                    try:
                        summary['closing_balance'] = float(last_balance.replace(',', ''))
                    except ValueError:
                        pass

            # Verify balance calculation
            expected_balance = summary['opening_balance'] + summary['net_change']
            balance_diff = abs(summary['closing_balance'] - expected_balance)
            summary['balance_verified'] = balance_diff < 1.0  # Allow 1 rupee difference

        except Exception as e:
            logger.error(f"Error calculating financial summary: {e}")

        return summary

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