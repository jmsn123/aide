Prompts:
--------
I need to add support for Axis Bank PDF statements to our serverless PDF extraction system. Please use the bank-extractor-specialist agent to:

  1. Analyze the sample PDF at
  '/Users/ramanjaneyulumedikonda/Downloads/axis original pdf.pdf' to understand:
    - Document structure and layout patterns
    - Transaction table format and columns
    - Date formats used
    - Balance information placement
    - Any multi-line transaction scenarios
  1. Create a complete Axis Bank extractor following our established patterns by:
    - Implementing axis_bank_extractor.py in
  the appropriate directory
    - Following the same class structure and
  methods as existing extractors
    - Handling edge cases like multi-line
  transactions, different date formats, and
  balance calculations
    - Including proper error handling and
  validation
  1. Ensure integration with the existing
  system:
    - Register the new extractor in the bank
  registry
    - Follow naming conventions used by other
  bank extractors
    - Include appropriate logging and debugging
   information

  Please analyze the PDF format thoroughly
  before implementation and create a robust
  extractor that handles the specific
  formatting patterns used by Axis Bank
  statements.
-----------