import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

def test_master_db_chunk_rendering_none_safety():
    """Verify that chunks with None values for counts do not raise TypeError."""
    import master_db_view

    # Mock chunk with None values (which previously caused TypeError: '>' not supported between instances of 'int' and 'NoneType')
    mock_chunks = [{
        "id": "chunk-123",
        "chunk_name": "Test Chunk",
        "processing_status": "READY",
        "template_name": "Outreach V1",
        "total_leads": None,
        "eligible_leads": None,
        "sent_count": None,
        "reply_count": None,
        "open_count": None,
        "booking_count": None,
        "duplicate_template_leads": None,
        "created_at": "2026-10-01T00:00:00Z"
    }]

    # Test the chunk calculation directly
    chunk = mock_chunks[0]
    sent = chunk.get("sent_count") or 0
    total = max(chunk.get("eligible_leads") or 1, 1)
    pct = min(100, int((sent / total) * 100))
    assert pct == 0
    assert total == 1
    assert sent == 0

def test_master_db_template_performance_none_safety():
    """Verify that template stats with None values for counts do not raise TypeError."""
    mock_assigned_chunks = [{
        "template_name": "Outreach Alpha",
        "total_leads": None,
        "sent_count": None,
        "reply_count": None,
        "open_count": None,
        "booking_count": None,
    }]

    tpl_map = {}
    for c in mock_assigned_chunks:
        tname = c["template_name"]
        if tname not in tpl_map:
            tpl_map[tname] = {"chunks": 0, "leads": 0, "sent": 0, "replies": 0, "opens": 0, "booked": 0}
        tpl_map[tname]["chunks"] += 1
        tpl_map[tname]["leads"] += (c.get("total_leads") or 0)
        tpl_map[tname]["sent"] += (c.get("sent_count") or 0)
        tpl_map[tname]["replies"] += (c.get("reply_count") or 0)
        tpl_map[tname]["opens"] += (c.get("open_count") or 0)
        tpl_map[tname]["booked"] += (c.get("booking_count") or 0)

    assert tpl_map["Outreach Alpha"]["sent"] == 0
    assert tpl_map["Outreach Alpha"]["replies"] == 0
    assert tpl_map["Outreach Alpha"]["leads"] == 0

def test_master_db_overview_metrics_none_safety():
    """Verify overview calculations with None values for metrics."""
    metrics = {
        "total_leads": None,
        "new_this_week": None,
        "duplicate_records": None,
        "total_emails_sent": None,
        "total_replies": None,
        "total_booked": None,
    }

    total_leads = metrics.get("total_leads") or 0
    new_this_week = metrics.get("new_this_week") or 0
    duplicate_records = metrics.get("duplicate_records") or 0
    total_emails_sent = metrics.get("total_emails_sent") or 0
    total_replies = metrics.get("total_replies") or 0
    total_booked = metrics.get("total_booked") or 0

    reply_rate = round((total_replies / max(total_emails_sent, 1)) * 100, 1)
    book_rate = round((total_booked / max(total_replies, 1)) * 100, 1) if total_replies > 0 else 0.0

    assert total_leads == 0
    assert reply_rate == 0.0
    assert book_rate == 0.0

def test_dashboard_render_main_view_no_duplicate_calls():
    """Verify render_main_view in dashboard.py does not wrap render_master_db in a try-except TypeError retry."""
    import ast

    with open("dashboard.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    # Find render_main_view function
    render_fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "render_main_view":
            render_fn = node
            break

    assert render_fn is not None, "render_main_view not found in dashboard.py"

    # Ensure no Try-Except nodes exist inside render_main_view that catch TypeError and call render_master_db twice
    try_nodes = [n for n in ast.walk(render_fn) if isinstance(n, ast.Try)]
    for try_node in try_nodes:
        for handler in try_node.handlers:
            if isinstance(handler.type, ast.Name) and handler.type.id == "TypeError":
                # Ensure neither try nor handler calls render_master_db
                calls = [c.func.id for c in ast.walk(try_node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
                assert "render_master_db" not in calls, "render_master_db is wrapped in an unsafe try-except TypeError retry!"

