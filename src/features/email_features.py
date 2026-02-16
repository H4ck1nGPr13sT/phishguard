"""Email feature extraction module for phishing detection.

This module provides functions to parse email files (.eml) and raw email text,
extract authentication headers (SPF, DKIM, DMARC), sender information, and
structural email features for phishing detection.
"""

import re
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import Dict

from bs4 import BeautifulSoup


def parse_email(raw_email: bytes) -> dict:
    """Parse raw email bytes into structured components.

    Extracts headers, body text, and metadata from raw email content.
    Handles multipart emails by preferring text/plain over text/html.
    For HTML-only emails, extracts plain text using BeautifulSoup.

    Args:
        raw_email: Raw email bytes (from .eml file or SMTP)

    Returns:
        Dictionary containing:
            - headers: Dict of email headers (From, To, Subject, etc.)
            - body: Extracted plain text body
            - is_html: Whether body was extracted from HTML
            - has_attachments: Whether email has attachments

    Examples:
        >>> raw = b"From: user@example.com\\nSubject: Test\\n\\nBody text"
        >>> result = parse_email(raw)
        >>> result['headers']['Subject']
        'Test'
        >>> result['body']
        'Body text'
    """
    if not raw_email:
        return {
            'headers': {},
            'body': '',
            'is_html': False,
            'has_attachments': False,
        }

    try:
        # Parse with RFC 5322 compliant policy
        msg = message_from_bytes(raw_email, policy=policy.default)
    except Exception:
        # Fallback for malformed emails
        return {
            'headers': {},
            'body': '',
            'is_html': False,
            'has_attachments': False,
        }

    # Extract headers
    headers = {
        'From': msg.get('From', ''),
        'To': msg.get('To', ''),
        'Subject': msg.get('Subject', ''),
        'Date': msg.get('Date', ''),
        'Reply-To': msg.get('Reply-To', ''),
        'Authentication-Results': msg.get('Authentication-Results', ''),
    }

    # Extract body text
    body = ''
    is_html = False
    has_attachments = False

    if msg.is_multipart():
        # Handle multipart emails
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))

            # Check for attachments
            if 'attachment' in content_disposition:
                has_attachments = True
                continue

            # Prefer text/plain over text/html
            if content_type == 'text/plain' and not body:
                try:
                    body = part.get_content()
                except Exception:
                    continue
            elif content_type == 'text/html' and not body:
                try:
                    html_content = part.get_content()
                    soup = BeautifulSoup(html_content, 'lxml')
                    body = soup.get_text(separator=' ', strip=True)
                    is_html = True
                except Exception:
                    continue
    else:
        # Single-part email
        content_type = msg.get_content_type()
        try:
            if content_type == 'text/plain':
                body = msg.get_content()
            elif content_type == 'text/html':
                html_content = msg.get_content()
                soup = BeautifulSoup(html_content, 'lxml')
                body = soup.get_text(separator=' ', strip=True)
                is_html = True
        except Exception:
            pass

    return {
        'headers': headers,
        'body': body.strip() if body else '',
        'is_html': is_html,
        'has_attachments': has_attachments,
    }


def extract_email_header_features(msg: EmailMessage) -> Dict[str, float]:
    """Extract numeric features from email headers for phishing detection.

    Analyzes authentication headers (SPF, DKIM, DMARC), sender information,
    subject line patterns, and header structure to detect phishing indicators.

    Features extracted (~15 features):
        - Authentication: SPF/DKIM/DMARC pass status
        - Sender: domain length, suspicious TLD, Reply-To mismatch
        - Subject: length, urgent keywords, Re:/Fwd: prefixes
        - Structure: header count, X-headers, Received headers

    Args:
        msg: Parsed EmailMessage object from email.message_from_bytes()

    Returns:
        Dictionary mapping feature names to numeric values (0 or 1 for binary,
        integers for counts, floats for ratios).

    Examples:
        >>> from email import message_from_bytes, policy
        >>> raw = b"From: user@example.com\\nSubject: Test\\n\\n"
        >>> msg = message_from_bytes(raw, policy=policy.default)
        >>> features = extract_email_header_features(msg)
        >>> features['sender_domain_length']
        11
        >>> features['has_urgent_subject']
        0
    """
    if not msg:
        return _get_default_email_header_features()

    features = {}

    # Authentication headers (from Authentication-Results)
    auth_results = msg.get('Authentication-Results', '').lower()
    features['has_spf_pass'] = 1 if 'spf=pass' in auth_results else 0
    features['has_dkim_pass'] = 1 if 'dkim=pass' in auth_results else 0
    features['has_dmarc_pass'] = 1 if 'dmarc=pass' in auth_results else 0

    # Sender domain features
    from_header = msg.get('From', '')
    sender_domain = extract_domain_from_email(from_header)
    features['sender_domain_length'] = len(sender_domain)

    # Suspicious TLD check
    suspicious_tlds = {'tk', 'ml', 'ga', 'cf', 'gq', 'xyz'}
    tld = sender_domain.split('.')[-1] if '.' in sender_domain else ''
    features['from_domain_suspicious'] = 1 if tld.lower() in suspicious_tlds else 0

    # Reply-To mismatch detection
    reply_to = msg.get('Reply-To', '')
    reply_to_domain = extract_domain_from_email(reply_to) if reply_to else ''
    features['reply_to_mismatch'] = 1 if (reply_to and reply_to_domain != sender_domain) else 0

    # Recipient count
    to_header = msg.get('To', '')
    # Count comma-separated addresses
    recipient_count = len([addr.strip() for addr in to_header.split(',') if addr.strip()])
    features['has_multiple_recipients'] = 1 if recipient_count > 1 else 0

    # Subject line features
    subject = msg.get('Subject', '')
    features['subject_length'] = len(subject)

    # Urgent keywords
    urgent_keywords = ['urgent', 'important', 'action required', 'immediate', 'verify', 'suspend']
    subject_lower = subject.lower()
    features['has_urgent_subject'] = 1 if any(kw in subject_lower for kw in urgent_keywords) else 0

    # Subject prefixes
    features['has_re_prefix'] = 1 if subject.startswith(('Re:', 'RE:')) else 0
    features['has_fwd_prefix'] = 1 if subject.startswith(('Fwd:', 'FW:', 'Fw:')) else 0

    # Header structure features
    all_headers = list(msg.keys())
    features['header_count'] = len(all_headers)

    # Custom X-headers (can indicate routing/spam filtering)
    x_headers = [h for h in all_headers if h.startswith('X-')]
    features['has_x_headers'] = 1 if x_headers else 0

    # Received headers (email routing path)
    received_headers = msg.get_all('Received', [])
    features['has_received_headers'] = 1 if received_headers else 0
    features['received_header_count'] = len(received_headers)

    return features


def extract_domain_from_email(email_address: str) -> str:
    """Extract domain from email address.

    Handles various email formats:
        - "Name <user@domain.com>" → "domain.com"
        - "user@domain.com" → "domain.com"
        - "invalid" → ""

    Args:
        email_address: Email address string (may include display name)

    Returns:
        Domain portion of email address, or empty string if invalid

    Examples:
        >>> extract_domain_from_email("John Doe <john@example.com>")
        'example.com'
        >>> extract_domain_from_email("user@test.org")
        'test.org'
        >>> extract_domain_from_email("invalid")
        ''
    """
    if not email_address:
        return ''

    # Extract domain using regex
    # Matches @domain.tld pattern
    match = re.search(r'@([\w.-]+)', email_address)
    if match:
        return match.group(1)

    return ''


def _get_default_email_header_features() -> Dict[str, float]:
    """Return default feature values for empty/invalid emails.

    Used as fallback when email cannot be parsed or is empty.
    All features set to 0 to indicate no phishing indicators detected.

    Returns:
        Dictionary with all 15 email header features set to 0
    """
    return {
        # Authentication
        'has_spf_pass': 0,
        'has_dkim_pass': 0,
        'has_dmarc_pass': 0,
        # Sender
        'sender_domain_length': 0,
        'from_domain_suspicious': 0,
        'reply_to_mismatch': 0,
        # Recipients
        'has_multiple_recipients': 0,
        # Subject
        'subject_length': 0,
        'has_urgent_subject': 0,
        'has_re_prefix': 0,
        'has_fwd_prefix': 0,
        # Structure
        'header_count': 0,
        'has_x_headers': 0,
        'has_received_headers': 0,
        'received_header_count': 0,
    }
