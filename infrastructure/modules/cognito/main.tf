# AWS Cognito User Pool Configuration
# Authentication service for PDF Extractor API

# Cognito User Pool - Lite Tier
resource "aws_cognito_user_pool" "main" {
  name = "${var.name_prefix}-user-pool"

  # Use email as username
  alias_attributes         = ["email", "preferred_username"]
  auto_verified_attributes = ["email"]

  # Password policy (enterprise-grade security)
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # Account recovery - email only
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false

    string_attribute_constraints {
      min_length = 5
      max_length = 256
    }
  }

  schema {
    name                = "name"
    attribute_data_type = "String"
    required            = false
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Email configuration (using default Cognito email)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # MFA configuration - OFF for MVP phase
  # Rationale:
  #   - Saves ~$0.10 per 1000 emails (cost optimization for early stage)
  #   - Reduces friction for initial user adoption
  #   - Can be enabled later when user base grows
  # When enabled, supports:
  #   - Email OTP (one-time password via email)
  #   - TOTP (Time-based OTP via authenticator apps like Google Authenticator)
  # Recommended to enable when:
  #   - User base exceeds 1,000 MAU
  #   - Handling sensitive financial data
  #   - Security audit requires it
  mfa_configuration = "OFF"

  # User pool add-ons (not using advanced security for now - saves cost)
  # Advanced security features can be enabled later if needed ($0.05/MAU extra)

  # Admin create user configuration
  admin_create_user_config {
    allow_admin_create_user_only = false # Allow self-registration

    invite_message_template {
      email_subject = "Your PDF Extractor API account"
      email_message = "Welcome! Your username is {username} and temporary password is {####}"
      sms_message   = "Your username is {username} and temporary password is {####}"
    }
  }

  # User pool deletion protection
  deletion_protection = var.environment == "prod" ? "ACTIVE" : "INACTIVE"

  # Verification message templates
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Verify your email for PDF Extractor API"
    email_message        = "Your verification code is {####}"
  }

  # User attribute update settings
  user_attribute_update_settings {
    attributes_require_verification_before_update = ["email"]
  }

  # Device configuration
  device_configuration {
    challenge_required_on_new_device      = false
    device_only_remembered_on_user_prompt = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-user-pool"
    Type = "Cognito-UserPool"
  })

  lifecycle {
    # Terraform-level deletion protection (manual flag)
    # Set to true in production deployment to prevent accidental terraform destroy
    # This is intentionally NOT variable-based for additional safety
    # AWS-level deletion_protection (line 79) is already environment-aware
    prevent_destroy = false
  }
}

# Cognito User Pool Client (for frontend authentication)
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.name_prefix}-user-pool-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # OAuth configuration
  generate_secret = false # Public client (frontend/SPA) - no client secret needed

  # Token validity configuration
  # Access token: 60 minutes (1 hour)
  #   - Short-lived for security (limits exposure window)
  #   - Long enough for reasonable session duration
  #   - Automatically refreshed by refresh token before expiry
  # Refresh token: 30 days
  #   - Industry standard for web applications
  #   - Balances security (not too long) with UX (not too short)
  #   - User stays logged in for month without re-entering password
  # ID token: 60 minutes (matches access token)
  #   - Contains user claims (email, name, sub)
  #   - Used for user profile information
  refresh_token_validity = 30    # 30 days
  access_token_validity  = 60    # 60 minutes
  id_token_validity      = 60    # 60 minutes
  token_validity_units {
    refresh_token = "days"
    access_token  = "minutes"
    id_token      = "minutes"
  }

  # Authentication flows
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",       # Email + password authentication
    "ALLOW_REFRESH_TOKEN_AUTH",       # Refresh token flow
    "ALLOW_USER_SRP_AUTH",            # Secure Remote Password (more secure)
    "ALLOW_CUSTOM_AUTH",              # For future custom authentication
    "ALLOW_ADMIN_USER_PASSWORD_AUTH"  # Admin authentication for server-side login
  ]

  # Prevent user existence errors (security best practice)
  prevent_user_existence_errors = "ENABLED"

  # Read/write attributes
  read_attributes = [
    "email",
    "email_verified",
    "name",
    "sub"
  ]

  write_attributes = [
    "email",
    "name"
  ]

  # Enable token revocation
  enable_token_revocation = true

  # Allowed OAuth flows (for future social login)
  allowed_oauth_flows_user_pool_client = false
  allowed_oauth_flows                  = []
  allowed_oauth_scopes                 = []

  # Callback URLs (can be updated later for social login)
  callback_urls        = []
  logout_urls          = []
  default_redirect_uri = null

  # Supported identity providers
  supported_identity_providers = ["COGNITO"]
}

# Optional: Cognito User Pool Domain (for hosted UI)
# Uncomment if you want to use Cognito Hosted UI
# resource "aws_cognito_user_pool_domain" "main" {
#   count        = var.environment == "prod" ? 1 : 0
#   domain       = "${var.name_prefix}-auth"
#   user_pool_id = aws_cognito_user_pool.main.id
# }
