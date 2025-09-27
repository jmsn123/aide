# Bank Configuration Table - DynamoDB
# Stores Indian bank configurations for PDF extraction

resource "aws_dynamodb_table" "bank_configurations" {
  name         = "${var.name_prefix}-bank-configurations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  # Primary key attributes
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # BankCode attribute for GSI
  attribute {
    name = "BankCode"
    type = "S"
  }

  # GSI for efficient queries by BankCode
  global_secondary_index {
    name               = "BankCode-Index"
    hash_key           = "BankCode"
    projection_type    = "ALL"
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  tags = merge(var.tags, {
    Name      = "${var.name_prefix}-bank-configurations"
    Purpose   = "Bank configurations for PDF extraction"
    Component = "Configuration"
  })
}