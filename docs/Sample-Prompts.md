I need to add support for ANDHRA PRADESH GRAMEENA BANK PDF statements to my extraction system. The PDFs have a different format with transaction tables and I need to extract account details, transactions, and calculate financial summaries.
-------
I need to add support for ANDHRA PRADESH GRAMEENA BANK PDF statements. Please use Task(subagent_type="bank-statement-extractor") agent with hooks to:

  1. Analyze the PDF format from the sample at /Users/ramanjaneyulumedikonda/Downloads/bank statements samples/apgvb only pdf/APGVB.pdf
  2. Create a complete extractor following BaseBankExtractor interface
  3. Validate output structure and financial accuracy
  4. Update the bank configuration system
  5. Run comprehensive tests

Please run the bank-statement-extractor and general-purpose agents in parallel for  efficiency.
--------
  Use the bank-statement-extractor agent to implement support for [BANK_NAME] PDF 
  statements. Please analyze the format and create a complete extractor following the 
  established patterns.

--------
  Use the bank-statement-extractor agent to implement support for Bank Of India statement, physical file is in this location '/Users/ramanjaneyulumedikonda/Downloads/bank statements samples/boi original pdf and original excel/kona1006.pdf' this odf file is password protected, and password is kona1006, use password to unlock the file.
  Please analyze the format and create a 
  complete extractor following the established patterns.

  Use bank-statement-extractor agent to create the extractor implementation
-----------

