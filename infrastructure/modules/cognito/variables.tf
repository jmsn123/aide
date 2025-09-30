# Variables for Cognito User Pool Module

variable "name_prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "environment" {
  description = "Environment name (dev, prod, etc.)"
  type        = string
  default     = "dev"
}

variable "auto_confirm_users" {
  description = "Auto-confirm users in development (skips email verification)"
  type        = bool
  default     = false

  # TODO: Implement via Lambda pre-signup trigger (Iteration 18)
  # When true, Lambda trigger will set:
  #   - event.response.autoConfirmUser = True
  #   - event.response.autoVerifyEmail = True
  # This skips email verification in dev for faster testing
}
