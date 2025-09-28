# Bank Extractor Development Guide

## Development Workflow

### 1. PDF Analysis First (MANDATORY)
- **NEVER start coding without examining the actual PDF file**
- **ALWAYS identify table structure, column headers, and data layout first**
- **REQUIRED**: Document PDF structure in comments before implementation

### 2. Library Selection Strategy

#### Mandatory Implementation Hierarchy
```python
# REQUIRED extraction order (no exceptions):
1. pdfplumber: Primary choice for all PDFs (handles tables, text, passwords)
2. camelot-py: Secondary fallback only for bordered tables if pdfplumber fails
3. Text parsing: Last resort only for completely unstructured formats
# NOTE: pypdf is deprecated for new extractors
```

### 3. Table-Based Extraction Pattern

For tabular PDFs (REQUIRED approach):

```python
# Step 1: Open PDF with pdfplumber
with pdfplumber.open(pdf_path, password=password) as pdf:

# Step 2: Extract tables from each page
for page in pdf.pages:
    tables = page.extract_tables()

# Step 3: Process table rows directly
for table in tables:
    for row in table[1:]:  # Skip header
        # Map columns to transaction fields
        transaction = {
            "Date": row[0],
            "Particulars": row[2],
            "Debit": row[3],
            "Credit": row[4],
            "Balance": row[5]
        }

# Step 4: Clean and validate data
# Handle empty cells, number formatting, date validation
```

### 4. Regex Usage Philosophy

#### STRICT RULES:
- **ONLY use regex for metadata extraction** (customer name, account number, dates)
- **NEVER use regex for transaction parsing** in tabular PDFs
- **Keep patterns simple and robust** (avoid over-complex patterns that break)
- **Compile patterns at class level** for performance optimization

#### Example:
```python
class YourBankExtractor(BaseBankExtractor):
    # Compile regex patterns at class level
    ACCOUNT_NUMBER_PATTERN = re.compile(r'Account No[:\s]*(\d+)')
    CUSTOMER_NAME_PATTERN = re.compile(r'Customer Name[:\s]*([A-Z\s]+)')
```

### 5. Balance Verification Strategy

- **Extract opening/closing balances from headers/footers**, not transactions
- **Use direct balance values when available** instead of calculating
- **Verify mathematical consistency** but don't rely on balance math for transaction types
- **Handle Indian number formatting** (commas, decimal points)

### 6. Reference Implementation

**Use AxisBankExtractor v1.0.0 as the ONLY approved template** for new extractors:
- Located in `api/extractors/axis_bank_extractor.py`
- Demonstrates proper pdfplumber table extraction
- Shows correct output schema implementation
- Includes proper error handling patterns

## Bank-Specific Analysis Checklist

When implementing a new bank extractor:

1. **PDF Structure Assessment**: Determine if PDF uses tabular format or unstructured text
2. **Header Format**: How account information is structured in header/footer
3. **Table vs Text Layout**: Identify whether transactions are in structured tables or free text
4. **Column Mapping**: For tabular PDFs, map table columns to transaction fields
5. **Amount Formats**: Dr/Cr notation, decimal handling, currency symbols
6. **Date Formats**: Various date representations used by the bank
7. **Balance Calculation**: How running balances are displayed and calculated
8. **Encryption Patterns**: Common password formats and encryption methods

## Critical Implementation Rules

### Code Quality Requirements
- **Detailed Error Logging**: Error messages with context for debugging
- **Full Type Hints**: Python type annotations for better code quality
- **Comprehensive Documentation**: Docstrings for all methods
- **Unit Testability**: Code that can be easily unit tested
- **Performance Optimization**: Optimized for Lambda execution environment

### Development Process Rules
1. **ALWAYS create tasks/todo.md plan first** and get user approval
2. **ALWAYS test with actual PDF samples** before considering complete
3. **ALWAYS validate complete JSON output** matches AxisBankExtractor format
4. **NEVER implement temporary workarounds** - find and fix root causes

## Testing Protocol

1. **Unit Testing**: Test individual methods with mock data
2. **Integration Testing**: Test with actual PDF samples
3. **Schema Validation**: Ensure output matches exact JSON schema
4. **Error Scenario Testing**: Test with corrupted/incomplete PDFs
5. **Performance Testing**: Verify Lambda execution time limits

## Common Pitfalls to Avoid

- Using pypdf for new implementations
- Regex parsing of tabular transaction data
- Ignoring password protection requirements
- Inconsistent date formatting in output
- Missing error handling for edge cases
- Not following AxisBankExtractor patterns
- Implementing custom output schemas