# Frontend Authentication UI - Implementation Plan

## Current Status
- ✅ Backend: Cognito Infrastructure (COMPLETED)
- ✅ Backend: DynamoDB Users Table (COMPLETED)
- ✅ Backend: Signup Endpoint `/auth/signup` (COMPLETED)
- ✅ Backend: Login Endpoint `/auth/login` (COMPLETED)
- ❌ Frontend: No auth UI exists - building now

---

## 🎯 ACTIVE: Build Login & Signup UI

**Goal**: Connect frontend to existing backend auth system with login/signup screens

**Estimated Effort**: 8-12 hours

**Design Principles**:
- ✅ **Cost-Effective**: Zero additional AWS costs (frontend-only changes)
- ✅ **High Availability**: Leverages existing Cognito (99.9% SLA) + DynamoDB (99.99% SLA)
- ✅ **Enterprise-Grade**: Industry-standard JWT auth, secure token storage, proper error handling
- ✅ **Simplicity**: Minimal code, maximum reliability

---

## 📋 Implementation Tasks

### Phase 1: Foundation (2-3 hours)
- [ ] 1. Research existing UI patterns (shadcn/ui forms, validation)
- [ ] 2. Create auth utility module `/ui/src/utils/auth.ts`
  - **Cost**: Zero (client-side code only)
  - API client functions (signup, login, logout)
  - JWT token storage (localStorage - browser native, free)
  - Token validation helpers (client-side parsing only)
  - Get current user helper
  - **Enterprise**: Proper error handling, retry logic with exponential backoff
- [ ] 3. Create AuthContext `/ui/src/contexts/AuthContext.tsx`
  - **HA**: React context for efficient state management (no re-auth on navigation)
  - Global auth state (user, isAuthenticated, loading)
  - Login/logout/signup methods
  - Automatic token refresh logic (uses existing Cognito refresh tokens - zero cost)
  - Persist auth state across page reloads (localStorage)

### Phase 2: Auth Pages (3-4 hours)
- [ ] 4. Create SignupPage `/ui/src/pages/SignupPage.tsx`
  - **Enterprise**: Client-side validation BEFORE API call (reduces failed Lambda invocations)
  - Form fields: name, email, password, confirm password
  - Validation: email format (RFC 5322), password strength (8+ chars, complexity), match
  - **HA**: Graceful error handling (network failures, API errors, user-friendly messages)
  - Success → auto-login → redirect to dashboard (seamless UX)
  - Link to login page
- [ ] 5. Create LoginPage `/ui/src/pages/LoginPage.tsx`
  - **Cost**: Client validation reduces unnecessary Lambda calls
  - Form fields: email, password
  - Client-side validation (format checks before submission)
  - **Enterprise**: Proper error messages (avoid leaking user existence info)
  - Success → redirect to dashboard or intended page (deep linking support)
  - Link to signup page

### Phase 3: Protected Routes (1-2 hours)
- [ ] 6. Create ProtectedRoute wrapper `/ui/src/components/ProtectedRoute.tsx`
  - **HA**: Client-side auth check (no backend call needed for route protection)
  - Check authentication status from AuthContext (cached state)
  - Redirect to /login if not authenticated
  - **Enterprise**: Save intended destination for post-login redirect (better UX)
  - **Cost**: Zero (pure client-side routing logic)
- [ ] 7. Update routing in `/ui/src/main.tsx`
  - Add `/login` route → LoginPage (public)
  - Add `/signup` route → SignupPage (public)
  - Wrap `/dashboard` with ProtectedRoute
  - Wrap `/results/:id` with ProtectedRoute
  - **HA**: Lazy loading for code-splitting (faster initial load)

### Phase 4: Navigation Updates (1-2 hours)
- [ ] 8. Update HomePage `/ui/src/pages/HomePage.tsx`
  - Change "Get Started Free" → "Sign Up" (redirect to /signup)
  - Add "Login" button in header
  - Remove "No signup required" messaging
  - **Cost**: Zero (UI changes only)
- [ ] 9. Add header/navigation to authenticated pages
  - **HA**: Display user info from cached context (no API call)
  - Show user name/email from ID token claims
  - Add logout button (clears localStorage + context state)
  - Consistent navigation across dashboard/results
  - **Enterprise**: Responsive design for mobile/desktop

### Phase 5: Testing & Polish (1-2 hours)
- [ ] 10. Test complete user flows
  - **HA Testing**: Verify graceful degradation on network failures
  - New user signup → auto-login → dashboard
  - Existing user login → dashboard
  - Access protected route while logged out → redirect to login → return to intended page
  - Logout → return to homepage
  - Token persistence (refresh page while logged in - validates localStorage works)
- [ ] 11. Handle edge cases
  - **Enterprise**: Network errors during auth (retry with exponential backoff)
  - Invalid email/password combinations (clear error messages)
  - Session expiration (detect expired tokens, redirect to login)
  - Already logged in navigation (redirect authenticated users away from /login)
  - **HA**: Test token refresh flow (when access token expires)
- [ ] 12. Update documentation
  - Mark this iteration complete in tasks/todo.md
  - Document cost analysis (confirm zero AWS cost increase)
  - Update TECH_DEBT.md with any deferred items

---

## 📐 Technical Design

### Auth Flow
```
1. User visits homepage → sees "Sign Up" / "Login"
2. New user → /signup → creates account → auto-login → /dashboard
3. Existing user → /login → validates credentials → /dashboard
4. Protected routes check AuthContext → redirect to /login if not authenticated
5. Logout → clear tokens → redirect to homepage
```

### Data Flow (Cost-Effective & High Availability)
```
Frontend (React) → [Client Validation] → API Client (fetch) → Backend (Lambda + Cognito)
                                ↓
                         JWT tokens stored in localStorage (browser native, free)
                                ↓
                         AuthContext provides global state (React context, free)
                                ↓
                         ProtectedRoute checks auth (client-side, no API call)

Cost Impact: $0 (frontend-only changes, uses existing backend)
Availability: Inherits Cognito 99.9% + DynamoDB 99.99% SLA
```

### Enterprise-Grade Features
- **Token Management**: Industry-standard JWT (Cognito issued)
- **Secure Storage**: localStorage (HTTPS-only in production)
- **Error Handling**: Retry logic, exponential backoff, user-friendly messages
- **Input Validation**: Client-side pre-validation (reduces failed Lambda calls)
- **Session Management**: Automatic token refresh using Cognito refresh tokens
- **Security**: No passwords in client logs, generic error messages (prevent enumeration)

### File Structure
```
ui/src/
├── contexts/
│   └── AuthContext.tsx          # Global auth state
├── pages/
│   ├── HomePage.tsx             # Updated: signup/login links
│   ├── LoginPage.tsx            # NEW
│   ├── SignupPage.tsx           # NEW
│   ├── DashboardPage.tsx        # Protected route
│   └── ResultsPage.tsx          # Protected route
├── components/
│   ├── ProtectedRoute.tsx       # NEW: Auth wrapper
│   └── Header.tsx               # NEW: User menu + logout
└── utils/
    └── auth.ts                  # NEW: API client + helpers
```

### Backend Endpoints (Already Implemented)
- `POST /auth/signup` - Create new user
- `POST /auth/login` - Authenticate user, get JWT tokens

### JWT Token Management
- **Storage**: localStorage (keys: `access_token`, `id_token`, `refresh_token`)
- **Access Token**: 60 min expiry (used for API calls)
- **ID Token**: Contains user info (name, email, sub)
- **Refresh Token**: 30 days expiry (future: auto-refresh logic)

---

## ✅ Acceptance Criteria

- [ ] User can sign up with name, email, password
- [ ] User can log in with email, password
- [ ] Dashboard requires authentication
- [ ] Results page requires authentication
- [ ] Unauthenticated users redirected to /login
- [ ] After login, user redirected to intended page
- [ ] User info displayed in header/nav
- [ ] Logout clears session and redirects to homepage
- [ ] Auth state persists across page refreshes
- [ ] Error messages are clear and user-friendly
- [ ] Form validation prevents invalid submissions

---

## 🔮 Future Enhancements (Post-MVP)

Tracked in TECH_DEBT.md:
- Email verification workflow
- Password reset/forgot password
- Remember me checkbox
- Token auto-refresh logic
- Social auth (Google, GitHub)
- Profile management page
- Account deletion

---

## 📝 Backend Authentication Review (Sep 30, 2025)

### Expert Assessment
**Reviewer Role**: Senior UI/UX Designer with AWS Auth experience (Amazon, Microsoft, Google patterns)
**Overall Grade**: A- (92/100) - Production-ready, cost-effective, enterprise-grade

### ✅ Strengths
1. **Cost-Effective**: $0-3/month for first 1K users (PAY_PER_REQUEST DynamoDB, Cognito free tier)
2. **High Availability**: 99.9% SLA (Cognito) + 99.99% SLA (DynamoDB with PITR)
3. **Enterprise Security**: NIST-compliant password policy, generic error messages, JWT tokens
4. **Scalable**: Serverless architecture can handle 10M+ users without redesign
5. **Best Practices**: Matches Amazon/Google/Microsoft authentication patterns

### 🔴 Critical Gaps (Before Frontend Launch)
1. **Missing JWT Authorizer**: API Gateway still uses API keys (not user-specific)
   - **Fix**: Add Cognito User Pool Authorizer (2-3 hours, $0 cost)
   - **Impact**: Enable per-user authentication and rate limiting

2. **No Token Refresh Endpoint**: Users get kicked out after 60 min
   - **Fix**: Add `/auth/refresh` endpoint using `REFRESH_TOKEN_AUTH` (3-4 hours)
   - **Impact**: Seamless UX, no mid-session logouts

3. **Missing Request Correlation**: Hard to debug issues across services
   - **Fix**: Add request ID to all logs and response headers (1-2 hours, $0 cost)
   - **Impact**: Better observability and debugging

### 🟡 Post-MVP Improvements
- Email verification flow (2-3 hours)
- Password reset flow (2-3 hours) - IAM permissions already in place
- CloudWatch alarms for proactive monitoring ($0.50/month)
- Move to SRP authentication for zero-knowledge password (8-12 hours, deferred)

### 💰 Cost Projection
| Users | Monthly Cost | Per-User |
|-------|--------------|----------|
| 100-500 | $0 | $0 (free tier) |
| 1,000 | $3 | $0.003 |
| 10,000 | $30 | $0.003 |
| 50,000 | $150 | $0.003 |

### 🎯 Recommended Implementation Order
**Phase 1** (Must-have before launch): 6-8 hours
1. Add JWT Authorizer to API Gateway
2. Implement token refresh endpoint + frontend logic
3. Add request ID correlation

**Phase 2** (Post-launch): 4-6 hours
4. Email verification flow
5. Password reset flow
6. CloudWatch alarms

---

## 📝 Frontend Implementation Notes

### Summary of Changes
(To be filled after frontend implementation)

### Files Created
(To be listed after implementation)

### Files Modified
(To be listed after implementation)

### Testing Notes
(To be filled after testing)

---

---

## 🔴 BACKEND PRE-REQUISITES (Before Frontend)

**Goal**: Fix 3 critical backend gaps before starting frontend development

**Estimated Effort**: 6-8 hours total

---

### Task 1: Add JWT Authorizer to API Gateway (2-3 hours)

**Current Problem**: API Gateway uses API keys (shared secret, not user-specific)

**Solution**: Add Cognito User Pool Authorizer

**Files to Modify**:
- `infrastructure/modules/api_gateway/main.tf`
- `infrastructure/modules/api_gateway/variables.tf`

**Implementation Steps**:
1. Create Cognito User Pool Authorizer resource
2. Update protected endpoints:
   - `/statements` (GET)
   - `/upload` (POST)
   - `/statements/data` (GET)
   - `/statements/excel/{job_id}` (GET)
   - `/pdf/{job_id}` (GET)
   - `/configurations/banks` (GET)
3. Change `authorization = "NONE"` → `authorization = "COGNITO_USER_POOLS"`
4. Remove `api_key_required = true`
5. Keep `/auth/signup` and `/auth/login` public (no auth)

**Terraform Code**:
```hcl
# Add to api_gateway/main.tf
resource "aws_api_gateway_authorizer" "cognito" {
  name          = "${var.name_prefix}-cognito-authorizer"
  rest_api_id   = aws_api_gateway_rest_api.api.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [var.cognito_user_pool_arn]
}

# Update each protected endpoint method
resource "aws_api_gateway_method" "statements_method" {
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
  # Remove: api_key_required = true
}
```

**Cost**: $0 (included in API Gateway)

---

### Task 2: Token Refresh Endpoint (3-4 hours)

**Current Problem**: Access tokens expire after 60 min, no way to refresh without re-login

**Solution**: Add `/auth/refresh` endpoint using Cognito `REFRESH_TOKEN_AUTH` flow

**Files to Create**:
- `api/lambdas/auth_refresh/handler.py`
- `api/lambdas/auth_refresh/__init__.py`

**Files to Modify**:
- `infrastructure/modules/lambda/main.tf` (add new Lambda function)
- `infrastructure/modules/api_gateway/main.tf` (add new endpoint)

**Lambda Handler Code**:
```python
# api/lambdas/auth_refresh/handler.py
import json
import os
import boto3

cognito_client = boto3.client('cognito-idp')
CLIENT_ID = os.environ['COGNITO_CLIENT_ID']

def lambda_handler(event, context):
    """
    Refresh access token using refresh token

    POST /auth/refresh
    {
        "refresh_token": "eyJ..."
    }

    Returns:
    {
        "access_token": "eyJ...",
        "id_token": "eyJ...",
        "expires_in": 3600
    }
    """
    body = json.loads(event.get('body', '{}'))
    refresh_token = body.get('refresh_token')

    if not refresh_token:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'refresh_token required'})
        }

    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )

        auth_result = response['AuthenticationResult']

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'success': True,
                'data': {
                    'access_token': auth_result['AccessToken'],
                    'id_token': auth_result['IdToken'],
                    'expires_in': auth_result.get('ExpiresIn', 3600)
                }
            })
        }

    except cognito_client.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'body': json.dumps({
                'success': False,
                'error': {
                    'code': 'INVALID_TOKEN',
                    'message': 'Refresh token expired or invalid'
                }
            })
        }
```

**API Gateway Setup**:
```hcl
# Add to api_gateway/main.tf
resource "aws_api_gateway_resource" "auth_refresh" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "refresh"
}

resource "aws_api_gateway_method" "auth_refresh_method" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.auth_refresh.id
  http_method   = "POST"
  authorization = "NONE"  # Public endpoint
}
```

**Cost**: ~$0.0000055/refresh (negligible)

---

### Task 3: Request ID Correlation (1-2 hours)

**Current Problem**: Can't trace requests across frontend → API Gateway → Lambda → DynamoDB

**Solution**: Add `X-Request-ID` to all logs and responses

**Files to Modify**:
- `api/lambdas/auth_signup/handler.py`
- `api/lambdas/auth_login/handler.py`
- `api/lambdas/auth_refresh/handler.py` (new)

**Code Pattern**:
```python
def lambda_handler(event, context):
    # Extract or generate request ID
    request_context = event.get('requestContext', {})
    request_id = request_context.get('requestId') or str(uuid.uuid4())

    # Add to all log statements
    print(f"[{request_id}] Login attempt for email: {email}")

    # Return in response headers
    return {
        'statusCode': 200,
        'headers': {
            'X-Request-ID': request_id,
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Expose-Headers': 'X-Request-ID'  # Allow frontend to read
        },
        'body': json.dumps({...})
    }
```

**Frontend Usage**:
```typescript
// Frontend can use this for support tickets
const response = await fetch('/auth/login', {...});
const requestId = response.headers.get('X-Request-ID');
console.error('Login failed, Request ID:', requestId);
```

**Cost**: $0 (just logging format change)

---

## ✅ Acceptance Criteria (All 3 Tasks)

- [ ] Protected endpoints return 401 without valid JWT token
- [ ] Protected endpoints accept JWT token in `Authorization: Bearer <token>` header
- [ ] `/auth/refresh` endpoint returns new access token given valid refresh token
- [ ] Expired refresh tokens return 401 error
- [ ] All Lambda logs include `[request_id]` prefix
- [ ] All responses include `X-Request-ID` header
- [ ] CORS allows frontend to read `X-Request-ID` header
- [ ] Terraform apply succeeds without errors
- [ ] All endpoints tested with real Cognito tokens

---

## 🧪 Testing Plan

### Test 1: JWT Authorization
```bash
# Get token from login
TOKEN=$(curl -X POST https://api.example.com/auth/login \
  -d '{"email":"test@example.com","password":"Test123!"}' \
  | jq -r '.data.access_token')

# Test protected endpoint WITHOUT token (should fail)
curl -X GET https://api.example.com/statements
# Expected: 401 Unauthorized

# Test protected endpoint WITH token (should succeed)
curl -X GET https://api.example.com/statements \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK
```

### Test 2: Token Refresh
```bash
# Get refresh token from login
REFRESH_TOKEN=$(curl -X POST https://api.example.com/auth/login \
  -d '{"email":"test@example.com","password":"Test123!"}' \
  | jq -r '.data.refresh_token')

# Refresh access token
curl -X POST https://api.example.com/auth/refresh \
  -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}"
# Expected: New access_token and id_token
```

### Test 3: Request ID
```bash
# Make any request and check response headers
curl -v https://api.example.com/auth/login \
  -d '{"email":"test@example.com","password":"Test123!"}'
# Expected: X-Request-ID header in response

# Check CloudWatch logs
# Expected: [<request-id>] prefix in all log lines for that request
```

---

## 📦 Deployment Steps

1. Create new files:
   ```bash
   mkdir -p api/lambdas/auth_refresh
   touch api/lambdas/auth_refresh/__init__.py
   # Create handler.py with code above
   ```

2. Build Lambda packages:
   ```bash
   cd infrastructure
   ./scripts/build-functions.sh
   ```

3. Update Terraform:
   ```bash
   terraform plan -var-file="local.tfvars"
   # Review changes (new Lambda, API Gateway authorizer, etc.)

   terraform apply -var-file="local.tfvars"
   ```

4. Test endpoints (use testing plan above)

5. Update documentation

---

**Next Step**: Begin Task 1 - Add JWT Authorizer to API Gateway
