import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from gotrue.errors import AuthApiError
from sqlalchemy.orm import Session
from app.models.user import User, UserSession, UserRole
from app.schemas.auth import UserCreate, UserLogin, UserResponse
from datetime import datetime, timedelta
import secrets


class SupabaseAuthService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and Anon Key must be provided")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
    
    async def sign_up(self, user_data: UserCreate, db: Session) -> Dict[str, Any]:
        """Sign up a new user with Supabase Auth"""
        try:
            # Create user in Supabase Auth
            auth_response = self.supabase.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name,
                        "role": user_data.role.value,
                        "department": user_data.department,
                        "phone_number": user_data.phone_number
                    }
                }
            })
            
            if auth_response.user:
                # Determine if user is confirmed (session exists) or needs email confirmation
                is_confirmed = auth_response.session is not None
                
                # Create user record in our database
                db_user = User(
                    id=auth_response.user.id,
                    email=user_data.email,
                    full_name=user_data.full_name,
                    role=user_data.role,
                    department=user_data.department,
                    phone_number=user_data.phone_number,
                    is_active=is_confirmed  # Only active if email is confirmed
                )
                
                db.add(db_user)
                db.commit()
                db.refresh(db_user)
                
                # Store session if user is confirmed
                session_record = None
                if auth_response.session:
                    session_record = UserSession(
                        id=secrets.token_urlsafe(32),
                        user_id=auth_response.user.id,
                        access_token=auth_response.session.access_token,
                        refresh_token=auth_response.session.refresh_token,
                        expires_at=datetime.fromtimestamp(auth_response.session.expires_at)
                    )
                    db.add(session_record)
                    db.commit()
                
                return {
                    "user": auth_response.user,
                    "session": auth_response.session,
                    "db_user": db_user,
                    "requires_confirmation": not is_confirmed,
                    "message": "Please check your email to confirm your account" if not is_confirmed else "User created successfully"
                }
            
            raise Exception("Failed to create user")
            
        except AuthApiError as e:
            raise Exception(f"Authentication error: {e.message}")
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create user: {str(e)}")
    
    async def sign_in(self, credentials: UserLogin, db: Session) -> Dict[str, Any]:
        """Sign in user with Supabase Auth"""
        try:
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": credentials.email,
                "password": credentials.password
            })
            
            if auth_response.user and auth_response.session:
                # Update user's last login
                db_user = db.query(User).filter(User.id == auth_response.user.id).first()
                if db_user:
                    db_user.last_login = datetime.utcnow()
                    db.commit()
                    
                    # Store session in database
                    session_record = UserSession(
                        id=secrets.token_urlsafe(32),
                        user_id=auth_response.user.id,
                        access_token=auth_response.session.access_token,
                        refresh_token=auth_response.session.refresh_token,
                        expires_at=datetime.fromtimestamp(auth_response.session.expires_at)
                    )
                    
                    db.add(session_record)
                    db.commit()
                
                return {
                    "user": auth_response.user,
                    "session": auth_response.session,
                    "db_user": db_user
                }
            
            raise Exception("Invalid credentials")
            
        except AuthApiError as e:
            raise Exception(f"Authentication error: {e.message}")
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")
    
    async def sign_out(self, access_token: str, db: Session) -> bool:
        """Sign out user and revoke session"""
        try:
            # Sign out from Supabase
            self.supabase.auth.sign_out()
            
            # Revoke session in database
            session = db.query(UserSession).filter(
                UserSession.access_token == access_token
            ).first()
            
            if session:
                session.is_revoked = True
                db.commit()
            
            return True
            
        except Exception as e:
            print(f"Sign out error: {e}")
            return False
    
    async def get_current_user(self, access_token: str, db: Session) -> Optional[User]:
        """Get current user from access token"""
        try:
            # Verify token with Supabase
            user_response = self.supabase.auth.get_user(access_token)
            
            if user_response.user:
                # Get user from database
                db_user = db.query(User).filter(
                    User.id == user_response.user.id
                ).first()
                
                return db_user
            
            return None
            
        except Exception as e:
            print(f"Get current user error: {e}")
            return None
    
    async def refresh_token(self, refresh_token: str, db: Session) -> Dict[str, Any]:
        """Refresh access token"""
        try:
            auth_response = self.supabase.auth.refresh_session(refresh_token)
            
            if auth_response.session:
                # Update session in database
                session = db.query(UserSession).filter(
                    UserSession.refresh_token == refresh_token
                ).first()
                
                if session:
                    session.access_token = auth_response.session.access_token
                    session.refresh_token = auth_response.session.refresh_token
                    session.expires_at = datetime.fromtimestamp(auth_response.session.expires_at)
                    db.commit()
                
                return {
                    "session": auth_response.session,
                    "user": auth_response.user
                }
            
            raise Exception("Failed to refresh token")
            
        except AuthApiError as e:
            raise Exception(f"Token refresh error: {e.message}")
    
    async def confirm_email(self, token: str, db: Session) -> Dict[str, Any]:
        """Confirm user email with verification token"""
        try:
            # Verify email with Supabase
            auth_response = self.supabase.auth.verify_otp({
                'token_hash': token,
                'type': 'email'
            })
            
            if auth_response.user:
                # Activate user in our database
                db_user = db.query(User).filter(User.id == auth_response.user.id).first()
                if db_user:
                    db_user.is_active = True
                    db.commit()
                    db.refresh(db_user)
                
                return {
                    "user": auth_response.user,
                    "session": auth_response.session,
                    "db_user": db_user,
                    "message": "Email confirmed successfully"
                }
            
            raise Exception("Invalid confirmation token")
            
        except AuthApiError as e:
            raise Exception(f"Email confirmation error: {e.message}")
        except Exception as e:
            raise Exception(f"Failed to confirm email: {str(e)}")

    async def resend_confirmation(self, email: str) -> bool:
        """Resend email confirmation"""
        try:
            self.supabase.auth.resend({
                'type': 'signup',
                'email': email
            })
            return True
        except AuthApiError as e:
            raise Exception(f"Failed to resend confirmation: {e.message}")

    async def reset_password(self, email: str) -> bool:
        """Send password reset email"""
        try:
            self.supabase.auth.reset_password_email(email)
            return True
        except AuthApiError as e:
            raise Exception(f"Password reset error: {e.message}")
    
    async def update_user_role(self, user_id: str, role: UserRole, db: Session) -> Optional[User]:
        """Update user role (admin only)"""
        try:
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user:
                db_user.role = role
                db.commit()
                db.refresh(db_user)
                return db_user
            return None
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to update user role: {str(e)}")


# Create a global instance
auth_service = SupabaseAuthService()
