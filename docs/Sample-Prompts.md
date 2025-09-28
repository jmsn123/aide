Prompts:

## Example 1: Axis Bank PDF Extractor Implementation
--------
I need to add support for Axis Bank PDF statements to our serverless PDF extraction system. Please use the bank-extractor-specialist agent to:

  1. Analyze the sample PDF at '/Users/ramanjaneyulumedikonda/Downloads/axis original pdf.pdf' to understand:
    - Document structure and layout patterns
    - Transaction table format and columns
    - Date formats used
    - Balance information placement
    - Any multi-line transaction scenarios

  2. Create a complete Axis Bank extractor following our established patterns by:
    - Implementing axis_bank_extractor.py in the appropriate directory
    - Following the same class structure and methods as existing extractors
    - Handling edge cases like multi-line transactions, different date formats, and balance calculations
    - Including proper error handling and validation

  3. Ensure integration with the existing system:
    - Register the new extractor in the bank registry
    - Follow naming conventions used by other bank extractors
    - Include appropriate logging and debugging information

  Please analyze the PDF format thoroughly before implementation and create a robust extractor that handles the specific formatting patterns used by Axis Bank statements.
-----------

## Example 2: Bank of India PDF Extractor Implementation
--------
Use the bank-extractor-specialist agent to implement support for Bank Of India statement, physical file is in this location '/Users/ramanjaneyulumedikonda/Downloads/bank statements samples/boi original pdf and original excel/kona1006.pdf' this PDF file is password protected, and password is kona1006, use password to unlock the file.
Please analyze the format and create a complete extractor following the established patterns.

Use bank-extractor-specialist agent to create the extractor implementation
-----------
