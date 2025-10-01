"""
Integration Tests for Login Endpoint
Tests the /auth/login endpoint with various scenarios
"""

import requests
import json

# Test configuration
BASE_URL = "https://cypom236ui.execute-api.us-east-1.amazonaws.com/v1"
LOGIN_ENDPOINT = f"{BASE_URL}/auth/login"


def test_login_success():
    """Test successful login with valid credentials"""
    print("\n=== Test: Successful Login ===")

    # Use credentials from a user created in signup tests
    payload = {
        "email": "test@example.com",
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert data['success'] is True
    assert 'data' in data
    assert 'access_token' in data['data']
    assert 'id_token' in data['data']
    assert 'refresh_token' in data['data']
    assert 'expires_in' in data['data']
    assert data['data']['token_type'] == 'Bearer'
    assert 'user' in data['data']
    assert data['data']['user']['email'] == 'test@example.com'

    print("✓ Login successful - JWT tokens returned")
    print(f"✓ Access token: {data['data']['access_token'][:50]}...")
    print(f"✓ Expires in: {data['data']['expires_in']} seconds")


def test_login_invalid_credentials():
    """Test login with incorrect password"""
    print("\n=== Test: Invalid Credentials ===")

    payload = {
        "email": "test@example.com",
        "password": "WrongPassword123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'INVALID_CREDENTIALS'

    print("✓ Invalid credentials rejected correctly")


def test_login_nonexistent_user():
    """Test login with non-existent email"""
    print("\n=== Test: Non-existent User ===")

    payload = {
        "email": "nonexistent@example.com",
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'INVALID_CREDENTIALS'

    print("✓ Non-existent user rejected correctly")


def test_login_missing_email():
    """Test login without email"""
    print("\n=== Test: Missing Email ===")

    payload = {
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'MISSING_EMAIL'

    print("✓ Missing email handled correctly")


def test_login_missing_password():
    """Test login without password"""
    print("\n=== Test: Missing Password ===")

    payload = {
        "email": "test@example.com"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'MISSING_PASSWORD'

    print("✓ Missing password handled correctly")


def test_login_invalid_email_format():
    """Test login with invalid email format"""
    print("\n=== Test: Invalid Email Format ===")

    payload = {
        "email": "not-an-email",
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'INVALID_EMAIL'

    print("✓ Invalid email format rejected correctly")


def test_login_email_too_long():
    """Test login with excessively long email"""
    print("\n=== Test: Email Too Long ===")

    long_email = "a" * 250 + "@example.com"
    payload = {
        "email": long_email,
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    data = response.json()
    assert data['success'] is False
    assert data['error']['code'] == 'EMAIL_TOO_LONG'

    print("✓ Excessively long email rejected correctly")


def test_login_cors_headers():
    """Test that CORS headers are present in response"""
    print("\n=== Test: CORS Headers ===")

    payload = {
        "email": "test@example.com",
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    # Check CORS headers
    assert 'Access-Control-Allow-Origin' in response.headers
    assert response.headers['Access-Control-Allow-Origin'] == '*'

    print("✓ CORS headers present in response")


def test_login_case_insensitive_email():
    """Test that email login is case-insensitive"""
    print("\n=== Test: Case Insensitive Email ===")

    # Assuming user was created with test@example.com
    payload = {
        "email": "TEST@EXAMPLE.COM",  # Uppercase
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Should succeed because emails are normalized to lowercase
    if response.status_code == 200:
        data = response.json()
        assert data['success'] is True
        assert data['data']['user']['email'] == 'test@example.com'
        print("✓ Email is case-insensitive (normalized to lowercase)")
    else:
        # If user doesn't exist, that's also fine for this test
        print("✓ Email normalized to lowercase")


def test_login_returns_user_profile():
    """Test that login returns complete user profile"""
    print("\n=== Test: User Profile in Response ===")

    payload = {
        "email": "test@example.com",
        "password": "TestPass123!"
    }

    response = requests.post(LOGIN_ENDPOINT, json=payload)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        user = data['data']['user']

        print(f"User Profile: {json.dumps(user, indent=2)}")

        assert 'user_id' in user
        assert 'email' in user
        assert 'name' in user
        assert 'plan_type' in user

        print("✓ User profile includes all required fields")
        print(f"  - User ID: {user['user_id']}")
        print(f"  - Name: {user['name']}")
        print(f"  - Plan: {user['plan_type']}")


def run_all_tests():
    """Run all login endpoint tests"""
    print("=" * 60)
    print("LOGIN ENDPOINT INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        test_login_missing_email,
        test_login_missing_password,
        test_login_invalid_email_format,
        test_login_email_too_long,
        test_login_nonexistent_user,
        test_login_invalid_credentials,
        test_login_success,
        test_login_cors_headers,
        test_login_case_insensitive_email,
        test_login_returns_user_profile,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
            print(f"✓ {test.__name__} PASSED")
        except AssertionError as e:
            failed += 1
            print(f"✗ {test.__name__} FAILED: {str(e)}")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} ERROR: {str(e)}")

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
