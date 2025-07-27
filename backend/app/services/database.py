from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client with proper error handling"""
        print(f"Environment check:")
        print(f"SUPABASE_URL: {self.supabase_url}")
        print(f"SUPABASE_KEY: {'***' + self.supabase_key[-10:] if self.supabase_key else 'None'}")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        try:
            print("Attempting to create Supabase client...")
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            print("✅ Supabase client created successfully")
        except Exception as e:
            print(f"❌ Failed to create Supabase client: {type(e).__name__}: {e}")
            print(f"SUPABASE_URL format check: {self.supabase_url.startswith('https://') if self.supabase_url else 'URL is None'}")
            raise
    
    def get_client(self) -> Client:
        """Get the Supabase client instance"""
        return self.client

# Create a global instance
db_service = DatabaseService()