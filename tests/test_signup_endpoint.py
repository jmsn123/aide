#!/usr/bin/env python3
"""
Integration test for signup endpoint
Tests the deployed auth_signup Lambda via API Gateway

Run with: python3 tests/test_signup_endpoint.py
"""

import requests
import json
from datetime import datetime

# API Gateway endpoint
ENDPOINT = "https://cypom236ui.execute-api.us-east-1.amazonaws.com/v1/auth/signup"


def test_signup_success():
    """Test successful user signup"""
    print("\n=== Test 1: Successful Signup ===")

    # Unique email to avoid duplicates
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    email = f"testuser{timestamp}@example.com"

    response = requests.post(ENDPOINT, json={
        'email': email,
        'password': 'SecurePass123!',
        'name': 'Test User'
    })

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    data = response.json()
    assert data['success'] == True, "Expected success=True"
    assert 'user_id' in data['data'], "Missing user_id in response"
    assert data['data']['email'] == email, f"Email mismatch"

    print("✅ PASS: Successful signup")
    return data['data']['user_id']


def test_signup_duplicate():
    """Test duplicate user signup"""
    print("\n=== Test 2: Duplicate User ===")

    # Use same email as test 1
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    email = f"duplicate{timestamp}@example.com"

    # Create user first time
    response1 = requests.post(ENDPOINT, json={
        'email': email,
        'password': 'SecurePass123!',
        'name': 'First Signup'
    })
    print(f"First signup: {response1.status_code}")

    # Try to create again
    response2 = requests.post(ENDPOINT, json={
        'email': email,
        'password': 'SecurePass123!',
        'name': 'Duplicate Signup'
    })

    print(f"Status Code: {response2.status_code}")
    print(f"Response: {json.dumps(response2.json(), indent=2)}")

    assert response2.status_code == 409, f"Expected 409, got {response2.status_code}"
    data = response2.json()
    assert data['success'] == False, "Expected success=False"
    assert data['error']['code'] == 'USER_EXISTS', f"Expected USER_EXISTS error"

    print("✅ PASS: Duplicate user rejected")


def test_password_validation():
    """Test password validation"""
    print("\n=== Test 3: Password Validation ===")

    # Test weak password (no special character)
    response = requests.post(ENDPOINT, json={
        'email': 'weakpass@example.com',
        'password': 'WeakPass123',  # Missing special character
        'name': 'Weak Password'
    })

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    data = response.json()
    assert data['success'] == False, "Expected success=False"
    assert data['error']['code'] == 'WEAK_PASSWORD', f"Expected WEAK_PASSWORD error"

    print("✅ PASS: Weak password rejected")


def test_email_validation():
    """Test email format validation"""
    print("\n=== Test 4: Email Validation ===")

    response = requests.post(ENDPOINT, json={
        'email': 'invalid-email',  # Invalid format
        'password': 'SecurePass123!',
        'name': 'Invalid Email'
    })

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    data = response.json()
    assert data['success'] == False, "Expected success=False"
    assert data['error']['code'] == 'INVALID_EMAIL', f"Expected INVALID_EMAIL error"

    print("✅ PASS: Invalid email rejected")


def test_missing_fields():
    """Test required field validation"""
    print("\n=== Test 5: Missing Fields ===")

    response = requests.post(ENDPOINT, json={
        'email': 'test@example.com',
        # Missing password and name
    })

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    data = response.json()
    assert data['success'] == False, "Expected success=False"
    assert 'MISSING' in data['error']['code'], f"Expected MISSING_* error"

    print("✅ PASS: Missing fields rejected")


def test_length_validation():
    """Test input length validation"""
    print("\n=== Test 6: Length Validation ===")

    # Test email too long
    long_email = 'a' * 250 + '@example.com'  # 262 chars > 255 limit

    response = requests.post(ENDPOINT, json={
        'email': long_email,
        'password': 'SecurePass123!',
        'name': 'Test User'
    })

    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    data = response.json()
    assert data['success'] == False, "Expected success=False"
    assert data['error']['code'] == 'EMAIL_TOO_LONG', f"Expected EMAIL_TOO_LONG error"

    print("✅ PASS: Long email rejected")


def test_cors_headers():
    """Test CORS headers are present"""
    print("\n=== Test 7: CORS Headers ===")

    response = requests.post(ENDPOINT, json={
        'email': 'cors@example.com',
        'password': 'weak',  # Will fail validation
        'name': 'CORS Test'
    })

    print(f"Headers: {dict(response.headers)}")

    assert 'Access-Control-Allow-Origin' in response.headers, "Missing CORS header"
    assert response.headers['Access-Control-Allow-Origin'] == '*', "CORS not set to *"

    print("✅ PASS: CORS headers present")


def test_special_characters_in_password():
    """Test password with various special characters"""
    print("\n=== Test 8: Special Characters in Password ===")

    special_chars = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')']

    for char in special_chars:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        email = f"special{timestamp}@example.com"
        password = f"SecurePass123{char}"

        response = requests.post(ENDPOINT, json={
            'email': email,
            'password': password,
            'name': f'Special Char {char}'
        })

        print(f"Testing '{char}': {response.status_code}")

        if response.status_code != 201:
            print(f"❌ FAIL: Special char '{char}' failed")
            print(f"Response: {response.json()}")
            return

    print("✅ PASS: All special characters work")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("SIGNUP ENDPOINT INTEGRATION TESTS")
    print("="*60)

    tests = [
        test_signup_success,
        test_signup_duplicate,
        test_password_validation,
        test_email_validation,
        test_missing_fields,
        test_length_validation,
        test_cors_headers,
        test_special_characters_in_password
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
