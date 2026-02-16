"""SMS/chat message feature extraction for phishing detection.

SMS phishing (smishing) has distinct patterns:
- Short messages (160 char limit per segment)
- Shortened URLs (bit.ly, tinyurl, etc.)
- Urgency language compressed into brief text
- Common shorthand and abbreviations
- High emoji usage
- Uppercase words for emphasis
"""

import math
import re
from typing import Dict, List


# Shortened URL domains commonly used in smishing
SHORTENED_URL_DOMAINS = {
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',
    'is.gd', 'buff.ly', 'adf.ly', 'tiny.cc', 'tr.im',
    'short.to', 'cutt.ly', 'rebrand.ly', 'shorturl.at'
}

# Common SMS shorthand abbreviations
SMS_SHORTHAND = {
    'u', 'ur', 'plz', 'pls', 'thx', 'ty', 'lol', 'omg',
    'btw', 'fyi', 'asap', 'brb', 'ttyl', 'idk', 'imo',
    'msg', 'txt', 'tmw', 'rn', 'bc', 'np', 'nvm'
}


def parse_sms(message: str) -> dict:
    """Parse SMS message and extract structured components.

    Extracts URLs, phone numbers, and analyzes message structure (multipart detection).
    Preserves unicode/emoji as they are features for smishing detection.

    Args:
        message: SMS message text to parse

    Returns:
        Dictionary containing:
            - text (str): Original message text
            - urls (List[str]): List of extracted URLs
            - phone_numbers (List[str]): List of phone number patterns
            - is_multipart (bool): True if message exceeds 160 characters

    Examples:
        >>> result = parse_sms("Visit bit.ly/abc or call 1-800-555-0123")
        >>> len(result['urls'])
        1
        >>> result['urls'][0]
        'bit.ly/abc'
        >>> len(result['phone_numbers'])
        1
        >>> result['is_multipart']
        False

        >>> result = parse_sms("URGENT! Your account has been suspended...")
        >>> result['is_multipart']  # If message > 160 chars
        True
    """
    if not message or not message.strip():
        return {
            'text': '',
            'urls': [],
            'phone_numbers': [],
            'is_multipart': False
        }

    # Extract URLs (both with and without protocol)
    # Match http(s):// URLs and shortened domains without protocol
    # Build pattern from SHORTENED_URL_DOMAINS dynamically
    escaped_domains = [domain.replace('.', r'\.') for domain in SHORTENED_URL_DOMAINS]
    shortened_pattern = '|'.join(escaped_domains)
    url_pattern = rf'https?://[^\s]+|(?:{shortened_pattern})/[^\s]+'
    urls = re.findall(url_pattern, message, re.IGNORECASE)

    # Extract phone numbers
    # Match patterns like: +1-800-555-0123, 1-800-555-0123, (800) 555-0123, 8005550123
    phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
    phone_numbers = re.findall(phone_pattern, message)
    # Filter out false positives (must have enough digits)
    phone_numbers = [p for p in phone_numbers if sum(c.isdigit() for c in p) >= 10]

    # Detect multipart (SMS segments are 160 chars for GSM-7, 70 for Unicode)
    # Use 160 as threshold for simplicity
    is_multipart = len(message) > 160

    return {
        'text': message,
        'urls': urls,
        'phone_numbers': phone_numbers,
        'is_multipart': is_multipart
    }


def extract_sms_features(message: str) -> Dict[str, float]:
    """Extract SMS-specific features for phishing detection.

    Extracts ~20 features specific to SMS/chat messages: length constraints,
    URL patterns (especially shortened URLs), phone numbers, emoji usage,
    urgency patterns, and SMS-specific linguistic features.

    These features complement NLP text features (from text_features.py) and are
    designed specifically for smishing (SMS phishing) detection.

    Args:
        message: SMS message text to analyze

    Returns:
        Dictionary with ~20 numeric features (int or float):
            Length features (4):
                - sms_length: Message length in characters
                - sms_segment_count: Number of SMS segments (ceil(len/160))
                - exceeds_single_sms: 1 if >160 chars, 0 otherwise
                - char_per_word_avg: Average characters per word

            URL features (4):
                - url_count: Number of URLs detected
                - has_shortened_url: 1 if shortened URL domain present
                - shortened_url_count: Count of shortened URLs
                - url_to_text_ratio: Total URL length / message length

            Phone features (2):
                - has_phone_number: 1 if phone pattern detected
                - phone_number_count: Count of phone patterns

            Character features (4):
                - has_emoji: 1 if emoji present
                - emoji_count: Count of emoji characters
                - uppercase_word_count: Count of ALL CAPS words
                - exclamation_density: exclamations / word count

            SMS-specific patterns (6):
                - has_call_to_action: 1 if action words present
                - has_urgency_caps: 1 if URGENT/IMPORTANT/ALERT in caps
                - has_prize_claim: 1 if prize/win pattern present
                - has_account_alert: 1 if account security pattern present
                - shorthand_ratio: SMS abbreviations / word count
                - numeric_string_count: Count of number sequences

    Examples:
        >>> features = extract_sms_features("URGENT! Your account suspended. Click bit.ly/abc123")
        >>> features['has_shortened_url']
        1
        >>> features['has_urgency_caps']
        1
        >>> features['has_account_alert']
        1
        >>> features['url_count']
        1

        >>> features = extract_sms_features("Your package has shipped. Track: ups.com/track/123")
        >>> features['has_shortened_url']
        0
        >>> features['has_urgency_caps']
        0

        >>> features = extract_sms_features("")
        >>> features['sms_length']
        0
        >>> len(features)
        20
    """
    if not message or not message.strip():
        return _get_default_sms_features()

    # Parse message structure
    parsed = parse_sms(message)
    urls = parsed['urls']
    phone_numbers = parsed['phone_numbers']

    # Length features
    sms_length = len(message)
    words = message.split()
    word_count = len(words)
    sms_segment_count = math.ceil(sms_length / 160)
    exceeds_single_sms = 1 if sms_length > 160 else 0
    char_per_word_avg = sms_length / word_count if word_count > 0 else 0.0

    # URL features
    url_count = len(urls)
    shortened_urls = [u for u in urls if any(domain in u.lower() for domain in SHORTENED_URL_DOMAINS)]
    has_shortened_url = 1 if shortened_urls else 0
    shortened_url_count = len(shortened_urls)
    total_url_length = sum(len(u) for u in urls)
    url_to_text_ratio = total_url_length / sms_length if sms_length > 0 else 0.0

    # Phone features
    has_phone_number = 1 if phone_numbers else 0
    phone_number_count = len(phone_numbers)

    # Emoji detection
    # Unicode ranges for common emoji:
    # - Emoticons: U+1F600 - U+1F64F
    # - Symbols & Pictographs: U+1F300 - U+1F5FF
    # - Transport & Map: U+1F680 - U+1F6FF
    # - Supplemental Symbols: U+1F900 - U+1F9FF
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF]'
    emojis = re.findall(emoji_pattern, message)
    has_emoji = 1 if emojis else 0
    emoji_count = len(emojis)

    # Uppercase word detection
    uppercase_words = [w for w in words if w.isupper() and len(w) > 1]
    uppercase_word_count = len(uppercase_words)

    # Exclamation density
    exclamation_count = message.count('!')
    exclamation_density = exclamation_count / word_count if word_count > 0 else 0.0

    # SMS-specific pattern detection
    message_lower = message.lower()

    # Call to action keywords
    call_to_action_keywords = ['call', 'text', 'reply', 'click', 'visit', 'tap', 'download', 'install']
    has_call_to_action = 1 if any(keyword in message_lower for keyword in call_to_action_keywords) else 0

    # Urgency in caps
    urgency_caps_pattern = r'\b(URGENT|IMPORTANT|ALERT|IMMEDIATE|ACTION REQUIRED|TIME SENSITIVE)\b'
    has_urgency_caps = 1 if re.search(urgency_caps_pattern, message) else 0

    # Prize/claim patterns
    prize_patterns = ['won', 'prize', 'claim', 'winner', 'congratulations', 'reward', 'gift', 'free']
    has_prize_claim = 1 if any(pattern in message_lower for pattern in prize_patterns) else 0

    # Account alert patterns
    account_patterns = ['account', 'suspended', 'verify', 'confirm', 'locked', 'security', 'unauthorized']
    has_account_alert = 1 if any(pattern in message_lower for pattern in account_patterns) else 0

    # Shorthand ratio
    words_lower = [w.lower() for w in words]
    shorthand_count = sum(1 for w in words_lower if w in SMS_SHORTHAND)
    shorthand_ratio = shorthand_count / word_count if word_count > 0 else 0.0

    # Numeric string count (sequences of 3+ digits)
    numeric_sequences = re.findall(r'\d{3,}', message)
    numeric_string_count = len(numeric_sequences)

    return {
        # Length features (4)
        'sms_length': sms_length,
        'sms_segment_count': sms_segment_count,
        'exceeds_single_sms': exceeds_single_sms,
        'char_per_word_avg': char_per_word_avg,
        # URL features (4)
        'url_count': url_count,
        'has_shortened_url': has_shortened_url,
        'shortened_url_count': shortened_url_count,
        'url_to_text_ratio': url_to_text_ratio,
        # Phone features (2)
        'has_phone_number': has_phone_number,
        'phone_number_count': phone_number_count,
        # Character features (4)
        'has_emoji': has_emoji,
        'emoji_count': emoji_count,
        'uppercase_word_count': uppercase_word_count,
        'exclamation_density': exclamation_density,
        # SMS-specific patterns (6)
        'has_call_to_action': has_call_to_action,
        'has_urgency_caps': has_urgency_caps,
        'has_prize_claim': has_prize_claim,
        'has_account_alert': has_account_alert,
        'shorthand_ratio': shorthand_ratio,
        'numeric_string_count': numeric_string_count,
    }


def _get_default_sms_features() -> Dict[str, float]:
    """Return default feature values for empty SMS messages.

    Returns all zeros for empty or whitespace-only messages.

    Returns:
        Dictionary with all 20 SMS features set to 0 or 0.0
    """
    return {
        # Length features
        'sms_length': 0,
        'sms_segment_count': 0,
        'exceeds_single_sms': 0,
        'char_per_word_avg': 0.0,
        # URL features
        'url_count': 0,
        'has_shortened_url': 0,
        'shortened_url_count': 0,
        'url_to_text_ratio': 0.0,
        # Phone features
        'has_phone_number': 0,
        'phone_number_count': 0,
        # Character features
        'has_emoji': 0,
        'emoji_count': 0,
        'uppercase_word_count': 0,
        'exclamation_density': 0.0,
        # SMS-specific patterns
        'has_call_to_action': 0,
        'has_urgency_caps': 0,
        'has_prize_claim': 0,
        'has_account_alert': 0,
        'shorthand_ratio': 0.0,
        'numeric_string_count': 0,
    }
