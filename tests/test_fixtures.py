#!/usr/bin/env python3
"""
Test Fixtures - Sample data for testing
"""

import json
import base64
from datetime import datetime


def create_sample_email(email_id="test_001", subject="Test Email", body="This is a test email body.",
                        to="test@example.com", internal_date=None):
    """Create a sample email in Gmail API format."""
    if internal_date is None:
        internal_date = int(datetime.now().timestamp() * 1000)
    
    body_encoded = base64.urlsafe_b64encode(body.encode()).decode()
    
    return {
        "id": email_id,
        "threadId": email_id,
        "labelIds": ["SENT"],
        "snippet": body[:100],
        "internalDate": str(internal_date),
        "payload": {
            "headers": [
                {"name": "From", "value": "john@example.com"},
                {"name": "To", "value": to},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": datetime.fromtimestamp(internal_date/1000).isoformat()}
            ],
            "mimeType": "text/plain",
            "body": {
                "size": len(body),
                "data": body_encoded
            }
        }
    }


# Sample emails with different characteristics
SAMPLE_EMAILS = {
    "executive_brief": create_sample_email(
        email_id="exec_001",
        subject="Q2 Update",
        body="""Team,

Quick update on Q2 priorities. Three things:

1. Customer dashboard - launching next week
2. API v2 - beta in progress
3. Mobile app - pushed to Q3

Questions? Let's discuss in Thursday's all-hands.

-John""",
        to="team@example.com"
    ),
    
    "client_response": create_sample_email(
        email_id="client_001",
        subject="Re: Implementation Timeline",
        body="""Hi Sarah,

Thanks for the question. Here's the implementation timeline:

- Phase 1 (Weeks 1-2): Setup and configuration
- Phase 2 (Weeks 3-4): Data migration
- Phase 3 (Week 5): Testing and go-live

I've attached the detailed project plan. Happy to walk through it on our call tomorrow.

Best,
John""",
        to="sarah@client.com"
    ),
    
    "quick_reply": create_sample_email(
        email_id="quick_001",
        subject="Re: Meeting Time",
        body="Yup. I may be 5 min late though. I have a 10-10:30 meeting right before. Should be there by 10:35 at the latest. Let me know if that doesn't work and we can reschedule. Thanks!",
        to="colleague@example.com"
    ),
    
    "forward": create_sample_email(
        email_id="forward_001",
        subject="Fwd: Important Update",
        body="""---------- Forwarded message ---------
From: Someone Else
Date: Mon, Jan 1, 2024
Subject: Important Update

Here's the important information...""",
        to="team@example.com"
    ),
    
    "auto_reply": create_sample_email(
        email_id="auto_001",
        subject="Out of Office",
        body="Thank you for your email. I am currently out of the office and will not be checking email regularly. I will respond to your message when I return. If you need immediate assistance, please contact support@example.com.",
        to="someone@example.com"
    ),
    
    "too_short": create_sample_email(
        email_id="short_001",
        subject="Thanks",
        body="Thanks!",
        to="colleague@example.com"
    ),
    
    "mass_email": create_sample_email(
        email_id="mass_001",
        subject="Company Announcement",
        body="Hello everyone, this is a company-wide announcement about upcoming changes to our policies. Please review the attached document and provide feedback by end of week. Thank you for your attention to this important matter.",
        to="user1@example.com, user2@example.com, user3@example.com, " + ", ".join([f"user{i}@example.com" for i in range(4, 25)])
    )
}


def get_sample_email(email_type):
    """Get a sample email by type."""
    return SAMPLE_EMAILS.get(email_type)


def get_all_valid_samples():
    """Get all emails that should pass filtering."""
    return [
        SAMPLE_EMAILS["executive_brief"],
        SAMPLE_EMAILS["client_response"],
        SAMPLE_EMAILS["quick_reply"]
    ]


def get_all_invalid_samples():
    """Get all emails that should be filtered out."""
    return [
        SAMPLE_EMAILS["forward"],
        SAMPLE_EMAILS["auto_reply"],
        SAMPLE_EMAILS["too_short"],
        SAMPLE_EMAILS["mass_email"]
    ]


def create_filtered_sample(email_data, quality_score=0.75):
    """Create a filtered sample with quality metadata."""
    return {
        "id": email_data["id"],
        "original_data": email_data,
        "quality": {
            "score": quality_score,
            "body_length": 200,
            "flags": []
        },
        "filtered_at": datetime.now().isoformat()
    }


def create_enriched_sample(filtered_data, recipient_type="individual", audience="external"):
    """Create an enriched sample with metadata."""
    return {
        "id": filtered_data["id"],
        "original_data": filtered_data["original_data"],
        "quality": filtered_data["quality"],
        "enrichment": {
            "recipient_type": recipient_type,
            "audience": audience,
            "thread_position": "reply",
            "has_bullets": True,
            "paragraph_count": 3,
            "greeting": "Hi Sarah,",
            "closing": "Best, John"
        },
        "enriched_at": datetime.now().isoformat()
    }
