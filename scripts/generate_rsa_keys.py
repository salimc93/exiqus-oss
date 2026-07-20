#!/usr/bin/env python3
"""
Generate RSA key pair for JWT signing.

This script generates RSA-2048 keys and outputs them in two formats:
1. PEM files (for local development)
2. Base64-encoded strings (for Railway/production environment variables)

Usage:
    python scripts/generate_rsa_keys.py
"""

import base64
import os
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_key_pair():
    """Generate RSA-2048 key pair."""
    print("🔐 Generating RSA-2048 key pair...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Generate public key
    public_key = private_key.public_key()

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_pem, public_pem


def save_to_files(private_pem: bytes, public_pem: bytes):
    """Save keys to files for local development."""
    # Create keys directory if it doesn't exist
    keys_dir = Path("keys")
    keys_dir.mkdir(exist_ok=True)

    # Save private key
    private_key_path = keys_dir / "private_key.pem"
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    os.chmod(private_key_path, 0o600)  # Restrict permissions

    # Save public key
    public_key_path = keys_dir / "public_key.pem"
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    print("✅ Keys saved to files:")
    print(f"   - Private: {private_key_path}")
    print(f"   - Public: {public_key_path}")


def encode_for_railway(private_pem: bytes, public_pem: bytes):
    """Encode keys as base64 for Railway environment variables."""
    private_b64 = base64.b64encode(private_pem).decode("utf-8")
    public_b64 = base64.b64encode(public_pem).decode("utf-8")

    print("\n" + "=" * 80)
    print("🚂 RAILWAY ENVIRONMENT VARIABLES")
    print("=" * 80)
    print("\n📝 Copy these values to Railway:\n")

    print("JWT_PRIVATE_KEY:")
    print(private_b64)
    print("\nJWT_PUBLIC_KEY:")
    print(public_b64)

    # Also save to a file for easy copy-paste
    env_file = Path("keys") / "railway_env_vars.txt"
    with open(env_file, "w") as f:
        f.write("# Railway Environment Variables\n")
        f.write("# Copy these values to Railway dashboard\n\n")
        f.write(f"JWT_PRIVATE_KEY={private_b64}\n\n")
        f.write(f"JWT_PUBLIC_KEY={public_b64}\n")

    print(f"\n💾 Also saved to: {env_file}")


def show_local_env_example():
    """Show example .env configuration for local development."""
    print("\n" + "=" * 80)
    print("💻 LOCAL DEVELOPMENT (.env)")
    print("=" * 80)
    print("\n📝 Add these to your .env file:\n")
    print("JWT_ALGORITHM=RS256")
    print("JWT_PRIVATE_KEY_PATH=keys/private_key.pem")
    print("JWT_PUBLIC_KEY_PATH=keys/public_key.pem")
    print("JWT_AUDIENCE=exiqus-api")
    print("JWT_ISSUER=exiqus-api")


def main():
    """Main execution."""
    print("\n" + "=" * 80)
    print("🔑 Exiqus JWT Key Generator - Railway Edition")
    print("=" * 80)
    print()

    # Generate keys
    private_pem, public_pem = generate_rsa_key_pair()

    # Save to files (for local dev)
    save_to_files(private_pem, public_pem)

    # Encode for Railway (production)
    encode_for_railway(private_pem, public_pem)

    # Show local env example
    show_local_env_example()

    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)
    print("\n⚠️  SECURITY REMINDERS:")
    print("   1. Never commit keys/ directory to git (already in .gitignore)")
    print("   2. Keep keys/railway_env_vars.txt secure and delete after use")
    print("   3. Use different keys for staging and production")
    print("   4. Rotate keys every 90 days")
    print("\n🚀 Next steps:")
    print("   1. Copy JWT_PRIVATE_KEY and JWT_PUBLIC_KEY to Railway")
    print("   2. Add JWT_ALGORITHM=RS256 to Railway")
    print("   3. Add JWT_AUDIENCE and JWT_ISSUER to Railway")
    print("   4. Deprecate old JWT_SECRET_KEY (keep for rollback)")
    print()


if __name__ == "__main__":
    main()
