import sys, os
sys.path.insert(0, os.path.abspath("."))
from Agent.agents.composer import compose_email

subj, body = compose_email(
    name="aione",
    company="ai1",
    tracking_link="https://passion-babbling-stingray.ngrok-free.dev/form?token=zrIvszi6TGbNLyNwZS66Ag",
)

print("--- SUBJECT ---")
print(subj)
print("--- BODY ---")
print(body)
