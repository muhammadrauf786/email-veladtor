import sys
import re
import subprocess
import socket
import smtplib
import os
import concurrent.futures

def validate_format(email):
    """Checks if the email format is valid."""
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def get_mx_records(domain):
    """Gets MX records for a domain using nslookup."""
    try:
        result = subprocess.run(
            ["nslookup", "-type=mx", domain],
            capture_output=True,
            text=True,
            timeout=5
        )
        mx_records = []
        for line in result.stdout.splitlines():
            if "mail exchanger =" in line:
                mx_server = line.split("mail exchanger =")[-1].strip()
                mx_records.append(mx_server)
        return mx_records
    except Exception:
        return []

def check_smtp(email, mx_records):
    """Attempts to check deliverability via SMTP RCPT TO."""
    if not mx_records:
        return "INVALID"
    for mx in mx_records:
        try:
            with smtplib.SMTP(mx, port=25, timeout=10) as server:
                server.helo("deliverability-check.com")
                server.mail("verify@deliverability-check.com")
                code, message = server.rcpt(email)
                if code in [250, 251]:
                    return "VALID"
                else:
                    return "RISKY"
        except (socket.timeout, socket.error, smtplib.SMTPException):
            continue
    return "RISKY"

def process_email(email):
    email = email.strip()
    if not email:
        return None
    if '@' not in email:
        return "INVALID"
    domain = email.split('@')[-1]
    if not validate_format(email):
        return "INVALID"
    mx_records = get_mx_records(domain)
    if not mx_records:
        return "INVALID"
    return check_smtp(email, mx_records)

def main():
    if len(sys.argv) < 2:
        return

    raw_input = ""
    if os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], 'r') as f:
            raw_input = f.read()
    else:
        raw_input = " ".join(sys.argv[1:])

    raw_input = raw_input.replace(';', ' ').replace(',', ' ').replace('\n', ' ')
    emails = raw_input.split()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(process_email, emails))
        
    for result in results:
        if result:
            print(result, flush=True)

if __name__ == "__main__":
    main()
