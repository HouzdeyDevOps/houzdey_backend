"""Custom exception classes for the application"""

from fastapi import HTTPException, status


class BaseAppException(HTTPException):
    """Base exception class for application-specific exceptions"""
    
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class ValidationError(BaseAppException):
    """Exception raised for validation errors"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class NotFoundError(BaseAppException):
    """Exception raised when a resource is not found"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class PermissionError(BaseAppException):
    """Exception raised for permission/authorization errors"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class AuthenticationError(BaseAppException):
    """Exception raised for authentication errors"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ConflictError(BaseAppException):
    """Exception raised for resource conflicts"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class BusinessLogicError(BaseAppException):
    """Exception raised for business logic violations"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)