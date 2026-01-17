import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
service_key: str = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(url, key)
supabase_service: Client = create_client(url, service_key)


def get_supabase_client() -> Client:
    return supabase

def get_supabase_service_client() -> Client:
    return supabase_service