#!/usr/bin/env python3
"""
Quick start script for AI Astrologer API
This script helps you set up and run the application quickly.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if required tools are installed."""
    print("🔍 Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ is required")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Check if pipenv is available
    try:
        result = subprocess.run(['pipenv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Pipenv detected: {result.stdout.strip()}")
        else:
            print("❌ Pipenv not found. Please install it with: pip install pipenv")
            return False
    except FileNotFoundError:
        print("❌ Pipenv not found. Please install it with: pip install pipenv")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists."""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found!")
        print("📝 Creating a basic .env file...")
        
        env_content = """# AI Astrologer API Environment Configuration
ENVIRONMENT=development
DEBUG=true
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Database Settings - UPDATE THESE WITH YOUR VALUES
DATABASE_URL=postgresql://username:password@localhost:5432/ai_astrologer_db
TEST_DATABASE_URL=postgresql://username:password@localhost:5432/ai_astrologer_test_db

# Firebase Settings - UPDATE THESE WITH YOUR VALUES
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY_HERE\\n-----END PRIVATE KEY-----\\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_SERVICE_ACCOUNT_PATH=config/firebase-service-account.json

# OpenRouter API Settings - UPDATE WITH YOUR API KEY
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_API_BASE=https://openrouter.ai/api/v1
OPENROUTER_MODEL=deepseek/deepseek-chat

# Encryption Settings - GENERATE A RANDOM 32-CHARACTER KEY
ENCRYPTION_SECRET_KEY=your-32-character-encryption-key-here

# Redis Settings
REDIS_URL=redis://localhost:6379
"""
        
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("✅ Created .env file with default values")
        print("⚠️  IMPORTANT: Please update the .env file with your actual values before running!")
        return False
    else:
        print("✅ .env file found")
        return True

def install_dependencies():
    """Install project dependencies."""
    print("📦 Installing dependencies...")
    try:
        result = subprocess.run(['pipenv', 'install'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def run_app():
    """Run the FastAPI application."""
    print("🚀 Starting AI Astrologer API...")
    print("📍 Application will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run the app with uvicorn
        subprocess.run([
            'pipenv', 'run', 'uvicorn', 
            'app.main:app', 
            '--host', '0.0.0.0', 
            '--port', '8000', 
            '--reload'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error running application: {e}")

def main():
    """Main function to orchestrate the startup process."""
    print("🌟 AI Astrologer API - Quick Start")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Requirements check failed. Please install missing dependencies.")
        return
    
    # Check environment file
    env_ok = check_env_file()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies.")
        return
    
    if not env_ok:
        print("\n⚠️  Please update your .env file with actual values before continuing.")
        print("📖 See RUN_INSTRUCTIONS.md for detailed setup instructions.")
        
        response = input("\nDo you want to continue anyway? (y/N): ").lower().strip()
        if response != 'y':
            print("👋 Goodbye! Update your .env file and run this script again.")
            return
    
    print("\n🎉 Setup complete! Starting the application...")
    run_app()

if __name__ == "__main__":
    main()
