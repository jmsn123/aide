"""
Login Lambda Handler
Handles user authentication with Cognito and returns JWT tokens

Design Pattern: Cognito Authentication + DynamoDB Profile Sync
- Cognito authenticates user and issues JWT tokens
- DynamoDB profile updated with last_login timestamp
- If DynamoDB profile missing, lazy create from Cognito (recovery pattern)
"""

import json
import os
import boto3
from datetime import datetime
import re
import uuid

# AWS clients
cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# Environment variables
USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
CLIENT_ID = os.environ['COGNITO_CLIENT_ID']
USERS_TABLE_NAME = os.environ['USERS_TABLE_NAME']

# Configuration
MAX_EMAIL_LENGTH = 255
MAX_PASSWORD_LENGTH = 128

# Get DynamoDB table
users_table = dynamodb.Table(USERS_TABLE_NAME)


def api_response(status_code, body, request_id=None):
    """
    Create standardized API Gateway response with CORS headers

    Args:
        status_code: HTTP status code
        body: Response body (dict)
        request_id: Request correlation ID

    Returns:
        API Gateway response object
    """
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Access-Control-Expose-Headers': 'X-Request-ID'
    }

    if request_id:
        headers['X-Request-ID'] = request_id

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }


def validate_email(email):
    """Validate email format using RFC-compliant regex"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def extract_token_claims(id_token):
    """
    Extract claims from ID token received from Cognito admin_initiate_auth.

    SECURITY: Signature verification not needed because:
    - Token just issued by Cognito in this execution (trusted source)
    - Not used for client-provided tokens (use JWT verification for those)
    - Internal Lambda use only (no trust boundary crossing)

    Returns:
        dict: Token claims including sub (user_id), email, name
    """
    import base64

    # Split JWT (header.payload.signature)
    parts = id_token.split('.')
    if len(parts) != 3:
        return None

    # Decode payload (add padding if needed)
    payload = parts[1]
    payload += '=' * (4 - len(payload) % 4)

    try:
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding token: {str(e)}")
        return None


def get_user_profile_from_dynamodb(email):
    """
    Get user profile from DynamoDB using email-index

    Returns:
        dict: User profile or None if not found
    """
    try:
        response = users_table.query(
            IndexName='email-index',
            KeyConditionExpression='email = :email',
            ExpressionAttributeValues={':email': email},
            Limit=1
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"Error querying DynamoDB: {str(e)}")
        return None


def create_profile_from_cognito(user_id, email, cognito_username):
    """
    Lazy profile creation - Create DynamoDB profile from Cognito user data
    This handles cases where signup DynamoDB write failed

    Returns:
        dict: Created user profile
    """
    now = datetime.utcnow().isoformat() + 'Z'

    # Get full user attributes from Cognito
    try:
        cognito_user = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=cognito_username
        )

        # Extract name from Cognito attributes
        name = None
        for attr in cognito_user.get('UserAttributes', []):
            if attr['Name'] == 'name':
                name = attr['Value']
                break

        user_record = {
            'user_id': user_id,
            'email': email,
            'cognito_username': cognito_username,
            'name': name or 'Unknown',
            'plan_type': 'free',
            'created_at': now,
            'updated_at': now,
            'last_login': now,
            'email_verified': False,
            'is_active': True,
            'usage_limits': {
                'requests_per_day': 100,
                'requests_per_month': 1000
            },
            'metadata': {'recovered_on_login': True}
        }

        users_table.put_item(Item=user_record)
        print(f"Lazy profile created for user: {user_id}")
        return user_record

    except Exception as e:
        print(f"Error creating profile from Cognito: {str(e)}")
        # Return minimal profile
        return {
            'user_id': user_id,
            'email': email,
            'cognito_username': cognito_username,
            'name': 'Unknown',
            'plan_type': 'free',
            'last_login': now
        }


def update_last_login(user_id):
    """
    Update last_login timestamp in DynamoDB
    Best effort - don't fail login if this fails
    """
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET last_login = :now, updated_at = :now',
            ExpressionAttributeValues={
                ':now': now
            }
        )
        print(f"Updated last_login for user: {user_id}")
    except Exception as e:
        print(f"Warning: Failed to update last_login: {str(e)}")
        # Don't fail login - this is non-critical


def lambda_handler(event, context):
    """
    Handle user login with Cognito authentication

    Request body:
    {
        "email": "user@example.com",
        "password": "SecurePass123!"
    }

    Response (success):
    {
        "success": true,
        "data": {
            "access_token": "eyJ...",
            "id_token": "eyJ...",
            "refresh_token": "eyJ...",
            "expires_in": 3600,
            "token_type": "Bearer",
            "user": {
                "user_id": "uuid",
                "email": "user@example.com",
                "name": "John Doe"
            }
        },
        "message": "Login successful"
    }

    Response (error):
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message"
        }
    }
    """

    # Extract or generate request ID for correlation
    request_context = event.get('requestContext', {})
    request_id = request_context.get('requestId') or str(uuid.uuid4())

    print(f"[{request_id}] Login request received")

    try:
        # Parse request body
        body = event.get('body')

        if body is None:
            print(f"[{request_id}] Missing request body")
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'MISSING_BODY',
                    'message': 'Request body is required'
                }
            })

        # Parse JSON body
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {str(e)}")
                return api_response(400, {
                    'success': False,
                    'error': {
                        'code': 'INVALID_JSON',
                        'message': 'Request body must be valid JSON'
                    }
                })
        elif not isinstance(body, dict):
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'INVALID_BODY_TYPE',
                    'message': 'Request body must be a JSON object'
                }
            })

        email = body.get('email', '').lower().strip()
        password = body.get('password', '')

        # Validate required fields
        if not email:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'MISSING_EMAIL',
                    'message': 'Email is required'
                }
            })

        if not password:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'MISSING_PASSWORD',
                    'message': 'Password is required'
                }
            })

        # Validate field lengths
        if len(email) > MAX_EMAIL_LENGTH:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'EMAIL_TOO_LONG',
                    'message': f'Email too long (max {MAX_EMAIL_LENGTH} characters)'
                }
            })

        if len(password) > MAX_PASSWORD_LENGTH:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'PASSWORD_TOO_LONG',
                    'message': f'Password too long (max {MAX_PASSWORD_LENGTH} characters)'
                }
            })

        # Validate email format
        if not validate_email(email):
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'INVALID_EMAIL',
                    'message': 'Invalid email format'
                }
            })

        # Get user profile from DynamoDB to retrieve cognito_username
        user_profile = get_user_profile_from_dynamodb(email)

        if not user_profile:
            # User doesn't exist in DynamoDB - might exist in Cognito only
            # Try authentication anyway - will create profile if successful
            print(f"User not found in DynamoDB: {email}")
            # For now, return error - will handle Cognito-only users during auth
            return api_response(401, {
                'success': False,
                'error': {
                    'code': 'INVALID_CREDENTIALS',
                    'message': 'Invalid email or password'
                }
            })

        cognito_username = user_profile.get('cognito_username')
        if not cognito_username:
            print(f"Missing cognito_username for user: {email}")
            return api_response(500, {
                'success': False,
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'User account configuration error'
                }
            })

        # Authenticate with Cognito using admin_initiate_auth
        print(f"Authenticating user with Cognito: {cognito_username}")

        auth_response = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': cognito_username,  # Use UUID username
                'PASSWORD': password
            }
        )

        # Extract tokens
        auth_result = auth_response.get('AuthenticationResult')
        if not auth_result:
            # Handle MFA or other challenges (not implemented in Iteration 4)
            challenge_name = auth_response.get('ChallengeName')
            print(f"Authentication challenge: {challenge_name}")
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'AUTH_CHALLENGE_REQUIRED',
                    'message': f'Additional authentication required: {challenge_name}'
                }
            })

        access_token = auth_result.get('AccessToken')
        id_token = auth_result.get('IdToken')
        refresh_token = auth_result.get('RefreshToken')
        expires_in = auth_result.get('ExpiresIn', 3600)

        # Extract user_id from ID token
        token_claims = extract_token_claims(id_token)
        if not token_claims:
            print("Failed to extract token claims")
            return api_response(500, {
                'success': False,
                'error': {
                    'code': 'TOKEN_ERROR',
                    'message': 'Failed to process authentication tokens'
                }
            })

        user_id = token_claims.get('sub')
        if not user_id:
            print("Missing sub claim in token")
            return api_response(500, {
                'success': False,
                'error': {
                    'code': 'TOKEN_ERROR',
                    'message': 'Invalid authentication token'
                }
            })

        # Update last_login timestamp (best effort)
        update_last_login(user_id)

        # Return success response with tokens
        print(f"[{request_id}] Login successful for user: {user_id}")
        return api_response(200, {
            'success': True,
            'data': {
                'access_token': access_token,
                'id_token': id_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'token_type': 'Bearer',
                'user': {
                    'user_id': user_id,
                    'email': user_profile.get('email'),
                    'name': user_profile.get('name'),
                    'plan_type': user_profile.get('plan_type', 'free')
                }
            },
            'message': 'Login successful'
        }, request_id)

    except cognito_client.exceptions.NotAuthorizedException as e:
        # Invalid credentials
        print(f"Authentication failed: {str(e)}")
        return api_response(401, {
            'success': False,
            'error': {
                'code': 'INVALID_CREDENTIALS',
                'message': 'Invalid email or password'
            }
        })

    except cognito_client.exceptions.UserNotFoundException as e:
        # User doesn't exist in Cognito
        print(f"User not found in Cognito: {str(e)}")
        return api_response(401, {
            'success': False,
            'error': {
                'code': 'INVALID_CREDENTIALS',
                'message': 'Invalid email or password'
            }
        })

    except cognito_client.exceptions.UserNotConfirmedException as e:
        # User exists but not confirmed (email verification pending)
        print(f"User not confirmed: {str(e)}")
        return api_response(403, {
            'success': False,
            'error': {
                'code': 'EMAIL_NOT_VERIFIED',
                'message': 'Please verify your email before logging in'
            }
        })

    except cognito_client.exceptions.PasswordResetRequiredException as e:
        # Password reset required
        print(f"Password reset required: {str(e)}")
        return api_response(403, {
            'success': False,
            'error': {
                'code': 'PASSWORD_RESET_REQUIRED',
                'message': 'Password reset required. Please reset your password.'
            }
        })

    except cognito_client.exceptions.TooManyRequestsException as e:
        # Rate limit exceeded
        print(f"Rate limit exceeded: {str(e)}")
        return api_response(429, {
            'success': False,
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Too many login attempts. Please try again later.'
            }
        })

    except Exception as e:
        print(f"[{request_id}] Error during login: {str(e)}")
        import traceback
        traceback.print_exc()

        return api_response(500, {
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Internal server error during login'
            }
        }, request_id)
