#!/usr/bin/env python3
"""
Quick test script to verify that the fixes work correctly.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_basic_imports():
    """Test that all modules can be imported without errors."""
    print("🔍 Testing imports...")
    
    try:
        from app.models.user import User
        from app.models.admin import AdminUser
        from app.schemas.user import UserCreate
        from app.services.user_service import UserService
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

async def test_model_relationships():
    """Test that model relationships are properly configured."""
    print("🔍 Testing model relationships...")
    
    try:
        from app.models.user import User
        from app.models.admin import AdminUser
        from app.models.chat import ChatSession
        from app.models.chart import Chart
        
        # Check if the relationship attributes exist
        user_fields = User.__fields__
        required_relationships = ['admin_profile', 'chat_sessions', 'charts']
        
        missing_relationships = []
        for rel in required_relationships:
            if rel not in user_fields:
                missing_relationships.append(rel)
        
        if not missing_relationships:
            print("✅ All model relationships configured correctly")
            print(f"   - User -> AdminUser: ✅")
            print(f"   - User -> ChatSession: ✅") 
            print(f"   - User -> Chart: ✅")
            return True
        else:
            print(f"❌ Missing relationships: {missing_relationships}")
            return False
    except Exception as e:
        print(f"❌ Model relationship error: {e}")
        return False

async def test_schema_creation():
    """Test that schemas can be created with model_dump."""
    print("🔍 Testing schema creation...")
    
    try:
        from app.schemas.user import UserCreate
        
        # Create a sample user data
        user_data = UserCreate(
            firebase_uid="test_uid_123",
            email="test@example.com",
            email_verified=True
        )
        
        # Test model_dump method
        user_dict = user_data.model_dump()
        
        if isinstance(user_dict, dict) and 'firebase_uid' in user_dict:
            print("✅ Schema creation and model_dump work correctly")
            return True
        else:
            print("❌ Schema creation failed")
            return False
    except Exception as e:
        print(f"❌ Schema creation error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🧪 Running fix verification tests...")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_model_relationships,
        test_schema_creation
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()
    
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Your fixes are working correctly!")
        return True
    else:
        print(f"❌ Some tests failed ({passed}/{total})")
        print("⚠️  Please check the errors above")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
