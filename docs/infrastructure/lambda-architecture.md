# Lambda Architecture Documentation

## Three-Tier Serverless Architecture

### Architecture Overview

The PDF extraction system uses a layer-based Lambda architecture optimized for performance and cost:

- **Frontend**: React/Vite application with Tailwind CSS and TypeScript
- **API**: Python FastAPI serverless functions running on AWS Lambda
- **Infrastructure**: Terraform-managed AWS resources

### Layer-Based Lambda System

#### 1. Dependencies Layer (3rd Party Packages)
- **Purpose**: Contains external Python packages
- **Contents**: pdfplumber, camelot-py, pandas, numpy, etc.
- **Size Optimization**: Reduces individual function sizes by 80%
- **Update Frequency**: Only when dependencies change

#### 2. Business Logic Layer (Shared Code)
- **Purpose**: Contains shared extractor classes and utilities
- **Contents**: BaseBankExtractor, BankConfigService, utility functions
- **Size Optimization**: Eliminates code duplication across functions
- **Update Frequency**: When business logic changes

#### 3. Function Layer (Individual Handlers)
- **Purpose**: Contains lightweight function-specific code (1-3KB each)
- **Contents**: Lambda entry points and function-specific logic
- **Size Optimization**: Minimal footprint for faster cold starts
- **Update Frequency**: Most frequent - with each deployment

### Lambda Functions

#### 1. API Function (`api/lambdas/api/`)
- **Purpose**: Handles HTTP requests and PDF upload
- **Triggers**: API Gateway
- **Responsibilities**: Request validation, authentication, SQS queuing

#### 2. Processor Function (`api/lambdas/processor/`)
- **Purpose**: Performs actual PDF extraction
- **Triggers**: SQS messages
- **Responsibilities**: PDF processing, data extraction, result storage

#### 3. Cleanup Function (`api/lambdas/cleanup/`)
- **Purpose**: Cleans up temporary files and resources
- **Triggers**: Scheduled events
- **Responsibilities**: S3 cleanup, temporary file removal

#### 4. DLQ Processor Function (`api/lambdas/dlq_processor/`)
- **Purpose**: Handles failed extraction jobs
- **Triggers**: Dead Letter Queue messages
- **Responsibilities**: Error analysis, retry logic, failure notifications

## Build Process

### Layer Building

```bash
# Build all layers and functions
./infrastructure/scripts/build-all.sh

# Build layers only
./infrastructure/scripts/build-layers.sh

# Build functions only
./infrastructure/scripts/build-functions.sh
```

### Build Optimization

#### Automatic Minification
- **Production Code**: Comments and docstrings removed automatically
- **Size Reduction**: 60-80% reduction in file sizes
- **Performance**: Faster parsing and reduced memory usage
- **Process**: Uses `python-minifier` with safe settings

#### Layer Management
- **Dependency Tracking**: Layers rebuilt only when requirements change
- **Version Management**: Layer versions tracked for rollback capability
- **Shared Layers**: Common dependencies shared across functions

## Data Storage and Processing

### DynamoDB Tables

#### 1. Jobs Table
- **Purpose**: Track extraction job status and metadata
- **Structure**: JobID (PK), Status, BankName, ProcessingTime, etc.
- **Access Patterns**: Query by JobID, status filtering

#### 2. Transactions Table
- **Purpose**: Store extracted transaction data
- **Structure**: JobID (PK), TransactionID (SK), transaction details
- **Access Patterns**: Query by JobID, pagination support

#### 3. Usage Table
- **Purpose**: Track API usage and billing metrics
- **Structure**: UserID (PK), Date (SK), usage statistics
- **Access Patterns**: Query by user, date range filtering

### S3 Storage

#### PDF Storage
- **Bucket**: Temporary storage for uploaded PDFs
- **Lifecycle**: Auto-deletion after processing completion
- **Security**: Pre-signed URLs for secure access

#### Result Storage
- **Format**: JSON extraction results
- **Retention**: Configurable retention periods
- **Access**: Direct download or API retrieval

### SQS Queues

#### Processing Queue
- **Purpose**: Async PDF processing requests
- **Visibility Timeout**: Configured for extraction duration
- **Dead Letter Queue**: Failed message handling

#### Dead Letter Queue
- **Purpose**: Handle failed extractions
- **Retry Logic**: Exponential backoff
- **Monitoring**: CloudWatch alarms for queue depth

## Deployment Strategy

### Infrastructure Deployment
```bash
cd infrastructure
terraform plan -var-file="local.tfvars"
terraform apply -var-file="local.tfvars"
```

### Code-Only Deployment (Faster)
```bash
# For Lambda function code updates only
./scripts/build-functions.sh
terraform apply -var-file="local.tfvars"
```

### Rolling Updates
- **Zero Downtime**: Blue-green deployment pattern
- **Version Management**: Lambda aliases for traffic routing
- **Rollback**: Instant rollback to previous versions

## Performance Optimization

### Cold Start Mitigation
- **Lightweight Functions**: 1-3KB function packages
- **Shared Layers**: Pre-loaded dependencies
- **Connection Pooling**: DynamoDB connection reuse

### Memory and Timeout Configuration
- **API Function**: 512MB, 30s timeout
- **Processor Function**: 1024MB, 15min timeout
- **Cleanup Function**: 256MB, 5min timeout
- **DLQ Processor**: 512MB, 10min timeout

### Cost Optimization
- **Pay-per-Use**: Only charged for actual processing time
- **Layer Sharing**: Reduced storage costs
- **Auto-scaling**: Scales to zero when not in use

## Monitoring and Observability

### CloudWatch Integration
- **Logs**: Structured JSON logging with correlation IDs
- **Metrics**: Custom metrics for business logic
- **Alarms**: Automated alerting for errors and performance

### Distributed Tracing
- **Request Tracking**: End-to-end request correlation
- **Performance Analysis**: Identify bottlenecks
- **Error Attribution**: Trace errors to specific components

### Health Checks
- **API Health**: Endpoint health monitoring
- **Queue Health**: SQS queue depth monitoring
- **Storage Health**: S3 and DynamoDB availability