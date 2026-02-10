"""Nazario phishing corpus parser.

Parses phishing emails from Nazario corpus (mbox format) and extracts URLs,
metadata, and email content.

Corpus: https://monkey.org/~jose/phishing/
Citation: Jose Nazario's Phishing Corpus (4558+ phishing emails)
"""

import logging
import mailbox
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger('phishguard.downloaders.nazario')


def parse_nazario_corpus(mbox_path: Path) -> pd.DataFrame:
    """Parse Nazario phishing corpus from mbox file.

    Parses mbox-format phishing email corpus, extracting URLs, subject lines,
    sender addresses, timestamps, and body content. Each unique URL per email
    becomes a separate sample (one email may contain multiple phishing URLs).

    Args:
        mbox_path: Path to .mbox file containing phishing emails

    Returns:
        DataFrame with columns:
            - url (str): Extracted URL from email body
            - label (int): Always 1 (all Nazario emails are phishing)
            - timestamp (datetime): Email date header
            - source (str): Always 'nazario'
            - subject (str): Email subject line
            - from_addr (str): Email From address
            - content (str): Email body text (first 1000 chars)

    Raises:
        FileNotFoundError: If mbox_path doesn't exist
        ValueError: If mbox file is empty or malformed

    Example:
        >>> df = parse_nazario_corpus(Path('/data/nazario.mbox'))
        >>> print(f"Extracted {len(df)} URLs from phishing emails")
        >>> print(df[['url', 'subject']].head())
    """
    if not mbox_path.exists():
        raise FileNotFoundError(f"Nazario corpus not found at {mbox_path}")

    logger.info(f"Parsing Nazario corpus from {mbox_path}")

    try:
        mbox = mailbox.mbox(str(mbox_path))
    except Exception as e:
        raise ValueError(f"Failed to open mbox file: {e}")

    emails = []
    message_count = 0

    # Get total message count for progress bar (may be slow for large files)
    try:
        total_messages = len(mbox)
    except:
        total_messages = None  # Unknown length

    for message in tqdm(mbox, desc="Parsing Nazario corpus", total=total_messages):
        message_count += 1

        # Extract email body
        body = _extract_body(message)

        # Extract all URLs from body
        urls = _extract_urls(body)

        if not urls:
            # No URLs found, skip this email
            continue

        # Parse timestamp
        date_str = message.get('Date', '')
        try:
            timestamp = parsedate_to_datetime(date_str)
        except Exception as e:
            logger.debug(f"Failed to parse date '{date_str}': {e}")
            timestamp = None

        # Create one row per unique URL per email
        for url in set(urls):  # Deduplicate URLs within same email
            email_data = {
                'url': url,
                'label': 1,  # All Nazario emails are phishing
                'timestamp': timestamp,
                'source': 'nazario',
                'subject': message.get('Subject', ''),
                'from_addr': message.get('From', ''),
                'content': body[:1000]  # First 1000 chars only
            }
            emails.append(email_data)

    if not emails:
        logger.warning(f"No URLs extracted from {message_count} emails in corpus")
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=[
            'url', 'label', 'timestamp', 'source', 'subject', 'from_addr', 'content'
        ])

    df = pd.DataFrame(emails)
    logger.info(
        f"Parsed {message_count} emails, extracted {len(df)} URL samples "
        f"({len(df['url'].unique())} unique URLs)"
    )

    return df


def _extract_body(message: mailbox.mboxMessage) -> str:
    """Extract text body from email message.

    Handles multipart messages and various encodings.

    Args:
        message: Email message object

    Returns:
        Email body as string
    """
    body = ""

    if message.is_multipart():
        # Walk through message parts
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    # Try multiple encodings
                    for encoding in ['utf-8', 'latin-1', 'windows-1252', 'ascii']:
                        try:
                            body += payload.decode(encoding)
                            break
                        except (UnicodeDecodeError, AttributeError):
                            continue
                except Exception as e:
                    logger.debug(f"Failed to extract part payload: {e}")
    else:
        # Single-part message
        try:
            payload = message.get_payload(decode=True)
            # Try multiple encodings
            for encoding in ['utf-8', 'latin-1', 'windows-1252', 'ascii']:
                try:
                    body = payload.decode(encoding) if payload else message.get_payload()
                    break
                except (UnicodeDecodeError, AttributeError):
                    continue
        except Exception as e:
            logger.debug(f"Failed to extract payload: {e}")
            body = str(message.get_payload())

    return body


def _extract_urls(text: str) -> List[str]:
    """Extract all HTTP(S) URLs from text.

    Args:
        text: Text to extract URLs from

    Returns:
        List of URLs found in text
    """
    # URL regex pattern - matches http:// and https:// URLs
    # Stops at whitespace, quotes, or angle brackets
    url_pattern = r'https?://[^\s<>"\']+'

    urls = re.findall(url_pattern, text, re.IGNORECASE)

    # Clean up URLs - remove trailing punctuation that might be sentence endings
    cleaned_urls = []
    for url in urls:
        # Remove trailing punctuation (., ,, ;, :, ), ], etc.)
        url = url.rstrip('.,;:)]\'"')
        if url:
            cleaned_urls.append(url)

    return cleaned_urls
