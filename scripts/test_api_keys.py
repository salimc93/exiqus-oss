#!/usr/bin/env python3
"""
API Key Testing Script for GitHub Analyzer

This script verifies that both GitHub and Anthropic API keys are working correctly
before proceeding with development.

Run this after setting up your .env file with real API keys.
"""

import os
import sys

from dotenv import load_dotenv


def test_github_api():
    """Test GitHub API access"""
    print("🔍 Testing GitHub API...")

    try:
        from github import Auth, Github

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token or github_token == "your_github_token_here":
            print("❌ GITHUB_TOKEN not found or still has placeholder value in .env")
            print("   Please update your .env file with a real GitHub token")
            return False

        g = Github(auth=Auth.Token(github_token))
        user = g.get_user()
        print(f"✅ GitHub API: Connected as {user.login}")

        # Test rate limit
        rate_limit = g.get_rate_limit()
        print(
            f"   Rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit} remaining"
        )

        # Test with a simple repository query
        repo = g.get_repo("octocat/Hello-World")
        print(f"   Test query: {repo.full_name} has {repo.stargazers_count} stars")

        return True

    except ImportError:
        print("❌ PyGithub not installed. Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ GitHub API Error: {e}")
        print("   Check your GITHUB_TOKEN in .env file")
        return False


def test_anthropic_api():
    """Test Anthropic Claude API access"""
    print("\n🤖 Testing Anthropic API...")

    try:
        from anthropic import Anthropic

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key or anthropic_key == "your_anthropic_key_here":
            print(
                "❌ ANTHROPIC_API_KEY not found or still has placeholder value in .env"
            )
            print("   Please update your .env file with a real Anthropic API key")
            return False

        client = Anthropic(api_key=anthropic_key)

        # Test with simple request
        print("   Making test request to Claude Haiku...")
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "Respond with exactly: 'GitHub Analyzer API test successful'",
                }
            ],
        )

        response_text = response.content[0].text.strip()
        print(f"   Claude response: {response_text}")

        if "successful" in response_text.lower():
            print("✅ Anthropic API: Connected successfully")
            print("   Model: claude-3-haiku-20240307")

            # Estimate cost for development
            input_tokens = 50  # rough estimate
            output_tokens = 50
            cost = (input_tokens * 0.00025 + output_tokens * 0.00125) / 1000
            print(f"   Estimated cost for this test: ${cost:.6f}")

            return True
        else:
            print("❌ Anthropic API: Unexpected response")
            return False

    except ImportError:
        print(
            "❌ Anthropic library not installed. Run: pip install -r requirements.txt"
        )
        return False
    except Exception as e:
        print(f"❌ Anthropic API Error: {e}")
        print("   Check your ANTHROPIC_API_KEY in .env file")
        return False


def test_environment_setup():
    """Test basic environment setup"""
    print("\n🔧 Testing Environment Setup...")

    # Check Python version
    if sys.version_info < (3, 9):
        print(
            f"❌ Python {sys.version_info.major}.{sys.version_info.minor} detected. Python 3.9+ required."
        )
        return False
    else:
        print(
            f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    # Check .env file exists
    if not os.path.exists(".env"):
        print("❌ .env file not found")
        return False
    else:
        print("✅ .env file found")

    # Check required environment variables are set
    required_vars = ["ANTHROPIC_API_KEY", "GITHUB_TOKEN"]
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith("your_"):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing or placeholder values for: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables set")

    return True


def main():
    """Main testing function"""
    print("🚀 GitHub Analyzer API Key Testing")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Run tests
    env_ok = test_environment_setup()
    github_ok = test_github_api() if env_ok else False
    anthropic_ok = test_anthropic_api() if env_ok else False

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Environment Setup: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"   GitHub API:        {'✅ PASS' if github_ok else '❌ FAIL'}")
    print(f"   Anthropic API:     {'✅ PASS' if anthropic_ok else '❌ FAIL'}")

    if env_ok and github_ok and anthropic_ok:
        print("\n🎉 All tests passed! Ready for development.")
        print("\nNext steps:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Run the analyzer: python main.py https://github.com/user/repo")
        return True
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        if not env_ok:
            print(
                "   - Check your .env file has real API keys (not placeholder values)"
            )
        if not github_ok:
            print(
                "   - Verify your GitHub token has correct scopes: public_repo, read:user, read:org"
            )
        if not anthropic_ok:
            print("   - Verify your Anthropic API key is valid and has credit")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
