"""
Migration script to transition to the new architecture
This script helps validate the new architecture by testing key components
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the path to import app modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.core.database import create_indexes
    from app.repositories.user_repository import UserRepository
    from app.repositories.property_repository import PropertyRepository
    from app.services.user_service import UserService
    from app.services.property_service import PropertyService
    from app.core.logging import setup_logging, get_logger
except ImportError as e:
    print(f"Failed to import modules: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)


async def test_repositories():
    """Test repository layer functionality"""
    logger.info("Testing repository layer...")
    
    try:
        # Test user repository
        user_repo = UserRepository()
        logger.info("✅ UserRepository initialized successfully")
        
        # Test property repository
        property_repo = PropertyRepository()
        logger.info("✅ PropertyRepository initialized successfully")
        
        # Test basic repository operations (without actually modifying data)
        # Just test that the methods exist and are callable
        assert hasattr(user_repo, 'find_by_email'), "UserRepository missing find_by_email method"
        assert hasattr(property_repo, 'find_by_owner_id'), "PropertyRepository missing find_by_owner_id method"
        
        logger.info("✅ Repository layer test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Repository layer test failed: {str(e)}")
        return False


async def test_services():
    """Test service layer functionality"""
    logger.info("Testing service layer...")
    
    try:
        # Test user service
        user_service = UserService()
        logger.info("✅ UserService initialized successfully")
        
        # Test property service
        property_service = PropertyService()
        logger.info("✅ PropertyService initialized successfully")
        
        # Test that services have the expected methods
        assert hasattr(user_service, 'authenticate_user'), "UserService missing authenticate_user method"
        assert hasattr(property_service, 'get_properties_with_filters'), "PropertyService missing get_properties_with_filters method"
        
        # Test validation methods
        assert user_service.validate_object_id("507f1f77bcf86cd799439011"), "ObjectId validation failed"
        assert not user_service.validate_object_id("invalid"), "ObjectId validation should fail for invalid ID"
        
        logger.info("✅ Service layer test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service layer test failed: {str(e)}")
        return False


async def test_database_connections():
    """Test database connectivity and indexes"""
    logger.info("Testing database connections...")
    
    try:
        # Test database index creation
        await create_indexes()
        logger.info("✅ Database indexes created/verified successfully")
        
        # Test basic database connectivity through repositories
        user_repo = UserRepository()
        
        # Try to count users (this tests database connectivity)
        user_count = await user_repo.count()
        logger.info(f"✅ Database connection successful. Found {user_count} users")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {str(e)}")
        return False


async def validate_imports():
    """Validate that all new modules can be imported correctly"""
    logger.info("Validating imports...")
    
    try:
        # Test repository imports
        from app.repositories.base import BaseRepository
        from app.repositories.user_repository import UserRepository
        from app.repositories.property_repository import PropertyRepository
        from app.repositories.review_repository import ReviewRepository, ReviewSummaryRepository
        
        # Test service imports
        from app.services.base_service import BaseService
        from app.services.user_service import UserService
        from app.services.property_service import PropertyService
        
        # Test core imports
        from app.core.exceptions import ValidationError, NotFoundError
        from app.core.dependencies import get_user_service, get_property_service
        from app.core.error_handlers import register_error_handlers
        from app.core.logging import setup_logging
        
        logger.info("✅ All imports successful")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during import validation: {str(e)}")
        return False


async def run_migration_tests():
    """Run all migration tests"""
    logger.info("🚀 Starting architecture migration validation...")
    
    tests = [
        ("Import Validation", validate_imports()),
        ("Database Connections", test_database_connections()),
        ("Repository Layer", test_repositories()),
        ("Service Layer", test_services()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        logger.info(f"\n--- Running {test_name} ---")
        result = await test_coro
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("MIGRATION VALIDATION SUMMARY")
    logger.info("="*50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    logger.info("-"*50)
    logger.info(f"Total: {len(results)} tests | Passed: {passed} | Failed: {failed}")
    
    if failed == 0:
        logger.info("🎉 All tests passed! Architecture migration is ready.")
        return True
    else:
        logger.error(f"💥 {failed} test(s) failed. Please fix issues before proceeding.")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration_tests())
    sys.exit(0 if success else 1)