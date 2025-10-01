"""
Signup Lambda Handler
Handles user registration with Cognito and DynamoDB

Design Pattern: Cognito as Source of Truth
- Cognito handles user authentication and uniqueness
- DynamoDB stores user metadata and profile information
- If DynamoDB fails, user can still authenticate (lazy profile creation on first login)
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
MAX_NAME_LENGTH = 100
MAX_PASSWORD_LENGTH = 128

# Get DynamoDB table
users_table = dynamodb.Table(USERS_TABLE_NAME)


def api_response(status_code, body):
    """
    Create standardized API Gateway response with CORS headers

    Args:
        status_code: HTTP status code
        body: Response body (dict)

    Returns:
        API Gateway response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body)
    }


def validate_email(email):
    """Validate email format using RFC-compliant regex"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_password(password):
    """
    Validate password meets security requirements:
    - At least 8 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains number
    - Contains special character

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain an uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain a lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain a number"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain a special character"

    return True, "Password valid"


def extract_user_sub(cognito_response):
    """Extract user sub (UUID) from Cognito response"""
    for attr in cognito_response['User']['Attributes']:
        if attr['Name'] == 'sub':
            return attr['Value']
    return None


def lambda_handler(event, context):
    """
    Handle user signup with Cognito and DynamoDB

    Request body:
    {
        "email": "user@example.com",
        "password": "SecurePass123!",
        "name": "John Doe"
    }

    Response (success):
    {
        "success": true,
        "data": {
            "user_id": "uuid",
            "email": "user@example.com",
            "name": "John Doe",
            "email_verified": false
        },
        "message": "User created successfully"
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

    print(f"Signup request received: {json.dumps(event, default=str)}")

    try:
        # Parse request body with explicit JSON validation
        body = event.get('body')

        if body is None:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'MISSING_BODY',
                    'message': 'Request body is required'
                }
            })

        # Parse JSON body if string, otherwise use as-is (for Lambda test events)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {str(e)}")
                print(f"Raw body: {body}")
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
        name = body.get('name', '').strip()

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

        if not name:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'MISSING_NAME',
                    'message': 'Name is required'
                }
            })

        # Validate field lengths (prevent abuse/DoS)
        if len(email) > MAX_EMAIL_LENGTH:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'EMAIL_TOO_LONG',
                    'message': f'Email too long (max {MAX_EMAIL_LENGTH} characters)'
                }
            })

        if len(name) > MAX_NAME_LENGTH:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'NAME_TOO_LONG',
                    'message': f'Name too long (max {MAX_NAME_LENGTH} characters)'
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

        # Validate password strength
        password_valid, password_message = validate_password(password)
        if not password_valid:
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'WEAK_PASSWORD',
                    'message': password_message
                }
            })

        # Check for duplicate email in DynamoDB (Cognito alias doesn't enforce uniqueness)
        # This is necessary because Cognito alias_attributes don't prevent duplicate emails
        try:
            existing_users = users_table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email},
                Limit=1
            )
            if existing_users.get('Items'):
                print(f"Email already exists in DynamoDB: {email}")
                return api_response(409, {
                    'success': False,
                    'error': {
                        'code': 'USER_EXISTS',
                        'message': 'User with this email already exists'
                    }
                })
        except Exception as db_check_error:
            # If DynamoDB check fails, log but continue (Cognito will be source of truth)
            print(f"DynamoDB check failed: {str(db_check_error)}")

        # Create user in Cognito (source of truth for authentication)
        # Note: Cognito User Pool is configured with email as alias, so username must be UUID
        print(f"Creating Cognito user for: {email}")

        # Generate unique username (Cognito requirement when email is alias)
        username = str(uuid.uuid4())

        cognito_response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,  # Use UUID as username (email is alias)
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'false'},  # TODO: Iteration 5 - Add email verification
                {'Name': 'name', 'Value': name}
            ],
            MessageAction='SUPPRESS'  # Don't send welcome email
        )

        user_sub = extract_user_sub(cognito_response)
        if not user_sub:
            raise Exception("Failed to get user sub from Cognito")

        print(f"Cognito user created with sub: {user_sub}, username: {username}")

        # Set permanent password (skip temporary password flow)
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username,  # Use UUID username, not email
            Password=password,
            Permanent=True
        )

        print("Permanent password set")

        # Authenticate the newly created user to get JWT tokens
        # This provides seamless signup -> login flow (Netflix/Google pattern)
        print(f"Authenticating newly created user: {username}")

        try:
            auth_response = cognito_client.admin_initiate_auth(
                UserPoolId=USER_POOL_ID,
                ClientId=CLIENT_ID,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,  # Use UUID username
                    'PASSWORD': password
                }
            )

            # Extract tokens
            auth_result = auth_response.get('AuthenticationResult')
            if not auth_result:
                # Unlikely, but handle gracefully
                print("WARNING: Failed to get authentication result after signup")
                # Continue with DynamoDB creation - user can still login manually
                access_token = None
                id_token = None
                refresh_token = None
                expires_in = None
            else:
                access_token = auth_result.get('AccessToken')
                id_token = auth_result.get('IdToken')
                refresh_token = auth_result.get('RefreshToken')
                expires_in = auth_result.get('ExpiresIn', 3600)

                # SECURITY: Validate token expiry per NIST guidelines
                # NIST SP 800-63B: Session tokens should expire within 12 hours
                MIN_TOKEN_EXPIRY = 300    # 5 minutes (minimum for UX)
                MAX_TOKEN_EXPIRY = 43200  # 12 hours (NIST recommendation)

                if expires_in < MIN_TOKEN_EXPIRY:
                    print(f"SECURITY_CRITICAL: Token expiry {expires_in}s below minimum {MIN_TOKEN_EXPIRY}s")
                    print(f"Action required: Update Cognito User Pool token settings")
                elif expires_in > MAX_TOKEN_EXPIRY:
                    print(f"SECURITY_CRITICAL: Token expiry {expires_in}s exceeds NIST limit {MAX_TOKEN_EXPIRY}s")
                    print(f"Action required: Update Cognito User Pool settings immediately")

                # Return ACTUAL expiry from Cognito (do not modify)
                print(f"Authentication successful - tokens generated for: {user_sub}")
                print(f"Token expiry: {expires_in}s ({expires_in/3600:.1f} hours)")

        except cognito_client.exceptions.NotAuthorizedException as e:
            # SECURITY: Authentication denied for newly created user (should not happen)
            # OWASP A07: Monitor for authentication anomalies
            print(f"SECURITY_ALERT: NotAuthorizedException after signup for user {user_sub}")
            print(f"Error class: {e.__class__.__name__}")
            access_token = None
            id_token = None
            refresh_token = None
            expires_in = None

        except cognito_client.exceptions.InvalidPasswordException as e:
            # SECURITY: Password validation failed (should be caught earlier)
            print(f"SECURITY_WARNING: InvalidPasswordException after signup for user {user_sub}")
            print(f"Error class: {e.__class__.__name__}")
            access_token = None
            id_token = None
            refresh_token = None
            expires_in = None

        except cognito_client.exceptions.TooManyRequestsException as e:
            # SECURITY: Rate limit exceeded - possible abuse/attack
            # CIS AWS 3.1: Monitor for unauthorized API calls
            print(f"SECURITY_ALERT: TooManyRequestsException during signup auth for user {user_sub}")
            print(f"Possible rate limit attack detected")
            access_token = None
            id_token = None
            refresh_token = None
            expires_in = None

        except cognito_client.exceptions.UserNotFoundException as e:
            # SECURITY: User not found immediately after creation (critical error)
            print(f"SECURITY_ALERT: UserNotFoundException after signup for user {user_sub}")
            print(f"Data consistency issue - user created but not found")
            access_token = None
            id_token = None
            refresh_token = None
            expires_in = None

        except Exception as unexpected_error:
            # SECURITY: Unexpected error - log for security analysis
            # NIST CSF DE.AE-3: Analyze detected events
            print(f"SECURITY_ALERT: Unexpected auth failure after signup for user {user_sub}")
            print(f"Error type: {unexpected_error.__class__.__name__}")
            # Do not log full error message (may contain sensitive data)
            import traceback
            traceback.print_exc()
            access_token = None
            id_token = None
            refresh_token = None
            expires_in = None

        # Create user record in DynamoDB (best effort - can be recovered)
        now = datetime.utcnow().isoformat() + 'Z'

        # TODO: Iteration 6 - Move usage limits to environment variables or config table
        user_record = {
            'user_id': user_sub,
            'email': email,
            'cognito_username': username,  # Store UUID username for future Cognito operations
            'name': name,
            'plan_type': 'free',  # Default plan
            'created_at': now,
            'updated_at': now,
            'last_login': None,
            'email_verified': False,
            'is_active': True,
            'usage_limits': {
                'requests_per_day': 100,
                'requests_per_month': 1000
            },
            'metadata': {}
        }

        try:
            users_table.put_item(Item=user_record)
            print(f"User record created in DynamoDB: {user_sub}")
        except Exception as db_error:
            # DynamoDB failure is not critical - Cognito user exists and can authenticate
            # Recovery: Create DynamoDB record on first login (lazy initialization)
            print(f"WARNING: Cognito user created but DynamoDB failed: {user_sub}")
            print(f"DynamoDB error: {str(db_error)}")
            # Continue - don't fail the signup

        # Return success response with JWT tokens (if authentication succeeded)
        response_data = {
            'user': {
                'user_id': user_sub,
                'email': email,
                'name': name,
                'email_verified': False
            }
        }

        # Include JWT tokens if authentication succeeded
        if access_token and id_token and refresh_token:
            response_data.update({
                'access_token': access_token,
                'id_token': id_token,
                'refresh_token': refresh_token,
                'expires_in': expires_in,
                'token_type': 'Bearer'
            })
            message = 'User created and authenticated successfully'
        else:
            # Fallback: User created but not authenticated (can login manually)
            message = 'User created successfully. Please login to continue.'

        return api_response(201, {
            'success': True,
            'data': response_data,
            'message': message
        })

    except cognito_client.exceptions.UsernameExistsException:
        # Cognito enforces uniqueness atomically - no race condition
        print(f"User already exists in Cognito (username): {email}")
        return api_response(409, {
            'success': False,
            'error': {
                'code': 'USER_EXISTS',
                'message': 'User with this email already exists'
            }
        })

    except cognito_client.exceptions.AliasExistsException:
        # Email alias already exists (Cognito enforces email uniqueness)
        print(f"User already exists in Cognito (email alias): {email}")
        return api_response(409, {
            'success': False,
            'error': {
                'code': 'USER_EXISTS',
                'message': 'User with this email already exists'
            }
        })

    except cognito_client.exceptions.InvalidPasswordException as e:
        print(f"Cognito rejected password: {str(e)}")
        return api_response(400, {
            'success': False,
            'error': {
                'code': 'INVALID_PASSWORD',
                'message': f'Password does not meet requirements: {str(e)}'
            }
        })

    except Exception as e:
        print(f"Error during signup: {str(e)}")
        import traceback
        traceback.print_exc()

        return api_response(500, {
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Internal server error during signup'
            }
        })
