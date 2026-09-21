sample = """New booking from

het suthar

support with
Support

Tuesday, September 22, 2026
11:05 AM - 11:35 AM

(UTC+05:30) Chennai, Kolkata, Mumbai, New Delhi"""

lines = [l.strip() for l in sample.split("\n") if l.strip()]
name = ""
service = "Consultation"
slot = ""

for i, l in enumerate(lines):
    if "new booking from" in l.lower() and i + 1 < len(lines):
        name = lines[i+1]
    if "with support" in l.lower():
        service = lines[i].replace("with Support", "").strip() or (lines[i-1] if i > 0 else "Consultation")
    if any(day in l for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
        time_part = lines[i+1] if i + 1 < len(lines) and ("AM" in lines[i+1] or "PM" in lines[i+1]) else ""
        slot = f"{l} {time_part}".strip()

print(f"Name: '{name}' | Service: '{service}' | Slot: '{slot}'")
