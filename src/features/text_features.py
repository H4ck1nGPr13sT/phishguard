"""NLP-based text feature extraction for email/SMS phishing detection.

This module extracts linguistic features from text content:
- Lexical features (character counts, word patterns, n-grams)
- Syntactic features (POS tag distributions, sentence structure)
- Stylometric features (readability, complexity, lexical diversity)
- Sentiment features (urgency, threat indicators)

Pattern: Similar to url_features.py, this provides TextFeatureExtractor class
that can be instantiated once and reused for multiple texts.
"""

import re
from typing import Dict

import spacy
import textstat


class TextFeatureExtractor:
    """Extract NLP features from text content.

    This class provides methods to extract ~50 linguistic features from email
    bodies and SMS messages for phishing detection. Features are divided into
    four categories: lexical, syntactic, stylometric, and sentiment.

    The spaCy model is loaded once at initialization (not per extraction) for
    efficiency. Named entity recognition (NER) is disabled as it's not needed
    for our feature set, reducing processing time.

    Example:
        >>> extractor = TextFeatureExtractor()
        >>> text = "Urgent! Verify your account now."
        >>> features = extractor.extract_all_features(text)
        >>> features['has_urgency']
        1
        >>> features['word_count']
        5
    """

    def __init__(self):
        """Initialize extractor with spaCy model.

        Loads en_core_web_sm model with NER disabled for faster processing.
        The model provides POS tagging and dependency parsing needed for
        syntactic features.
        """
        # Load spaCy model once (disable NER for speed)
        # en_core_web_sm is ~15MB and includes POS tagging
        self.nlp = spacy.load("en_core_web_sm", disable=["ner"])

    def extract_all_features(self, text: str) -> Dict[str, float]:
        """Extract all NLP features from text.

        Combines lexical, syntactic, stylometric, and sentiment features into
        a single feature dictionary suitable for machine learning models.

        Args:
            text: Input text to extract features from

        Returns:
            Dictionary with ~50 numeric features (int or float).
            Returns default zeros for empty/whitespace-only text.

        Example:
            >>> extractor = TextFeatureExtractor()
            >>> features = extractor.extract_all_features("Hello world!")
            >>> len(features)
            50
        """
        if not text or not text.strip():
            return _get_default_text_features()

        features = {}
        features.update(self.extract_lexical_features(text))
        features.update(self.extract_syntactic_features(text))
        features.update(self.extract_stylometric_features(text))
        features.update(self.extract_sentiment_features(text))
        return features

    def extract_lexical_features(self, text: str) -> Dict[str, float]:
        """Extract lexical features from text.

        Lexical features capture surface-level characteristics: text length,
        word counts, character distributions, and pattern occurrences.

        Args:
            text: Input text

        Returns:
            Dictionary with 15 lexical features:
                - text_length: Total character count
                - word_count: Number of words (split by whitespace)
                - avg_word_length: Mean word length in characters
                - digit_count: Count of digit characters
                - digit_ratio: Proportion of digits (0-1)
                - uppercase_count: Count of uppercase letters
                - uppercase_ratio: Proportion of uppercase (0-1)
                - exclamation_count: Count of ! characters
                - question_count: Count of ? characters
                - dollar_count: Count of $ characters
                - url_count: Count of http/https patterns
                - email_count: Count of @domain patterns
                - phone_pattern_count: Count of phone-like patterns
                - special_char_ratio: Non-alphanumeric proportion
                - whitespace_ratio: Whitespace proportion
        """
        words = text.split()
        text_len = len(text)

        # Word statistics
        word_count = len(words)
        avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0.0

        # Character counts
        digit_count = sum(c.isdigit() for c in text)
        uppercase_count = sum(c.isupper() for c in text)
        special_char_count = len(re.findall(r'[^a-zA-Z0-9\s]', text))
        whitespace_count = sum(c.isspace() for c in text)

        # Pattern counts
        url_count = len(re.findall(r'https?://', text, re.IGNORECASE))
        email_count = len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text))
        phone_pattern_count = len(re.findall(
            r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            text
        ))

        return {
            'text_length': text_len,
            'word_count': word_count,
            'avg_word_length': avg_word_length,
            'digit_count': digit_count,
            'digit_ratio': digit_count / text_len if text_len > 0 else 0.0,
            'uppercase_count': uppercase_count,
            'uppercase_ratio': uppercase_count / text_len if text_len > 0 else 0.0,
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'dollar_count': text.count('$'),
            'url_count': url_count,
            'email_count': email_count,
            'phone_pattern_count': phone_pattern_count,
            'special_char_ratio': special_char_count / text_len if text_len > 0 else 0.0,
            'whitespace_ratio': whitespace_count / text_len if text_len > 0 else 0.0,
        }

    def extract_syntactic_features(self, text: str) -> Dict[str, float]:
        """Extract syntactic features using spaCy POS tagging.

        Syntactic features capture grammatical structure: sentence counts,
        part-of-speech distributions, and imperative verb usage (common in
        phishing commands like "Click here", "Verify now").

        Args:
            text: Input text

        Returns:
            Dictionary with 15 syntactic features:
                - sentence_count: Number of sentences
                - avg_sentence_length: Mean tokens per sentence
                - token_count: Total token count
                - verb_count, verb_ratio: VERB POS tag count and proportion
                - noun_count, noun_ratio: NOUN POS tag count and proportion
                - pronoun_count, pronoun_ratio: PRON POS tag count and proportion
                - adjective_count, adjective_ratio: ADJ POS tag count and proportion
                - adverb_count, adverb_ratio: ADV POS tag count and proportion
                - punct_count: PUNCT token count
                - imperative_verb_count: Verbs at sentence start (commands)
        """
        doc = self.nlp(text)

        # Sentence statistics
        sentences = list(doc.sents)
        sentence_count = len(sentences)
        token_count = len(doc)
        avg_sentence_length = token_count / sentence_count if sentence_count > 0 else 0.0

        # POS tag counts
        verb_count = sum(1 for token in doc if token.pos_ == 'VERB')
        noun_count = sum(1 for token in doc if token.pos_ == 'NOUN')
        pronoun_count = sum(1 for token in doc if token.pos_ == 'PRON')
        adjective_count = sum(1 for token in doc if token.pos_ == 'ADJ')
        adverb_count = sum(1 for token in doc if token.pos_ == 'ADV')
        punct_count = sum(1 for token in doc if token.pos_ == 'PUNCT')

        # Imperative verbs (verbs at sentence start - indicative of commands)
        imperative_verb_count = 0
        for sent in sentences:
            if len(sent) > 0 and sent[0].pos_ == 'VERB':
                imperative_verb_count += 1

        return {
            'sentence_count': sentence_count,
            'avg_sentence_length': avg_sentence_length,
            'token_count': token_count,
            'verb_count': verb_count,
            'verb_ratio': verb_count / token_count if token_count > 0 else 0.0,
            'noun_count': noun_count,
            'noun_ratio': noun_count / token_count if token_count > 0 else 0.0,
            'pronoun_count': pronoun_count,
            'pronoun_ratio': pronoun_count / token_count if token_count > 0 else 0.0,
            'adjective_count': adjective_count,
            'adjective_ratio': adjective_count / token_count if token_count > 0 else 0.0,
            'adverb_count': adverb_count,
            'adverb_ratio': adverb_count / token_count if token_count > 0 else 0.0,
            'punct_count': punct_count,
            'imperative_verb_count': imperative_verb_count,
        }

    def extract_stylometric_features(self, text: str) -> Dict[str, float]:
        """Extract stylometric (writing style) features.

        Stylometric features measure text complexity and readability using
        established metrics from textstat library. Lower readability scores
        and higher complexity may indicate automated/template-based phishing.

        Args:
            text: Input text

        Returns:
            Dictionary with 10 stylometric features:
                - flesch_reading_ease: Readability (0-100, higher = easier)
                - flesch_kincaid_grade: US grade level required to understand
                - gunning_fog: Years of formal education needed
                - smog_index: Simple Measure of Gobbledygook
                - coleman_liau_index: Grade level based on characters
                - automated_readability_index: Grade level (character-based)
                - syllable_count: Total syllable count
                - lexicon_count: Total word count (excluding punctuation)
                - difficult_words: Words not on common word list
                - lexical_diversity: Unique words / total words (0-1)

        Note:
            Readability metrics may return negative values for very short or
            unusual texts. These are valid outputs from textstat library.
        """
        words = text.split()
        word_count = len(words)

        # Lexical diversity (type-token ratio)
        unique_words = len(set(words))
        lexical_diversity = unique_words / word_count if word_count > 0 else 0.0

        return {
            'flesch_reading_ease': textstat.flesch_reading_ease(text),
            'flesch_kincaid_grade': textstat.flesch_kincaid_grade(text),
            'gunning_fog': textstat.gunning_fog(text),
            'smog_index': textstat.smog_index(text),
            'coleman_liau_index': textstat.coleman_liau_index(text),
            'automated_readability_index': textstat.automated_readability_index(text),
            'syllable_count': textstat.syllable_count(text),
            'lexicon_count': textstat.lexicon_count(text, removepunct=True),
            'difficult_words': textstat.difficult_words(text),
            'lexical_diversity': lexical_diversity,
        }

    def extract_sentiment_features(self, text: str) -> Dict[str, float]:
        """Extract sentiment/urgency features for phishing detection.

        Sentiment features identify phishing-specific language patterns:
        urgency keywords ("urgent", "immediately"), threats ("suspended",
        "locked"), action requests ("click", "verify"), and reward claims
        ("prize", "won").

        CRITICAL: Does NOT use stop words filtering - words like "your", "now",
        "urgent" are important phishing indicators per research.

        Args:
            text: Input text

        Returns:
            Dictionary with 10 sentiment features:
                - urgency_keyword_count: Count of urgency words
                - threat_keyword_count: Count of threat words
                - action_keyword_count: Count of action request words
                - reward_keyword_count: Count of reward claim words
                - has_urgency: Binary (1 if any urgency keywords)
                - has_threat: Binary (1 if any threat keywords)
                - has_action_request: Binary (1 if any action keywords)
                - has_reward_claim: Binary (1 if any reward keywords)
                - personal_pronoun_ratio: Proportion of "you"/"your" words
                - impersonal_greeting: Binary (1 if generic greeting detected)
        """
        text_lower = text.lower()
        words = text.split()

        # Phishing-specific keyword lists (from research)
        urgency_keywords = ['urgent', 'immediately', 'act now', 'asap', 'expire',
                           'expires', 'suspended', 'verify', 'confirm', 'within']
        threat_keywords = ['suspended', 'terminated', 'locked', 'unauthorized',
                          'fraud', 'security', 'breach', 'compromised']
        action_keywords = ['click', 'login', 'update', 'verify', 'confirm',
                          'download', 'open', 'follow', 'respond']
        reward_keywords = ['won', 'winner', 'prize', 'free', 'claim', 'reward',
                          'congratulations', 'selected']

        # Count keyword occurrences
        urgency_count = sum(text_lower.count(kw) for kw in urgency_keywords)
        threat_count = sum(text_lower.count(kw) for kw in threat_keywords)
        action_count = sum(text_lower.count(kw) for kw in action_keywords)
        reward_count = sum(text_lower.count(kw) for kw in reward_keywords)

        # Personal pronoun ratio (direct addressing common in phishing)
        personal_pronoun_count = text_lower.count('you') + text_lower.count('your')
        personal_pronoun_ratio = personal_pronoun_count / len(words) if len(words) > 0 else 0.0

        # Impersonal greeting detection (generic phishing templates)
        impersonal_greetings = ['dear customer', 'dear user', 'dear member',
                               'dear sir', 'dear madam', 'valued customer']
        has_impersonal_greeting = any(greeting in text_lower for greeting in impersonal_greetings)

        return {
            'urgency_keyword_count': urgency_count,
            'threat_keyword_count': threat_count,
            'action_keyword_count': action_count,
            'reward_keyword_count': reward_count,
            'has_urgency': 1 if urgency_count > 0 else 0,
            'has_threat': 1 if threat_count > 0 else 0,
            'has_action_request': 1 if action_count > 0 else 0,
            'has_reward_claim': 1 if reward_count > 0 else 0,
            'personal_pronoun_ratio': personal_pronoun_ratio,
            'impersonal_greeting': 1 if has_impersonal_greeting else 0,
        }


def _get_default_text_features() -> Dict[str, float]:
    """Return default feature values for empty or invalid text.

    Used as fallback when text is empty, None, or whitespace-only.
    Returns all zeros/defaults to prevent crashes and ensure consistent
    feature dictionary structure.

    Returns:
        Dictionary with all ~50 features set to 0 or 0.0
    """
    return {
        # Lexical features (15)
        'text_length': 0,
        'word_count': 0,
        'avg_word_length': 0.0,
        'digit_count': 0,
        'digit_ratio': 0.0,
        'uppercase_count': 0,
        'uppercase_ratio': 0.0,
        'exclamation_count': 0,
        'question_count': 0,
        'dollar_count': 0,
        'url_count': 0,
        'email_count': 0,
        'phone_pattern_count': 0,
        'special_char_ratio': 0.0,
        'whitespace_ratio': 0.0,
        # Syntactic features (15)
        'sentence_count': 0,
        'avg_sentence_length': 0.0,
        'token_count': 0,
        'verb_count': 0,
        'verb_ratio': 0.0,
        'noun_count': 0,
        'noun_ratio': 0.0,
        'pronoun_count': 0,
        'pronoun_ratio': 0.0,
        'adjective_count': 0,
        'adjective_ratio': 0.0,
        'adverb_count': 0,
        'adverb_ratio': 0.0,
        'punct_count': 0,
        'imperative_verb_count': 0,
        # Stylometric features (10)
        'flesch_reading_ease': 0.0,
        'flesch_kincaid_grade': 0.0,
        'gunning_fog': 0.0,
        'smog_index': 0.0,
        'coleman_liau_index': 0.0,
        'automated_readability_index': 0.0,
        'syllable_count': 0,
        'lexicon_count': 0,
        'difficult_words': 0,
        'lexical_diversity': 0.0,
        # Sentiment features (10)
        'urgency_keyword_count': 0,
        'threat_keyword_count': 0,
        'action_keyword_count': 0,
        'reward_keyword_count': 0,
        'has_urgency': 0,
        'has_threat': 0,
        'has_action_request': 0,
        'has_reward_claim': 0,
        'personal_pronoun_ratio': 0.0,
        'impersonal_greeting': 0,
    }


def extract_text_features(text: str, extractor: TextFeatureExtractor = None) -> Dict[str, float]:
    """Module-level convenience function for text feature extraction.

    Extracts all NLP features from text. If no extractor is provided, creates
    a new one (note: this loads spaCy model each time, which is slower).
    For repeated extractions, create an extractor once and reuse it.

    Args:
        text: Input text to extract features from
        extractor: Optional pre-initialized TextFeatureExtractor instance

    Returns:
        Dictionary with ~50 numeric features

    Example:
        >>> # One-off extraction (slower)
        >>> features = extract_text_features("Test message")

        >>> # Repeated extraction (faster)
        >>> extractor = TextFeatureExtractor()
        >>> features1 = extract_text_features("Message 1", extractor)
        >>> features2 = extract_text_features("Message 2", extractor)
    """
    if extractor is None:
        extractor = TextFeatureExtractor()
    return extractor.extract_all_features(text)
