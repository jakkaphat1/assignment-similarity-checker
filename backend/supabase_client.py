from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

sb_url: str = os.environ.get("SUPABASE_URL")
sb_key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(sb_url, sb_key)
