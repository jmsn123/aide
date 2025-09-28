# Bank Configuration and Dynamic Loading

## DynamoDB Configuration

### Required DynamoDB Fields

Bank configurations are stored in `BANK_CONFIGURATIONS_TABLE` with the following DynamoDB structure (showing actual AWS DynamoDB format with data types):

```json
{
  "PK": {
    "S": "BANK_CONFIG"
  },
  "SK": {
    "S": "ACTIVE#005#AXIS"
  },
  "BankCode": {
    "S": "AXIS"
  },
  "BankIdentifiers": {
    "SS": [
      "axis",
      "axis bank",
      "axis bank ltd",
      "axisbank"
    ]
  },
  "BankName": {
    "S": "Axis Bank"
  },
  "Capabilities": {
    "SS": [
      "account_metadata",
      "balance_calculation",
      "financial_summary",
      "multi_page",
      "password_protected",
      "statement_period",
      "transactions",
      "upi_transactions"
    ]
  },
  "ExtractorClass": {
    "S": "AxisBankExtractor"
  },
  "ExtractorFunction": {
    "S": "extract_axis_bank_statement"
  },
  "ExtractorModule": {
    "S": "extractors.axis_bank_extractor"
  },
  "LastUpdated": {
    "S": "2025-09-28T12:30:00Z"
  },
  "MaxFileSize": {
    "N": "50"
  },
  "Status": {
    "S": "ACTIVE"
  },
  "SupportedFormats": {
    "SS": [
      "PDF"
    ]
  },
  "Version": {
    "S": "1.0.0"
  }
}
```

### Field Specifications

#### Core Keys
- **PK**: Partition key, always `"BANK_CONFIG"` (String)
- **SK**: Sort key format `"ACTIVE#{priority}#{BankCode}"` for ordering (String)

#### Bank Information
- **BankCode**: 3-4 letter unique identifier (uppercase) (String)
- **BankName**: Display name for frontend dropdown (String)
- **BankIdentifiers**: Array of search terms for bank identification (String Set)
- **Version**: Extractor version using semantic versioning (String)

#### Extractor Configuration
- **ExtractorModule**: Python module path to extractor (String)
- **ExtractorClass**: Extractor class name (String)
- **ExtractorFunction**: Function name for extraction (String)
- **Capabilities**: Array of supported features from standard list (String Set)

#### Technical Specifications
- **Status**: Must be "ACTIVE" for loading (String)
- **MaxFileSize**: Maximum PDF file size in MB (Number)
- **SupportedFormats**: Array of supported file formats (String Set)
- **LastUpdated**: ISO timestamp of last configuration update (String)

#### DynamoDB Data Types
- **S**: String
- **N**: Number
- **SS**: String Set (array of strings)

## Dynamic Loading System

### BankConfigService Architecture

The system uses `api/bank_config.py` with multi-level caching:

1. **Memory Cache**: In-memory dictionary for fastest access
2. **LRU Cache**: Least Recently Used cache for frequently accessed configs
3. **DynamoDB**: Persistent storage with ACTIVE status filtering

### Security Validation

- **Module Path Validation**: Ensures safe dynamic imports
- **Class Existence Verification**: Validates extractor class exists
- **Interface Compliance**: Checks BaseBankExtractor inheritance

### Hot Reloading

- **Runtime Updates**: Extractor updates without Lambda restart
- **Cache Invalidation**: Automatic cache refresh on configuration changes
- **Error Recovery**: Graceful fallback on loading failures

## Integration with Lambda Architecture

### Layer-Based System

The system uses 3-layer Lambda architecture:

1. **Dependencies Layer**: Third-party packages (pdfplumber, pandas, etc.)
2. **Business Logic Layer**: Shared extractor classes and utilities
3. **Function Layer**: Individual Lambda handlers

### Dynamic Loading Flow

1. **Request Routing**: `api/extract_pdf_data.py` receives bank_name parameter
2. **Configuration Lookup**: BankConfigService queries DynamoDB for active config
3. **Module Loading**: Dynamic import of specified extractor module
4. **Class Instantiation**: Create extractor instance with validation
5. **Processing**: Execute extraction with error handling and logging

### Error Recovery Integration

- **Retry Logic**: Automatic retries on transient failures
- **Dead Letter Queue**: Failed jobs routed to DLQ for investigation
- **Logging Standards**: Structured CloudWatch logging for monitoring

## Frontend Integration

### Automatic Bank Discovery

- **API Endpoint**: `/api/banks` returns list of active banks
- **Dropdown Population**: Frontend automatically populates bank selection
- **Real-time Updates**: Configuration changes reflected immediately

### Bank Selection Requirement

- **Mandatory Selection**: Users must select bank before PDF upload
- **Validation**: API validates bank selection against active configurations
- **Error Handling**: Clear error messages for invalid/inactive banks

## Configuration Management

### Adding New Banks

1. **Implement Extractor**: Create new extractor class following standards
2. **Add to Package**: Update `api/extractors/__init__.py`
3. **Deploy Code**: Use `infrastructure/scripts/build-functions.sh`
4. **Add Configuration**: Insert DynamoDB record with all required fields
5. **Verify Loading**: Test dynamic loading via BankConfigService
6. **Frontend Testing**: Confirm bank appears in dropdown

### Updating Existing Banks

1. **Code Changes**: Update extractor implementation
2. **Deploy Functions**: Rebuild and deploy Lambda functions
3. **Configuration Updates**: Modify DynamoDB record if needed
4. **Cache Invalidation**: Service automatically refreshes cache
5. **Verification**: Test extraction with updated code

### Deactivating Banks

- **Status Change**: Set Status to "INACTIVE" in DynamoDB
- **Automatic Removal**: Bank disappears from frontend dropdown
- **Graceful Handling**: Existing jobs complete, new jobs rejected

## Monitoring and Troubleshooting

### CloudWatch Logging

- **Structured Logs**: JSON format with correlation IDs
- **Error Context**: Detailed error information for debugging
- **Performance Metrics**: Extraction timing and success rates

### Common Issues

- **Module Not Found**: Check ExtractorModule path in configuration
- **Class Loading Error**: Verify ExtractorClass name matches implementation
- **Cache Issues**: Monitor cache hit rates and invalidation patterns
- **Status Problems**: Ensure Status field is exactly "ACTIVE"