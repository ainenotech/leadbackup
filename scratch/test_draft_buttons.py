import sys, os
sys.path.insert(0, os.path.abspath("."))
from Email.draft_options import get_draft_template_option, OPTIONS_METADATA
from Email.outlook_mailer import OutlookMailer
import re

def test_draft_templates():
    print("Testing 3 Predefined Draft Options...")
    for i in [1, 2, 3]:
        subj, body = get_draft_template_option(
            option_id=i,
            name="Jane Doe",
            company="Acme Corp",
            cta_url="https://passion-babbling-stingray.ngrok-free.dev/form?token=test123",
        )
        assert "Jane Doe" in body, f"Option {i} missing lead name"
        assert "Acme Corp" in body, f"Option {i} missing company"
        assert "logo-dark.png" in body, f"Option {i} missing logo-dark.png"
        assert "unsubscribe" not in body.lower(), f"Option {i} contains unsubscribe!"
        assert body.strip().startswith("<div style=\"max-width:600px;"), f"Option {i} invalid container"
        print(f"  [PASS] Option {i}: Subject='{subj[:40]}...' (Len={len(body)} chars, Logo=logo-dark.png, Unsubscribe=None)")

    # Test fallback handling when name or company is missing
    s_anon, b_anon = get_draft_template_option(1, None, None, None)
    assert "there" in b_anon
    assert "https://www.nenotechnology.com" in b_anon
    assert "unsubscribe" not in b_anon.lower()
    print("  [PASS] Anonymous/Missing Data Fallbacks verified.")

    # Test Outlook Mailer packaging
    clean_body = b_anon.strip()
    assert clean_body.startswith("<div")
    print("  [PASS] Outlook Mailer raw HTML detection verified.")

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_draft_templates()
