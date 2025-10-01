"""
Authentication utilities for Lambda functions
Handles JWT claim extraction and user authorization
"""

import json
from typing import Optional, Dict, Any


def extract_user_from_jwt(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user_id (sub claim) from JWT token validated by API Gateway Cognito Authorizer

    When API Gateway validates a JWT token using Cognito User Pool Authorizer,
    it automatically populates the requestContext.authorizer.claims with the token claims.

    Args:
        event: API Gateway event object

    Returns:
        str: User ID (Cognito sub claim) if found, None otherwise

    Example event structure after JWT validation:
    {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "email": "user@example.com",
                    "cognito:username": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "email_verified": "true",
                    ...
                }
            }
        }
    }
    """
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})

        # Extract user_id from 'sub' claim (standard JWT claim for subject/user ID)
        user_id = claims.get('sub')

        if user_id:
            print(f"Extracted user_id from JWT: {user_id}")
            return user_id
        else:
            print("Warning: No 'sub' claim found in JWT")
            return None

    except Exception as e:
        print(f"Error extracting user from JWT: {str(e)}")
        return None


def extract_user_email_from_jwt(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract user email from JWT token validated by API Gateway

    Args:
        event: API Gateway event object

    Returns:
        str: User email if found, None otherwise
    """
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})

        email = claims.get('email')

        if email:
            print(f"Extracted email from JWT: {email}")
            return email
        else:
            print("Warning: No 'email' claim found in JWT")
            return None

    except Exception as e:
        print(f"Error extracting email from JWT: {str(e)}")
        return None


def get_jwt_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get all JWT claims from validated token

    Args:
        event: API Gateway event object

    Returns:
        dict: All JWT claims or empty dict if not found
    """
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})

        return claims

    except Exception as e:
        print(f"Error extracting JWT claims: {str(e)}")
        return {}


def unauthorized_response(message: str = "Unauthorized") -> Dict[str, Any]:
    """
    Create standardized 401 Unauthorized response

    Args:
        message: Error message to return

    Returns:
        API Gateway response object
    """
    return {
        'statusCode': 401,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps({
            'success': False,
            'error': {
                'code': 'UNAUTHORIZED',
                'message': message
            }
        })
    }


def forbidden_response(message: str = "Access denied") -> Dict[str, Any]:
    """
    Create standardized 403 Forbidden response

    Args:
        message: Error message to return

    Returns:
        API Gateway response object
    """
    return {
        'statusCode': 403,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        },
        'body': json.dumps({
            'success': False,
            'error': {
                'code': 'FORBIDDEN',
                'message': message
            }
        })
    }
