#!/usr/bin/env python3
"""Test runner for Snooze components."""

import os
import sys
import unittest

import dotenv

# Load environment variables
dotenv.load_dotenv()


def main():
    """Run all tests with different configurations."""
    print("🧪 Snooze Test Suite")
    print("=" * 50)

    # Check for API credentials
    reddit_creds = all([
        os.getenv("REDDIT_CLIENT_ID"),
        os.getenv("REDDIT_CLIENT_SECRET")
    ])

    azure_creds = all([
        os.getenv("AZURE_API_KEY"),
        os.getenv("AZURE_ENDPOINT"),
        os.getenv("AZURE_DEPLOYMENT")
    ])

    print(f"📋 Test Environment:")
    print(f"   Reddit API: {'✅ Available' if reddit_creds else '❌ Missing'}")
    print(f"   Azure OpenAI: {'✅ Available' if azure_creds else '❌ Missing'}")
    print()

    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 50)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")

    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   • {test}: {traceback.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            error_line = traceback.split('\n')[-2] if '\n' in traceback else traceback
            print(f"   • {test}: {error_line}")

    if result.skipped:
        print("\n⏭️  Skipped:")
        for test, reason in result.skipped:
            print(f"   • {test}: {reason}")

    # Return appropriate exit code
    if result.failures or result.errors:
        print("\n💡 Tip: Make sure your .env file has valid API credentials for integration tests")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()