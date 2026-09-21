import re

sample_bodies = [
    "New booking from het suthar &nbsp; support with Support Tuesday, September 22, 2026 11:05 AM - 11:35 AM (UTC+05:30) Chennai, Kolkata",
    "New booking from MIT DHARMESHBHAI PATEL &nbsp; support with Support Friday, September 25, 2026 10:05 AM - 10:35 AM (UTC+05:30)",
    "New booking from ajay &nbsp; 15-min meeting with Support Thursday, September 17, 2026 12:05 PM - 12:20 PM (UTC)",
    "New booking from Dhruv Mali &nbsp; lead support with Support Friday, September 18, 2026 3:05 PM - 3:20 PM (UTC)",
]

for s in sample_bodies:
    # Clean HTML entities
    cleaned = s.replace("&nbsp;", " ").replace("\r\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # Extract name
    name_m = re.search(r"New booking from\s+(.+?)\s+(?:support|15-min|30-min|lead support|[a-zA-Z0-9\-_ ]+)\s+with Support", cleaned, re.IGNORECASE)
    name = name_m.group(1).strip() if name_m else "Client"
    
    # Extract service
    serv_m = re.search(r"(?:New booking from\s+.+?\s+)(.*?)\s+with Support", cleaned, re.IGNORECASE)
    service = serv_m.group(1).strip() if serv_m else "Consultation"
    
    # Extract date time
    slot_m = re.search(r"([A-Za-z]+day,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*(?:AM|PM)\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM))", cleaned, re.IGNORECASE)
    slot = slot_m.group(1).strip() if slot_m else "Scheduled Consultation"
    
    print(f"Parsed -> Name: '{name}' | Service: '{service}' | Slot: '{slot}'")
