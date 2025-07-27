from typing import List, Optional
from functools import wraps
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.config import get_db
from app.models.user import User, UserRole
from app.services.auth_service import auth_service


security = HTTPBearer()


class RolePermissions:
    """Define role-based permissions"""
    
    PERMISSIONS = {
        UserRole.ADMIN: [
            "manage_users", "assign_roles", "platform_settings", 
            "view_all_reports", "monitor_system", "upload_data", 
            "view_dashboards", "analyze_seismic", "annotate_models",
            "model_simulations", "generate_forecasts", "impact_assessments",
            "report_compliance", "access_training", "validate_learning"
        ],
        UserRole.FIELD_TEAM: [
            "upload_data", "view_dashboards", "access_training", "validate_learning"
        ],
        UserRole.GEOSCIENTIST: [
            "analyze_seismic", "annotate_models", "view_dashboards", 
            "access_training", "validate_learning"
        ],
        UserRole.RESERVOIR_ENGINEER: [
            "model_simulations", "generate_forecasts", "view_dashboards",
            "access_training", "validate_learning"
        ],
        UserRole.ENVIRONMENTAL_OFFICER: [
            "impact_assessments", "report_compliance", "view_dashboards",
            "access_training", "validate_learning"
        ],
        UserRole.MANAGER: [
            "view_all_reports", "monitor_system", "view_dashboards",
            "access_training", "validate_learning"
        ],
        UserRole.NEW_EMPLOYEE: [
            "access_training", "validate_learning"
        ]
    }
    
    @classmethod
    def has_permission(cls, role: UserRole, permission: str) -> bool:
        """Check if role has specific permission"""
        return permission in cls.PERMISSIONS.get(role, [])
    
    @classmethod
    def get_user_permissions(cls, role: UserRole) -> List[str]:
        """Get all permissions for a role"""
        return cls.PERMISSIONS.get(role, [])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    try:
        access_token = credentials.credentials
        user = await auth_service.get_current_user(access_token, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    return current_user


def require_roles(allowed_roles: List[UserRole]):
    """Decorator to require specific roles"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the current_user parameter
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_permissions(required_permissions: List[str]):
    """Decorator to require specific permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the current_user parameter
            current_user = None
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_permissions = RolePermissions.get_user_permissions(current_user.role)
            
            for permission in required_permissions:
                if permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied. Missing permission: {permission}"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Specific role dependencies
async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_manager_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require manager or admin role"""
    if current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Admin access required"
        )
    return current_user


async def require_field_access(current_user: User = Depends(get_current_active_user)) -> User:
    """Require field team, manager, or admin role"""
    allowed_roles = [UserRole.FIELD_TEAM, UserRole.MANAGER, UserRole.ADMIN]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Field team access required"
        )
    return current_user
