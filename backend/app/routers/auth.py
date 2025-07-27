from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.config import get_db
from app.schemas.auth import (
    UserLogin, UserSignup, TokenResponse, UserResponse, SignupResponse,
    UserUpdate, PasswordReset, TokenRefresh, ChangePassword, 
    EmailConfirmation, ResendConfirmation
)
from app.models.user import User, UserRole
from app.services.auth_service import auth_service
from app.auth.dependencies import (
    get_current_active_user, require_admin, require_manager_or_admin,
    RolePermissions
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=SignupResponse)
async def signup(
    user_data: UserSignup,
    db: Session = Depends(get_db)
):
    """Sign up a new user"""
    try:
        result = await auth_service.sign_up(user_data, db)
        return SignupResponse(
            user=UserResponse.model_validate(result["db_user"]),
            requires_confirmation=result["requires_confirmation"],
            message=result["message"],
            session=result.get("session")
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user and return access token"""
    try:
        result = await auth_service.sign_in(credentials, db)
        
        return TokenResponse(
            access_token=result["session"].access_token,
            refresh_token=result["session"].refresh_token,
            token_type="bearer",
            expires_in=result["session"].expires_in,
            user=UserResponse.model_validate(result["db_user"])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout current user"""
    # Note: You'd need to pass the access token here
    # This is a simplified version
    return {"message": "Successfully logged out"}


@router.post("/confirm-email")
async def confirm_email(
    confirmation: EmailConfirmation,
    db: Session = Depends(get_db)
):
    """Confirm user email address"""
    try:
        result = await auth_service.confirm_email(confirmation.token, db)
        return {
            "message": result["message"],
            "user": UserResponse.model_validate(result["db_user"])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/resend-confirmation")
async def resend_confirmation(
    request: ResendConfirmation,
    db: Session = Depends(get_db)
):
    """Resend email confirmation"""
    try:
        success = await auth_service.resend_confirmation(request.email)
        if success:
            return {"message": "Confirmation email sent successfully"}
        raise Exception("Failed to send confirmation email")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Refresh access token"""
    try:
        result = await auth_service.refresh_token(token_data.refresh_token, db)
        
        return TokenResponse(
            access_token=result["session"].access_token,
            refresh_token=result["session"].refresh_token,
            token_type="bearer",
            expires_in=result["session"].expires_in,
            user=UserResponse.model_validate(result["user"])
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    try:
        # Users can update their own info except role and is_active
        update_data = user_update.dict(exclude_unset=True)
        
        # Prevent users from changing their own role or active status
        if "role" in update_data or "is_active" in update_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update role or active status"
            )
        
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        db.commit()
        db.refresh(current_user)
        
        return UserResponse.model_validate(current_user)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update user: {str(e)}"
        )


@router.post("/reset-password")
async def reset_password(password_reset: PasswordReset):
    """Send password reset email"""
    try:
        await auth_service.reset_password(password_reset.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's permissions"""
    permissions = RolePermissions.get_user_permissions(current_user.role)
    return {
        "role": current_user.role.value,
        "permissions": permissions
    }


# Admin-only routes
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID (manager/admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return UserResponse.model_validate(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update user: {str(e)}"
        )


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: UserRole,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)"""
    try:
        updated_user = await auth_service.update_user_role(user_id, role, db)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "message": f"User role updated to {role.value}",
            "user": UserResponse.model_validate(updated_user)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    return {"message": "User activated successfully"}
