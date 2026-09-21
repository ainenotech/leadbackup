with open('dashboard.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'Permanent Excel Archives' in line or 'PERMANENT ARCHIVE' in line or 'Customer Inquiries' in line:
            print(f"{i}: {line.encode('ascii', 'ignore').decode().strip()}")
