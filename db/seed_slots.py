import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, timedelta, time
from db.models import Slot, Base
from db.session import engine, SessionLocal

def seed_slots():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if slots already exist
    existing = db.query(Slot).count()
    if existing > 0:
        print(f"Found {existing} existing slots. Adding more if needed...")

    # Seed slots for the next 7 days
    start_date = date.today()
    slots_to_add = []
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        # Include weekends so it works during the hackathon!
        # Add slots at 9:00, 11:00, 14:00, 16:00
        times = [time(9, 0), time(11, 0), time(14, 0), time(16, 0)]
        for t in times:
            # Check if this specific slot already exists
            exists = db.query(Slot).filter(Slot.slot_date == current_date, Slot.slot_time == t).first()
            if not exists:
                slots_to_add.append(Slot(slot_date=current_date, slot_time=t))
            
    db.add_all(slots_to_add)
    db.commit()
    print(f"Successfully seeded {len(slots_to_add)} slots.")
    db.close()

if __name__ == "__main__":
    seed_slots()
