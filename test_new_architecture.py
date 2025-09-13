"""Simple test to validate the new architecture works"""

def test_imports():
    """Test that all new modules can be imported"""
    try:
        # Test repository imports
        from app.repositories.base import BaseRepository
        from app.repositories.user_repository import UserRepository
        from app.repositories.property_repository import PropertyRepository
        
        # Test service imports
        from app.services.base_service import BaseService
        from app.services.user_service import UserService
        from app.services.property_service import PropertyService
        
        # Test core imports
        from app.core.exceptions import ValidationError, NotFoundError
        from app.core.dependencies import get_user_service, get_property_service
        from app.core.logging import setup_logging
        
        print("All imports successful")
        return True
        
    except ImportError as e:
        print(f"Import failed: {e}")
        return False


def test_instantiation():
    """Test that classes can be instantiated"""
    try:
        from app.repositories.user_repository import UserRepository
        from app.services.user_service import UserService
        
        # Test repository instantiation
        user_repo = UserRepository()
        print("UserRepository instantiated")
        
        # Test service instantiation
        user_service = UserService()
        print("UserService instantiated")
        
        # Test validation methods
        assert user_service.validate_object_id("507f1f77bcf86cd799439011"), "ObjectId validation failed"
        assert not user_service.validate_object_id("invalid"), "ObjectId validation should fail"
        print("Validation methods working")
        
        return True
        
    except Exception as e:
        print(f"Instantiation failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing new architecture...")
    
    tests = [
        ("Import Test", test_imports()),
        ("Instantiation Test", test_instantiation()),
    ]
    
    print("\n" + "="*40)
    print("TEST RESULTS")
    print("="*40)
    
    passed = 0
    for test_name, result in tests:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("All tests passed! New architecture is working.")
    else:
        print("Some tests failed. Please check the issues above.")