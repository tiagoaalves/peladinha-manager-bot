from supabase import create_client
import os


class BaseManager:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            print("Supabase client created successfully")
        except Exception as e:
            print(f"Error creating Supabase client: {e}")
            raise
