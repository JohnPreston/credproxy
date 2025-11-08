#!/usr/bin/env python3
"""
Test script for Python Boto3 SDK with CredProxy
"""

import sys

import boto3


def test_boto3_credentials():
    """Test that Boto3 can use CredProxy credentials."""
    try:
        # Create STS client using container credentials
        sts_client = boto3.client("sts")

        # Get caller identity
        response = sts_client.get_caller_identity()

        print("✅ Boto3 test successful!")
        print(f"Account: {response.get('Account', 'Unknown')}")
        print(f"User ID: {response.get('UserId', 'Unknown')}")
        print(f"ARN: {response.get('Arn', 'Unknown')}")

        return True

    except Exception as error:
        print(f"❌ Boto3 test failed: {error}")
        return False


if __name__ == "__main__":
    success = test_boto3_credentials()
    sys.exit(0 if success else 1)
