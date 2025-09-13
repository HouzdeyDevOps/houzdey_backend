# Houzdey Backend Architecture

## Overview

This backend has been refactored to follow a **layered architecture** with proper separation of concerns, making it scalable, maintainable, and testable.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│                API Layer                    │  ← Thin controllers
├─────────────────────────────────────────────┤
│              Service Layer                  │  ← Business logic
├─────────────────────────────────────────────┤
│            Repository Layer                 │  ← Data access
├─────────────────────────────────────────────┤
│              Database Layer                 │  ← MongoDB
└─────────────────────────────────────────────┘
```

### 1. API Layer (`app/api/routes/`)
- **Responsibility**: HTTP request/response handling, input validation, authentication
- **Characteristics**: Thin controllers that delegate business logic to services
- **Files**: `properties_new.py`, `users.py`, etc.

### 2. Service Layer (`app/services/`)
- **Responsibility**: Business logic, validation, orchestration between repositories
- **Characteristics**: Contains all domain-specific logic, transaction management
- **Files**: `user_service.py`, `property_service.py`, `base_service.py`

### 3. Repository Layer (`app/repositories/`)
- **Responsibility**: Data access abstraction, database operations
- **Characteristics**: Clean interface to database, no business logic
- **Files**: `user_repository.py`, `property_repository.py`, `base.py`

### 4. Database Layer
- **Responsibility**: Data persistence
- **Technology**: MongoDB with Motor (async driver)

## Key Components

### Base Classes

#### `BaseRepository` (`app/repositories/base.py`)
Provides common database operations:
- `create()` - Create new document
- `get_by_id()` - Fetch by ID
- `update_by_id()` - Update document
- `delete_by_id()` - Delete document
- `find()` - Query with filters, pagination, sorting
- `count()` - Count documents

#### `BaseService` (`app/services/base_service.py`)
Provides common business logic utilities:
- `validate_object_id()` - ObjectId validation
- `validate_required_fields()` - Field validation
- `check_ownership()` - Authorization checks
- `ensure_exists()` - Existence validation

### Dependency Injection (`app/core/dependencies.py`)
- Manages service and repository instantiation
- Uses FastAPI's dependency injection system
- Provides type-safe dependencies

### Error Handling (`app/core/exceptions.py` & `app/core/error_handlers.py`)
- Custom exception hierarchy
- Global error handlers with proper HTTP status codes
- Structured error responses

### Logging (`app/core/logging.py`)
- Colored console output
- File logging support
- Configurable log levels

## Usage Examples

### Repository Usage
```python
from app.repositories.user_repository import UserRepository

user_repo = UserRepository()

# Find user by email
user = await user_repo.find_by_email("user@example.com")

# Create new user
new_user = await user_repo.create(user_data)

# Update user
success = await user_repo.update_by_id(user_id, update_data)
```

### Service Usage
```python
from app.services.user_service import UserService

user_service = UserService()

# Authenticate user (includes business logic)
user = await user_service.authenticate_user(email, password)

# Create user (includes validation, hashing, etc.)
new_user = await user_service.create_user(user_data)
```

### API Route (Thin Controller)
```python
@router.post("/users/login")
async def login_user(
    credentials: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    try:
        user = await user_service.authenticate_user(
            credentials.email, 
            credentials.password
        )
        return {"user": user, "token": create_token(user["id"])}
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

## Benefits of New Architecture

### 1. **Separation of Concerns**
- Each layer has a single responsibility
- Business logic is centralized in services
- Data access is abstracted in repositories

### 2. **Scalability**
- Easy to add new features
- Services can be easily extracted into microservices
- Database operations are optimized and reusable

### 3. **Testability**
- Each layer can be unit tested independently
- Mock dependencies easily
- Clear interfaces between layers

### 4. **Maintainability**
- Code is organized and predictable
- Changes in one layer don't affect others
- Consistent patterns throughout

### 5. **Error Handling**
- Structured error responses
- Proper HTTP status codes
- Comprehensive logging

## Migration from Old Architecture

The old architecture had these issues:
- **Fat controllers**: Routes contained business logic and database operations
- **Tight coupling**: Direct database access from routes
- **Code duplication**: Similar logic repeated across routes
- **Poor error handling**: Inconsistent error responses

### Before (Old):
```python
@router.get("/properties")
async def get_properties():
    # 100+ lines of filtering logic
    filter_query = {"status": "available"}
    if search:
        filter_query["$or"] = [...]
    # Direct database access
    properties = await property_collection.find(filter_query)
    # More logic...
```

### After (New):
```python
@router.get("/properties")
async def get_properties(
    search: str = None,
    property_service: PropertyService = Depends(get_property_service)
):
    return await property_service.get_properties_with_filters(search=search)
```

## Testing the New Architecture

Run the migration validation script:

```bash
cd backend
python app/scripts/migrate_to_new_architecture.py
```

This validates:
- All imports work correctly
- Database connections
- Repository layer functionality
- Service layer functionality

## Best Practices

### 1. **Service Layer**
- Keep business logic in services
- Services should orchestrate repositories
- Use proper exception handling
- Log important operations

### 2. **Repository Layer**
- Only handle data access
- No business logic
- Return consistent data structures
- Handle database errors gracefully

### 3. **API Layer**
- Keep controllers thin
- Validate input using Pydantic models
- Use dependency injection
- Let global error handlers manage exceptions

### 4. **Error Handling**
- Use custom exceptions for business logic errors
- Let global handlers format responses
- Log errors with appropriate levels
- Provide meaningful error messages

## Future Enhancements

1. **Caching Layer**: Add Redis for frequently accessed data
2. **Event System**: Implement domain events for decoupled communication
3. **Background Tasks**: Add Celery for async processing
4. **Monitoring**: Add metrics and health checks
5. **API Documentation**: Auto-generated OpenAPI docs with proper examples