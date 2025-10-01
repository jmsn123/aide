"""
Token Refresh Lambda Handler
Refreshes access and ID tokens using Cognito refresh token

Design Pattern: Cognito REFRESH_TOKEN_AUTH Flow
- Client sends refresh_token received during login
- Cognito validates refresh token and issues new access_token + id_token
- No password required (refresh token is proof of previous authentication)
- Refresh tokens expire after 30 days (configured in Cognito)
"""

import json
import os
import boto3
import uuid

# AWS clients
cognito_client = boto3.client('cognito-idp')

# Environment variables
CLIENT_ID = os.environ['COGNITO_CLIENT_ID']

# Configuration
MAX_REFRESH_TOKEN_LENGTH = 2048  # Refresh tokens are longer than access tokens


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
        'Access-Control-Expose-Headers': 'X-Request-ID'  # Allow frontend to read request ID
    }

    if request_id:
        headers['X-Request-ID'] = request_id

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }


def lambda_handler(event, context):
    """
    Handle token refresh with Cognito

    Request body:
    {
        "refresh_token": "eyJ..."
    }

    Response (success):
    {
        "success": true,
        "data": {
            "access_token": "eyJ...",
            "id_token": "eyJ...",
            "expires_in": 3600,
            "token_type": "Bearer"
        },
        "message": "Token refreshed successfully"
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

    print(f"[{request_id}] Token refresh request received")

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
            }, request_id)

        # Parse JSON body
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"[{request_id}] JSON parsing error: {str(e)}")
                return api_response(400, {
                    'success': False,
                    'error': {
                        'code': 'INVALID_JSON',
                        'message': 'Request body must be valid JSON'
                    }
                }, request_id)
        elif not isinstance(body, dict):
            print(f"[{request_id}] Invalid body type: {type(body)}")
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'INVALID_BODY_TYPE',
                    'message': 'Request body must be a JSON object'
                }
            }, request_id)

        refresh_token = body.get('refresh_token', '').strip()

        # Validate required fields
        if not refresh_token:
            print(f"[{request_id}] Missing refresh_token")
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'MISSING_REFRESH_TOKEN',
                    'message': 'Refresh token is required'
                }
            }, request_id)

        # Validate token length (prevent abuse/DoS)
        if len(refresh_token) > MAX_REFRESH_TOKEN_LENGTH:
            print(f"[{request_id}] Refresh token too long: {len(refresh_token)} chars")
            return api_response(400, {
                'success': False,
                'error': {
                    'code': 'TOKEN_TOO_LONG',
                    'message': f'Refresh token too long (max {MAX_REFRESH_TOKEN_LENGTH} characters)'
                }
            }, request_id)

        # Refresh tokens with Cognito
        print(f"[{request_id}] Initiating token refresh with Cognito")

        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )

        # Extract new tokens
        auth_result = response.get('AuthenticationResult')
        if not auth_result:
            # Handle unexpected response (shouldn't happen in REFRESH_TOKEN_AUTH)
            print(f"[{request_id}] No AuthenticationResult in Cognito response")
            return api_response(500, {
                'success': False,
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': 'Failed to refresh token'
                }
            }, request_id)

        access_token = auth_result.get('AccessToken')
        id_token = auth_result.get('IdToken')
        expires_in = auth_result.get('ExpiresIn', 3600)

        # Note: Cognito does NOT return a new refresh_token in REFRESH_TOKEN_AUTH response
        # Client should continue using the same refresh_token until it expires (30 days)

        print(f"[{request_id}] Token refresh successful")

        # Return success response with new tokens
        return api_response(200, {
            'success': True,
            'data': {
                'access_token': access_token,
                'id_token': id_token,
                'expires_in': expires_in,
                'token_type': 'Bearer'
            },
            'message': 'Token refreshed successfully'
        }, request_id)

    except cognito_client.exceptions.NotAuthorizedException as e:
        # Invalid or expired refresh token
        print(f"[{request_id}] Invalid refresh token: {str(e)}")
        return api_response(401, {
            'success': False,
            'error': {
                'code': 'INVALID_TOKEN',
                'message': 'Refresh token is invalid or expired. Please login again.'
            }
        }, request_id)

    except cognito_client.exceptions.TooManyRequestsException as e:
        # Rate limit exceeded
        print(f"[{request_id}] Rate limit exceeded: {str(e)}")
        return api_response(429, {
            'success': False,
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Too many requests. Please try again later.'
            }
        }, request_id)

    except Exception as e:
        print(f"[{request_id}] Error during token refresh: {str(e)}")
        import traceback
        traceback.print_exc()

        return api_response(500, {
            'success': False,
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Internal server error during token refresh'
            }
        }, request_id)
