# Bank Extractor Interface Documentation

## BaseBankExtractor Abstract Class

All bank extractors must inherit from `BaseBankExtractor` class located in `api/extractors/base_extractor.py`.

### Required Abstract Methods

Every extractor must implement these four methods:

```python
def get_bank_name(self) -> str:
    """Return official bank name"""

def get_version(self) -> str:
    """Return extractor version (use semantic versioning)"""

def get_supported_capabilities(self) -> List[str]:
    """Return list of supported capabilities from STANDARD_CAPABILITIES"""

def extract_complete_statement(self, pdf_path: str, password: Optional[str] = None) -> Dict:
    """Main extraction method"""
```

### Standard Capabilities

Declare only supported capabilities from this list:
- `account_metadata`
- `balance_calculation`
- `financial_summary`
- `multi_page`
- `password_protected`
- `statement_period`
- `transactions`
- `upi_transactions`

## Mandatory Output Schema

All extractors MUST return this EXACT JSON structure:

```json
{
  "customer_name": "string",
  "account_number": "string",
  "statement_period": {
    "from_date": "DD-MM-YYYY",
    "to_date": "DD-MM-YYYY"
  },
  "ifsc_code": "string (if available)",
  "micr_code": "string (if available)",
  "customer_id": "string (if available)",
  "customer_phone": "string (if available)",
  "customer_email": "string (if available)",
  "pan_number": "string (if available)",
  "opening_balance": "float",
  "account_type": "string",
  "transactions": [
    {
      "S.No": "string (sequential)",
      "Date": "DD-MM-YYYY",
      "Transaction_ID": "string (empty if not available)",
      "Remarks": "string",
      "Debit": "string (amount or empty)",
      "Credit": "string (amount or empty)",
      "Balance": "string (amount)",
      "Transaction_Type": "Credit or Debit",
      "Page_Number": "int"
    }
  ],
  "total_transactions": "int",
  "financial_summary": {
    "total_credits": "float",
    "total_debits": "float",
    "net_change": "float",
    "opening_balance": "float",
    "closing_balance": "float",
    "balance_verified": "boolean"
  },
  "extraction_metadata": {
    "extractor_name": "string (class name)",
    "version": "string (semantic version)",
    "extraction_method": "string",
    "bank_name": "string",
    "total_pages_processed": "int",
    "extraction_timestamp": "ISO timestamp",
    "optimization_notes": "string"
  }
}
```

## Integration Requirements

### Package Integration
Add new extractors to `api/extractors/__init__.py`:

```python
from .your_bank_extractor import YourBankExtractor
```

### Error Handling
- Never fail silently - always log detailed error information
- Provide graceful degradation - return partial data when possible
- Include debug information for troubleshooting
- Use structured logging for CloudWatch monitoring

### Performance Requirements
- Optimize for Lambda execution environment
- Use compiled regex patterns at class level
- Implement efficient table processing
- Handle multi-page processing with consistent numbering