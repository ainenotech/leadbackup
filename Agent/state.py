from typing import Optional, TypedDict


class LeadState(TypedDict, total=False):
    lead_id: str
    email: str
    name: Optional[str]
    company: Optional[str]
    last_activity_date: Optional[str]
    last_deal_stage: Optional[str]
    tracking_link: Optional[str]

    subject: str
    body: str
