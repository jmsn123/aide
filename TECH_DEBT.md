# Technical Debt Documentation

This document tracks technical debt, deferred features, and future improvements for the PDF Extractor API authentication system.

## Table of Contents
- [Authentication & Authorization](#authentication--authorization)
- [Infrastructure & DevOps](#infrastructure--devops)
- [Code Quality & Architecture](#code-quality--architecture)
- [Security Enhancements](#security-enhancements)

---

## Authentication & Authorization

### 0. Frontend Authentication UI
**Status**: ✅ COMPLETED (Iteration 5 - Sep 30, 2025)
**Priority**: Critical
**Effort**: High (10 hours)

**Description**:
Enterprise-grade frontend authentication UI with login, signup, and protected route functionality. Follows industry patterns from Amazon, Netflix, and Google.

**Implementation Completed**:
- ✅ Auth utility module with JWT token management
- ✅ React Context for global auth state
- ✅ Signup page with password strength indicator
- ✅ Login page with "remember me" functionality
- ✅ Protected route wrapper with deep linking
- ✅ Authenticated navigation header
- ✅ Automatic token refresh every 5 minutes
- ✅ Exponential backoff retry logic (Netflix pattern)
- ✅ Client-side validation to reduce API calls

**Files Created**:
- `/ui/src/utils/auth.ts` (450 lines)
- `/ui/src/contexts/AuthContext.tsx` (230 lines)
- `/ui/src/pages/SignupPage.tsx` (380 lines)
- `/ui/src/pages/LoginPage.tsx` (265 lines)
- `/ui/src/components/ProtectedRoute.tsx` (65 lines)
- `/ui/src/components/AuthHeader.tsx` (130 lines)

**Files Modified**:
- `/ui/src/main.tsx` (routing updates)
- `/ui/src/pages/HomePage.tsx` (CTA updates)
- `/ui/src/components/HomeHeader.tsx` (conditional auth buttons)
- `/ui/src/pages/DashboardPage.tsx` (use AuthHeader)
- `/ui/src/config/api.ts` (JWT token injection)

**Cost Impact**: $0 (frontend-only changes)

**Future Enhancements** (see sections below):
- Frontend email verification UI
- Frontend password reset UI
- Remember me with secure cookie storage
- Session timeout warnings
- Social auth buttons (Google, GitHub)
- User profile editing page
- Account settings page
- Password change functionality

---

### 1. Email Verification Flow
**Status**: Deferred to Iteration 5
**Priority**: High
**Effort**: Medium

**Description**:
Currently, users can sign up but email verification is not enforced. The `email_verified` flag exists but no verification flow is implemented.

**Implementation Plan**:
```python
# Required components:
1. Lambda trigger: Cognito PreSignUp - Send verification email
2. Verification endpoint: POST /auth/verify-email
3. Resend verification: POST /auth/resend-verification
4. Update Cognito user pool: email_verified = true after verification
```

**Acceptance Criteria**:
- [ ] Users receive verification email after signup
- [ ] Email contains secure verification link with token
- [ ] Token expires after 24 hours
- [ ] Users can resend verification email
- [ ] Unverified users have limited access or cannot login

**Resources**:
- AWS Cognito Custom Message Lambda Trigger
- SES for email delivery
- DynamoDB for verification token storage

---

### 2. Password Reset Flow
**Status**: Not implemented
**Priority**: High
**Effort**: Medium

**Description**:
Users cannot reset forgotten passwords. Need forgot password and password reset flow.

**Implementation Plan**:
```python
# Required endpoints:
1. POST /auth/forgot-password - Initiate reset
2. POST /auth/reset-password - Complete reset with code
```

**Acceptance Criteria**:
- [ ] Users receive password reset code via email
- [ ] Code expires after 1 hour
- [ ] Code is single-use
- [ ] New password meets complexity requirements
- [ ] User can login with new password

**IAM Permissions Already Added**:
✅ `cognito-idp:ForgotPassword`
✅ `cognito-idp:ConfirmForgotPassword`

---

### 3. Login Endpoint
**Status**: ✅ COMPLETED (Iteration 4 - Sep 30, 2025)
**Priority**: Critical
**Effort**: Medium

**Description**:
Users can sign up but cannot login. Need authentication endpoint that returns JWT tokens.

**Implementation Plan**:
```python
# POST /auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**Acceptance Criteria**:
- [x] Validate credentials against Cognito
- [x] Return access token (60 min) and refresh token (30 days)
- [x] Update last_login in DynamoDB (best effort)
- [x] Handle incorrect credentials gracefully
- [ ] Rate limit login attempts (Deferred to Iteration 11 - AWS WAF)

**Implementation Details**:
- Created `auth_login` Lambda function with admin authentication flow
- Added `ALLOW_ADMIN_USER_PASSWORD_AUTH` to Cognito User Pool Client
- Returns access_token, id_token, refresh_token, and user profile
- Validates email format and credentials
- Updates last_login timestamp (non-blocking)
- Comprehensive error handling for various failure scenarios
- CORS enabled for browser compatibility

**Known Limitations** (Acceptable for MVP):
- No lazy profile creation: If DynamoDB write fails during signup, user must re-signup
- DynamoDB dependency: Login requires DynamoDB lookup (99.99% availability acceptable)
- Rate limiting: Relies on Cognito built-in limits (5 attempts/sec per account)
- Monitoring: Uses CloudWatch Logs only (no custom metrics to minimize cost)

---

### 4. JWT Validation Utility
**Status**: Not implemented (Iteration 5)
**Priority**: Critical
**Effort**: Low

**Description**:
Need shared utility for validating JWT tokens from Cognito across all Lambda functions.

**Implementation Plan**:
```python
# api/auth_utils.py
import jwt
from jwt.algorithms import RSAAlgorithm
import requests

def validate_jwt(token):
    """Validate Cognito JWT token"""
    # 1. Get Cognito public keys (cached)
    # 2. Verify signature
    # 3. Check expiration
    # 4. Validate issuer
    # 5. Return decoded token
```

**Acceptance Criteria**:
- [ ] Validates token signature using Cognito public keys
- [ ] Checks token expiration
- [ ] Validates token issuer (User Pool)
- [ ] Caches Cognito JWKS for performance
- [ ] Returns user_id (sub) from valid tokens

---

### 5. API Gateway JWT Authorizer
**Status**: Not implemented (Iteration 6)
**Priority**: Critical
**Effort**: Low

**Description**:
Protected endpoints currently use API key. Need JWT authorizer for user-specific access.

**Implementation Plan**:
```hcl
# Terraform: JWT Authorizer
resource "aws_api_gateway_authorizer" "jwt" {
  name          = "cognito-jwt-authorizer"
  type          = "COGNITO_USER_POOLS"
  rest_api_id   = aws_api_gateway_rest_api.api.id
  provider_arns = [aws_cognito_user_pool.main.arn]
}

# Apply to protected routes
resource "aws_api_gateway_method" "upload_method" {
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.jwt.id
}
```

**Acceptance Criteria**:
- [ ] Upload endpoint requires JWT
- [ ] Statements endpoint requires JWT
- [ ] Auth endpoints (signup/login) remain public
- [ ] Invalid JWT returns 401 Unauthorized
- [ ] user_id from JWT available in Lambda event

---

## Infrastructure & DevOps

### 6. Rate Limiting with AWS WAF
**Status**: Not implemented
**Priority**: High
**Effort**: Medium

**Description**:
Public signup endpoint vulnerable to abuse/spam. Need rate limiting at API Gateway level.

**Implementation Plan**:
```hcl
# WAF Rate-Based Rule
resource "aws_wafv2_web_acl" "api" {
  name  = "${var.name_prefix}-api-waf"
  scope = "REGIONAL"

  rule {
    name     = "RateLimitSignup"
    priority = 1

    statement {
      rate_based_statement {
        limit              = 100  # requests per 5 minutes per IP
        aggregate_key_type = "IP"

        scope_down_statement {
          byte_match_statement {
            search_string = "/auth/signup"
            field_to_match {
              uri_path {}
            }
          }
        }
      }
    }

    action {
      block {
        custom_response {
          response_code = 429
          custom_response_body_key = "rate_limit_exceeded"
        }
      }
    }
  }
}
```

**Acceptance Criteria**:
- [ ] Signup: 100 requests per 5 min per IP
- [ ] Login: 20 requests per 5 min per IP
- [ ] Returns 429 status when exceeded
- [ ] CloudWatch metrics for rate limit hits
- [ ] Whitelist for known IPs (optional)

**Cost**: ~$5/month + $0.60 per million requests

---

### 7. Usage Limits Configuration Table
**Status**: Hardcoded in Lambda
**Priority**: Medium
**Effort**: Low

**Description**:
Plan limits (free/pro/enterprise) are hardcoded in Lambda code. Should be in DynamoDB config table for dynamic updates.

**Current State**:
```python
'usage_limits': {
    'requests_per_day': 100,
    'requests_per_month': 1000
}
```

**Desired State**:
```python
# DynamoDB: plan-configurations table
{
  'plan_id': 'free',
  'limits': {
    'requests_per_day': 100,
    'requests_per_month': 1000,
    'max_file_size_mb': 10,
    'concurrent_uploads': 2
  },
  'features': ['basic_extraction'],
  'price_per_month': 0
}
```

**Implementation**:
1. Create `plan-configurations` DynamoDB table
2. Add plans: free, pro, enterprise
3. Update Lambda to read from table
4. Add environment variable or cache for performance

---

### 8. Lambda Configuration Parameters
**Status**: Hardcoded in Terraform
**Priority**: Low
**Effort**: Low

**Description**:
Lambda timeout, memory, retention hardcoded. Should be variables for environment-specific tuning.

**Current State**:
```hcl
timeout         = 30
memory_size     = 256
retention_in_days = 7
```

**Desired State**:
```hcl
# variables.tf
variable "auth_lambda_config" {
  description = "Auth Lambda configuration"
  type = object({
    timeout           = number
    memory_size       = number
    log_retention     = number
  })
  default = {
    timeout       = 30
    memory_size   = 256
    log_retention = 7
  }
}

# Production override:
log_retention = 30  # Keep logs longer in prod
```

---

## Code Quality & Architecture

### 9. DynamoDB Profile Recovery on Login
**Status**: Design documented, not implemented
**Priority**: Medium
**Effort**: Low

**Description**:
If DynamoDB write fails during signup, user exists in Cognito but not DynamoDB. Need lazy profile creation on first login.

**Implementation Plan**:
```python
# In login Lambda:
def lambda_handler(event, context):
    # Authenticate with Cognito
    tokens = cognito_client.admin_initiate_auth(...)
    user_id = decode_jwt(tokens['id_token'])['sub']

    # Check DynamoDB profile
    try:
        profile = users_table.get_item(Key={'user_id': user_id})
    except:
        profile = None

    if not profile:
        # Lazy create from Cognito
        cognito_user = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=email
        )
        profile = create_profile_from_cognito(cognito_user)
        users_table.put_item(Item=profile)

    return {
        'tokens': tokens,
        'profile': profile
    }
```

**Acceptance Criteria**:
- [ ] Login checks if DynamoDB profile exists
- [ ] Missing profiles created from Cognito data
- [ ] CloudWatch alert for orphaned users
- [ ] Metrics: orphaned_users_recovered

---

### 10. Shared Response Utility Module
**Status**: Implemented in signup, needs extraction
**Priority**: Low
**Effort**: Low

**Description**:
`api_response()` helper is duplicated across Lambda functions. Extract to shared module.

**Implementation Plan**:
```python
# api/shared/response_utils.py
def api_response(status_code, body, include_cors=True):
    """Standardized API Gateway response with CORS"""
    headers = {'Content-Type': 'application/json'}

    if include_cors:
        headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': '...',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        })

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }

# Usage in Lambda:
from shared.response_utils import api_response

def lambda_handler(event, context):
    return api_response(200, {'message': 'Success'})
```

**Deployment**:
Add to Lambda Layer (business logic layer)

---

## Security Enhancements

### 11. Multi-Factor Authentication (MFA)
**Status**: Not implemented
**Priority**: Low (Optional feature)
**Effort**: High

**Description**:
Add optional MFA for enhanced security (SMS or TOTP).

**Implementation**:
```python
# Cognito User Pool already configured with MFA = "OFF"
# To enable:
1. Update Cognito: mfa_configuration = "OPTIONAL"
2. Add MFA setup endpoint: POST /auth/mfa/setup
3. Add MFA verify endpoint: POST /auth/mfa/verify
4. Update login flow to handle MFA challenges
```

**Cost**: SMS MFA: $0.00645 per message (SNS)

---

### 12. Account Lockout Policy
**Status**: Not implemented
**Priority**: Medium
**Effort**: Low

**Description**:
Prevent brute force attacks by locking accounts after N failed login attempts.

**Implementation**:
```python
# DynamoDB tracking:
{
  'user_id': 'uuid',
  'failed_login_attempts': 5,
  'locked_until': '2025-09-30T22:00:00Z'
}

# In login Lambda:
if user.failed_attempts >= 5:
    if user.locked_until > now:
        return api_response(403, {
            'error': {
                'code': 'ACCOUNT_LOCKED',
                'message': 'Too many failed attempts. Try again later.'
            }
        })
```

**Policy**:
- 5 failed attempts within 15 minutes
- Lock account for 30 minutes
- Email notification on lockout
- Admin unlock capability

---

### 13. Audit Logging
**Status**: Basic CloudWatch, no structured audit log
**Priority**: Medium
**Effort**: Medium

**Description**:
Comprehensive audit trail for security and compliance.

**Events to Log**:
- User signup
- Login (success/failure)
- Password reset
- Email verification
- Profile updates
- Account deletion
- Permission changes

**Implementation**:
```python
# DynamoDB: audit-logs table
{
  'log_id': 'uuid',
  'user_id': 'uuid',
  'event_type': 'LOGIN_SUCCESS',
  'timestamp': '2025-09-30T20:00:00Z',
  'ip_address': '192.168.1.1',
  'user_agent': 'Mozilla/5.0...',
  'metadata': {
    'location': 'US',
    'device': 'Desktop'
  }
}
```

---

## Frontend Enhancements

### 17. Session Timeout Warning Modal
**Status**: Not implemented
**Priority**: Medium
**Effort**: Low (2-3 hours)

**Description**:
Users are automatically logged out after token expires (60 minutes) without warning. Need modal to warn users and allow extending session.

**UX Pattern**: Banking apps style - "Your session is about to expire in 2 minutes"

**Implementation**:
```typescript
// ui/src/components/SessionTimeoutModal.tsx
export function SessionTimeoutModal() {
  const [showWarning, setShowWarning] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState(120) // 2 minutes
  const { refreshUserSession } = useAuth()

  // Show warning 2 minutes before expiry
  useEffect(() => {
    const expiryStr = localStorage.getItem('token_expiry')
    const expiry = parseInt(expiryStr || '0', 10)
    const timeUntilExpiry = expiry - Date.now()

    if (timeUntilExpiry < 120000) { // Less than 2 minutes
      setShowWarning(true)
      setTimeRemaining(Math.floor(timeUntilExpiry / 1000))
    }
  }, [])

  return showWarning ? (
    <Dialog open={showWarning}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Session Expiring Soon</DialogTitle>
          <DialogDescription>
            Your session will expire in {timeRemaining} seconds.
            Would you like to stay signed in?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => logout()}>Sign Out</Button>
          <Button onClick={() => { refreshUserSession(); setShowWarning(false); }}>
            Stay Signed In
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ) : null
}
```

**Acceptance Criteria**:
- [ ] Warning appears 2 minutes before token expiry
- [ ] Countdown timer shows remaining time
- [ ] "Stay Signed In" button refreshes token
- [ ] "Sign Out" button logs user out
- [ ] Auto-logout if no action taken
- [ ] Works across multiple tabs (localStorage events)

---

### 18. Frontend Email Verification UI
**Status**: Not implemented (depends on backend Iteration 8)
**Priority**: High
**Effort**: Medium (3-4 hours)

**Description**:
Backend email verification exists but no frontend UI to handle verification flow.

**Implementation Required**:
1. Create `/ui/src/pages/VerifyEmailPage.tsx`:
   - Extract verification token from URL query params
   - Call `/auth/verify-email` endpoint
   - Show success/error messages
   - Redirect to dashboard on success

2. Create `/ui/src/pages/ResendVerificationPage.tsx`:
   - Form to resend verification email
   - Call `/auth/resend-verification` endpoint

3. Update SignupPage:
   - Show "Check your email" message after signup
   - Link to resend verification page

**Route Updates**:
```typescript
// ui/src/main.tsx
<Route path="/verify-email" element={<VerifyEmailPage />} />
<Route path="/resend-verification" element={<ResendVerificationPage />} />
```

**Acceptance Criteria**:
- [ ] User receives email after signup
- [ ] Clicking email link verifies account
- [ ] Success message shown after verification
- [ ] User can resend verification email
- [ ] Expired tokens show clear error message

---

### 19. Frontend Password Reset UI
**Status**: Not implemented (depends on backend Iteration 9)
**Priority**: High
**Effort**: Medium (3-4 hours)

**Description**:
Backend password reset exists but no frontend UI to handle reset flow.

**Implementation Required**:
1. Create `/ui/src/pages/ForgotPasswordPage.tsx`:
   - Email input form
   - Call `/auth/forgot-password` endpoint
   - Show "Check your email" success message

2. Create `/ui/src/pages/ResetPasswordPage.tsx`:
   - Extract reset code from URL query params
   - New password form with strength indicator
   - Call `/auth/reset-password` endpoint
   - Redirect to login on success

3. Update LoginPage:
   - Add "Forgot password?" link below password field
   - Link to `/forgot-password` page

**Route Updates**:
```typescript
// ui/src/main.tsx
<Route path="/forgot-password" element={<ForgotPasswordPage />} />
<Route path="/reset-password" element={<ResetPasswordPage />} />
```

**Acceptance Criteria**:
- [ ] User can request password reset from login page
- [ ] User receives email with reset link
- [ ] Reset link contains secure code
- [ ] New password must meet complexity requirements
- [ ] Password strength indicator shown
- [ ] Expired codes show clear error message
- [ ] Success redirects to login page

---

### 20. User Profile Management Page
**Status**: Not implemented
**Priority**: Medium
**Effort**: Medium (4-5 hours)

**Description**:
Users cannot view or edit their profile information (name, email).

**Implementation**:
```typescript
// ui/src/pages/ProfilePage.tsx
export function ProfilePage() {
  const { user, updateProfile } = useAuth()
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || ''
  })

  return (
    <div>
      <AuthHeader />
      <div className="max-w-2xl mx-auto p-6">
        <h1>Profile Settings</h1>

        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpdateProfile}>
              <div>
                <Label>Full Name</Label>
                <Input name="name" value={formData.name} onChange={handleChange} />
              </div>
              <div>
                <Label>Email Address</Label>
                <Input name="email" value={formData.email} disabled />
                <p className="text-xs text-gray-500">
                  Contact support to change your email
                </p>
              </div>
              <Button type="submit">Save Changes</Button>
            </form>
          </CardContent>
        </Card>

        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleChangePassword}>
              <Input type="password" placeholder="Current password" />
              <Input type="password" placeholder="New password" />
              <Input type="password" placeholder="Confirm new password" />
              <Button type="submit">Update Password</Button>
            </form>
          </CardContent>
        </Card>

        <Card className="mt-6 border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">Danger Zone</CardTitle>
          </CardHeader>
          <CardContent>
            <Button variant="destructive" onClick={handleDeleteAccount}>
              Delete Account
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

**Backend Endpoints Needed**:
- `PUT /auth/profile` - Update user profile
- `POST /auth/change-password` - Change password
- `DELETE /auth/account` - Delete account

**Acceptance Criteria**:
- [ ] User can view current profile information
- [ ] User can update name (not email)
- [ ] User can change password with current password verification
- [ ] Password change requires logout and re-login
- [ ] Account deletion requires confirmation modal
- [ ] All changes reflected immediately in AuthHeader

---

### 21. Social Authentication (OAuth2)
**Status**: Not implemented
**Priority**: Low
**Effort**: High (8-12 hours)

**Description**:
Add "Sign in with Google" and "Sign in with GitHub" buttons.

**Pattern**: Google/GitHub OAuth2 flow with Cognito Federated Identity

**Implementation**:
1. Configure Cognito Identity Providers (Google, GitHub)
2. Add OAuth2 buttons to LoginPage and SignupPage
3. Handle OAuth2 callback URL
4. Create DynamoDB profile on first OAuth login

**Files to Modify**:
```typescript
// ui/src/pages/LoginPage.tsx
<Button onClick={() => loginWithGoogle()}>
  <GoogleIcon /> Sign in with Google
</Button>
<Button onClick={() => loginWithGitHub()}>
  <GitHubIcon /> Sign in with GitHub
</Button>

// ui/src/utils/auth.ts
export const loginWithGoogle = async () => {
  const oauthUrl = `${COGNITO_DOMAIN}/oauth2/authorize?...`
  window.location.href = oauthUrl
}

// ui/src/pages/OAuth2CallbackPage.tsx
// Handle OAuth2 redirect and exchange code for tokens
```

**Acceptance Criteria**:
- [ ] Google OAuth2 integration
- [ ] GitHub OAuth2 integration
- [ ] Profile creation on first OAuth login
- [ ] Existing email conflict handled gracefully
- [ ] User can link/unlink social accounts

---

### 22. Remember Me with Secure Cookies
**Status**: Partial (localStorage only)
**Priority**: Low
**Effort**: Medium (3-4 hours)

**Description**:
Currently "remember me" only saves email. Should persist refresh token in secure httpOnly cookie.

**Current State**: Saves email in localStorage
**Desired State**: Saves refresh token in secure cookie for 30 days

**Implementation**:
```typescript
// Backend: Set httpOnly cookie on login
res.setHeader('Set-Cookie', `refresh_token=${refreshToken}; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000`)

// Frontend: Remove refresh_token from localStorage
// Backend automatically reads from cookie on /auth/refresh endpoint
```

**Benefits**:
- ✅ More secure (JavaScript can't access refresh token)
- ✅ XSS protection
- ✅ True "remember me" functionality

**Acceptance Criteria**:
- [ ] Refresh token stored in httpOnly cookie
- [ ] Cookie set with Secure flag (HTTPS only)
- [ ] Cookie set with SameSite=Strict (CSRF protection)
- [ ] 30-day expiration
- [ ] /auth/refresh endpoint reads from cookie
- [ ] Logout clears cookie

---

## Monitoring & Observability

### 14. CloudWatch Dashboards
**Status**: Not created
**Priority**: Medium
**Effort**: Low

**Description**:
Centralized monitoring dashboard for authentication metrics.

**Metrics**:
- Signups per day/week
- Login success/failure rate
- Password reset requests
- Active users (DAU/MAU)
- API latency (p50, p95, p99)
- Error rates by endpoint
- DynamoDB throttling

**Implementation**:
Terraform CloudWatch Dashboard resource

---

### 15. CloudWatch Alarms
**Status**: Not configured
**Priority**: High
**Effort**: Low

**Description**:
Alerts for critical issues.

**Alarms**:
- Lambda errors > 1% in 5 minutes
- API Gateway 5xx > 1% in 5 minutes
- Login failures > 50 in 5 minutes (potential attack)
- DynamoDB throttling
- Cognito API errors

**Actions**:
- SNS topic → Email/Slack
- Auto-remediation (optional)

---

## Future Iterations Roadmap

### Immediate (Iterations 4-6)
1. ✅ Iteration 3: Signup endpoint (COMPLETED - Sep 30, 2025)
2. ✅ Iteration 4: Login endpoint (COMPLETED - Sep 30, 2025)
3. ✅ Iteration 5: Frontend Authentication UI (COMPLETED - Sep 30, 2025)
4. 🔄 Iteration 6: JWT validation utility + Update protected endpoints with JWT auth (NEXT)
5. ⏳ Iteration 7: Token refresh endpoint

### Short-term (Iterations 8-11)
6. ⏳ Iteration 8: Email verification
7. ⏳ Iteration 9: Password reset
8. ⏳ Iteration 10: User profile management
9. ⏳ Iteration 11: Frontend - Email verification UI

### Medium-term (Iterations 11-14)
9. ⏳ Iteration 11: Rate limiting with WAF
10. ⏳ Iteration 12: Audit logging
11. ⏳ Iteration 13: CloudWatch dashboards and alarms
12. ⏳ Iteration 14: Account lockout policy

### Long-term (Iterations 15-18)
13. ⏳ Iteration 15: MFA (optional)
14. ⏳ Iteration 16: OAuth2 social login
15. ⏳ Iteration 17: API key management
16. ⏳ Iteration 18: Auto-confirm for dev environment

---

## Priority Matrix

### P0 - Critical (Blocks production)
- [x] Login endpoint (Iteration 4) ✅ COMPLETED
- [ ] JWT authorizer (Iteration 6)
- [ ] Rate limiting (Iteration 11)

### P1 - High (Needed for MVP)
- [ ] Email verification (Iteration 7)
- [ ] Password reset (Iteration 8)
- [ ] CloudWatch alarms (Iteration 13)

### P2 - Medium (Quality of life)
- [ ] Audit logging (Iteration 12)
- [ ] Usage limits config table
- [ ] Account lockout policy
- [ ] CloudWatch dashboards

### P3 - Low (Nice to have)
- [ ] MFA
- [ ] OAuth2 social login
- [ ] Lambda config parameterization
- [ ] Shared response utility module

---

## Decision Log

### Why Cognito as Source of Truth?
**Decision**: Use Cognito for authentication, DynamoDB for metadata
**Rationale**:
- Cognito handles password hashing, MFA, JWT generation securely
- DynamoDB can be rebuilt from Cognito if needed
- Avoids complex rollback logic
- Better separation of concerns

**Alternative Considered**: Full transaction with rollback
**Why Not**: Adds complexity, could fail, not needed when Cognito is authoritative

---

### Why No Rollback on DynamoDB Failure?
**Decision**: Log warning, continue with signup
**Rationale**:
- User can authenticate with Cognito
- Profile can be created on first login (lazy initialization)
- Deleting Cognito user in rollback could fail, creating worse state
- CloudWatch alerts for orphaned users

**Mitigation**: Lazy profile creation in login Lambda

---

### Why Remove DynamoDB Duplicate Check?
**Decision**: Only use Cognito `UsernameExistsException`
**Rationale**:
- Cognito enforces uniqueness atomically (no race condition)
- DynamoDB check has race condition window
- Redundant check adds latency
- Cognito is source of truth

**Performance**: Saves ~50ms per signup request

---

## Contributing

When adding technical debt:
1. Describe the issue clearly
2. Explain why deferred (time/complexity/priority)
3. Provide implementation plan
4. List acceptance criteria
5. Tag with iteration number if planned

When resolving technical debt:
1. Update status to "Completed"
2. Link PR that resolved it
3. Add any new debt created
4. Update related sections

---

## Terraform Code Quality & Minimization

### 16. Terraform Code Minimization and Refactoring
**Status**: Not implemented
**Priority**: Medium
**Effort**: High (2-3 weeks)
**Estimated Impact**: 60-80% code reduction

**Description**:
Current Terraform infrastructure has significant code duplication, particularly in the API Gateway and Lambda modules. This leads to:
- High maintenance burden (1,190 lines in API Gateway alone)
- Increased risk of configuration drift
- Difficult to add new endpoints/functions
- Large git diffs for simple changes
- Harder code reviews

**Current State**:
```
infrastructure/modules/lambda/main.tf     - ~510 lines (10 Lambda functions, each ~50 lines)
infrastructure/modules/api_gateway/main.tf - ~1,190 lines (repetitive CORS, methods, integrations)
Total repetitive code: ~1,700 lines
```

**Proposed Optimization**:

#### 16.1. Lambda Functions - Use `for_each` with Metadata
**Reduction**: 510 lines → ~100 lines (80% reduction)

**Implementation**:
```hcl
# Create new file: infrastructure/modules/lambda/lambdas.tf
locals {
  api_functions = {
    api = {
      description     = "Main API handler for general endpoints"
      handler         = "handler.handler"
      timeout         = 180
      memory_size     = 512
      concurrency     = 5
      dlq_enabled     = true
      layers          = "api"
      environment_vars = { FUNCTION_TYPE = "api" }
    }
    upload = { ... }
    statement_data = { ... }
    # ... all 10 functions
  }

  all_functions = merge(
    local.api_functions,
    local.processor_functions,
    local.auth_functions
  )
}

# Refactor main.tf to use for_each:
resource "aws_lambda_function" "functions" {
  for_each = local.all_functions

  filename         = "${var.functions_dir}/${each.key}.zip"
  function_name    = "${var.name_prefix}-${each.key}"
  handler          = each.value.handler
  timeout          = each.value.timeout
  memory_size      = each.value.memory_size
  # ... dynamic configuration from metadata
}
```

**File Structure**:
```
infrastructure/modules/lambda/
├── main.tf              # Core Lambda resources (for_each logic)
├── lambdas.tf           # Lambda metadata configuration
├── event_sources.tf     # SQS triggers, EventBridge rules
├── variables.tf
├── outputs.tf
└── versions.tf
```

**Benefits**:
- ✅ Add new Lambda by adding 10 lines to `lambdas.tf`
- ✅ Change timeout/memory without touching main.tf
- ✅ Clear git diffs (config vs infrastructure)
- ✅ Type-safe with Terraform validation
- ✅ Team-friendly (junior devs edit lambdas.tf)

#### 16.2. API Gateway - Migrate to OpenAPI Specification
**Reduction**: 1,190 lines → ~450 lines (62% reduction)

**Recommendation**: Use OpenAPI spec instead of individual Terraform resources

**Implementation**:
```hcl
# modules/api_gateway/main.tf (simplified)
resource "aws_api_gateway_rest_api" "api" {
  name = "${var.name_prefix}-api"

  body = templatefile("${path.module}/openapi.yaml", {
    region                = data.aws_region.current.name
    cognito_user_pool_arn = var.cognito_user_pool_arn
    api_lambda_arn        = var.lambda_invoke_arn
    upload_lambda_arn     = var.upload_lambda_invoke_arn
    # ... other ARNs
  })
}

# Lambda permissions with for_each
locals {
  lambda_permissions = {
    api    = { name = var.lambda_function_name, path = "*/*" }
    upload = { name = var.upload_lambda_function_name, path = "*/POST/upload" }
    # ... more
  }
}

resource "aws_lambda_permission" "api_gateway" {
  for_each = local.lambda_permissions

  statement_id  = "AllowExecutionFromAPIGateway-${each.key}"
  function_name = each.value.name
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/${each.value.path}"
  # ...
}
```

**File Structure**:
```
infrastructure/modules/api_gateway/
├── main.tf           # Core API Gateway resources (~150 lines)
├── openapi.yaml      # API specification (~300 lines)
├── variables.tf
├── outputs.tf
```

**OpenAPI Benefits**:
- ✅ Industry standard, portable across clouds
- ✅ Auto-generated documentation (Swagger UI)
- ✅ Built-in request validation
- ✅ Easy to version control and diff
- ✅ Single source of truth for API
- ✅ AWS recommended best practice
- ✅ Eliminates 500+ lines of CORS boilerplate

**Alternative**: If OpenAPI is too drastic, create CORS module:
```
modules/api_gateway_cors/main.tf  # Reusable CORS resources
```
Saves ~500 lines of repetition.

#### 16.3. Consolidated Lambda Permissions
**Reduction**: ~150 lines → ~30 lines

**Current**: 8 individual `aws_lambda_permission` resources
**Proposed**: Single resource with `for_each` (see 16.2 above)

**Summary of Estimated Reductions**:
| Component | Current | Optimized | Reduction |
|-----------|---------|-----------|-----------|
| Lambda Functions | 510 lines | 100 lines | 80% |
| API Gateway | 1,190 lines | 450 lines | 62% |
| Lambda Permissions | 150 lines | 30 lines | 80% |
| **Total** | **1,850 lines** | **580 lines** | **69%** |

**Implementation Plan**:
1. [ ] Create backup branch: `git checkout -b terraform/code-minimization`
2. [ ] Phase 1: Lambda refactoring (Week 1)
   - [ ] Create `lambdas.tf` with metadata
   - [ ] Refactor `main.tf` to use `for_each`
   - [ ] Create `event_sources.tf` for triggers
   - [ ] Run `terraform plan` (should show NO changes)
   - [ ] Validate with `terraform validate`
3. [ ] Phase 2: API Gateway OpenAPI migration (Week 2)
   - [ ] Create `openapi.yaml` specification
   - [ ] Migrate endpoints incrementally
   - [ ] Test each endpoint after migration
   - [ ] Consolidate Lambda permissions
4. [ ] Phase 3: Testing and validation (Week 3)
   - [ ] Run full test suite
   - [ ] Deploy to dev environment
   - [ ] Monitor for any issues
   - [ ] Document new structure
5. [ ] Phase 4: Documentation and handoff
   - [ ] Update CLAUDE.md with new structure
   - [ ] Create migration guide
   - [ ] Team training session

**Acceptance Criteria**:
- [ ] `terraform plan` shows no changes after refactoring
- [ ] All endpoints function identically
- [ ] Code reduction of at least 60%
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Team trained on new structure

**Risks and Mitigations**:
- **Risk**: OpenAPI migration breaks existing endpoints
  - **Mitigation**: Incremental migration, test each endpoint
- **Risk**: for_each changes resource names/IDs
  - **Mitigation**: Use `moved` blocks to preserve state
- **Risk**: Team unfamiliar with OpenAPI
  - **Mitigation**: Training session, keep Terraform option as backup

**Decision Required**:
- [ ] Approve Lambda refactoring approach
- [ ] Choose: OpenAPI spec vs CORS module for API Gateway
- [ ] Assign implementation team and timeline

**References**:
- [AWS API Gateway OpenAPI Extensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-swagger-extensions.html)
- [Terraform for_each Meta-Argument](https://www.terraform.io/language/meta-arguments/for_each)
- [Managing Resource Drift with moved Blocks](https://www.terraform.io/language/modules/develop/refactoring)

**Comparison: OpenAPI vs Terraform Resources**:
| Aspect | OpenAPI Spec | Terraform Resources | Winner |
|--------|--------------|---------------------|--------|
| Code Size | 200-300 lines | 1000+ lines | ✅ OpenAPI |
| Readability | High | Low (repetitive) | ✅ OpenAPI |
| Version Control | Easy to diff | Hard to diff | ✅ OpenAPI |
| Request Validation | Built-in | Manual | ✅ OpenAPI |
| Documentation | Auto-generated | Manual | ✅ OpenAPI |
| Terraform State | Simple (1 resource) | Complex (100+ resources) | ✅ OpenAPI |
| Learning Curve | Medium | Low | ⚠️ Terraform |
| Complex Integrations | Limited | Full control | ⚠️ Terraform |

**Senior AWS Specialist Recommendation**: **Use OpenAPI Spec**
- AWS Best Practice documented in official guides
- Used by major enterprises (Netflix, Stripe, etc.)
- Reduces drift between documentation and implementation
- Better CI/CD integration (validate spec before deploy)
- Industry standard, portable across cloud providers

---

**Last Updated**: 2025-09-30
**Maintained By**: Development Team
**Review Frequency**: After each iteration
