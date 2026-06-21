from db.session import engine
from sqlalchemy import text

print("Attempting to connect to the database specified in .env...")

try:
    with engine.connect() as conn:
        print("\n✅ CONNECTION SUCCESSFUL!")
        
        # This query proves it's PostgreSQL (Supabase) and not SQLite
        version = conn.execute(text("SELECT version();")).fetchone()
        print(f"Database Engine: {version[0][:40]}...\n")
        
        # Let's see how many appointments you have saved in the cloud!
        apps = conn.execute(text("SELECT COUNT(*) FROM appointments;")).fetchone()
        print(f"Total Appointments stored in Supabase: {apps[0]}")
        
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
