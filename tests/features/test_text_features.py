"""Unit tests for NLP text feature extraction module.

Tests cover all feature extraction categories: lexical, syntactic, stylometric,
and sentiment features. Validates correct feature counts, edge case handling,
and phishing-specific detection logic.
"""

import pytest

from src.features.text_features import (
    TextFeatureExtractor,
    extract_text_features,
    _get_default_text_features,
)


# Test fixtures - Sample texts
@pytest.fixture
def phishing_text():
    """Typical phishing message with urgency and threats."""
    return "URGENT! Your account has been suspended. Click here to verify immediately."


@pytest.fixture
def legitimate_text():
    """Typical legitimate message."""
    return "Thank you for your order. Your package will arrive in 3-5 business days."


@pytest.fixture
def empty_text():
    """Empty string edge case."""
    return ""


@pytest.fixture
def short_text():
    """Very short text."""
    return "Hello"


@pytest.fixture
def extractor():
    """Reusable TextFeatureExtractor instance."""
    return TextFeatureExtractor()


# Test TextFeatureExtractor initialization
class TestExtractorInitialization:
    """Test TextFeatureExtractor class initialization."""

    def test_extractor_loads_spacy(self, extractor):
        """Test that spaCy model loads successfully."""
        assert extractor.nlp is not None
        assert hasattr(extractor.nlp, 'pipe_names')

    def test_extractor_reusable(self, extractor):
        """Test that same instance can extract multiple texts."""
        text1 = "First message"
        text2 = "Second message"

        features1 = extractor.extract_all_features(text1)
        features2 = extractor.extract_all_features(text2)

        assert features1 != features2
        assert len(features1) == len(features2)


# Test lexical features
class TestLexicalFeatures:
    """Test lexical feature extraction."""

    def test_lexical_text_length(self, extractor, phishing_text):
        """Test correct character count."""
        features = extractor.extract_lexical_features(phishing_text)
        assert features['text_length'] == len(phishing_text)

    def test_lexical_word_count(self, extractor, phishing_text):
        """Test correct word count."""
        features = extractor.extract_lexical_features(phishing_text)
        assert features['word_count'] == len(phishing_text.split())

    def test_lexical_digit_detection(self, extractor, legitimate_text):
        """Test digit count in text with numbers."""
        features = extractor.extract_lexical_features(legitimate_text)
        # "3-5" contains 2 digits
        assert features['digit_count'] == 2
        assert features['digit_ratio'] > 0

    def test_lexical_url_detection(self, extractor):
        """Test URL pattern detection."""
        text = "Visit https://example.com or http://phish.tk for details"
        features = extractor.extract_lexical_features(text)
        assert features['url_count'] == 2

    def test_lexical_email_detection(self, extractor):
        """Test email pattern detection."""
        text = "Contact us at support@example.com or admin@test.org"
        features = extractor.extract_lexical_features(text)
        assert features['email_count'] == 2

    def test_lexical_phone_detection(self, extractor):
        """Test phone pattern detection."""
        text = "Call 555-123-4567 or (555) 987-6543"
        features = extractor.extract_lexical_features(text)
        assert features['phone_pattern_count'] == 2

    def test_lexical_empty_text(self, extractor, empty_text):
        """Test that empty text returns defaults without crashing."""
        features = extractor.extract_all_features(empty_text)
        assert features['text_length'] == 0
        assert features['word_count'] == 0

    def test_lexical_uppercase_ratio(self, extractor):
        """Test uppercase character ratio."""
        text = "URGENT MESSAGE"
        features = extractor.extract_lexical_features(text)
        # "URGENTMESSAGE" = 13 uppercase, 1 space
        assert features['uppercase_ratio'] > 0.8

    def test_lexical_special_chars(self, extractor, phishing_text):
        """Test special character ratio."""
        features = extractor.extract_lexical_features(phishing_text)
        assert features['special_char_ratio'] > 0
        assert features['exclamation_count'] >= 1


# Test syntactic features
class TestSyntacticFeatures:
    """Test syntactic feature extraction using spaCy."""

    def test_syntactic_sentence_count(self, extractor, phishing_text):
        """Test correct sentence detection."""
        features = extractor.extract_syntactic_features(phishing_text)
        # "URGENT! ... suspended. ... immediately." = 2-3 sentences
        assert features['sentence_count'] >= 2

    def test_syntactic_pos_ratios(self, extractor, legitimate_text):
        """Test that POS ratios are float in range 0-1."""
        features = extractor.extract_syntactic_features(legitimate_text)

        assert 0 <= features['verb_ratio'] <= 1
        assert 0 <= features['noun_ratio'] <= 1
        assert 0 <= features['pronoun_ratio'] <= 1
        assert 0 <= features['adjective_ratio'] <= 1
        assert 0 <= features['adverb_ratio'] <= 1

    def test_syntactic_token_count(self, extractor, short_text):
        """Test token count matches expectations."""
        features = extractor.extract_syntactic_features(short_text)
        assert features['token_count'] > 0

    def test_syntactic_imperative_detection(self, extractor):
        """Test detection of imperative verbs (commands)."""
        # Imperative commands start with verbs
        command_text = "Click here. Verify now. Update your password."
        features = extractor.extract_syntactic_features(command_text)
        # Should detect multiple imperative verbs
        assert features['imperative_verb_count'] >= 2

    def test_syntactic_avg_sentence_length(self, extractor, legitimate_text):
        """Test average sentence length calculation."""
        features = extractor.extract_syntactic_features(legitimate_text)
        assert features['avg_sentence_length'] > 0


# Test stylometric features
class TestStylometricFeatures:
    """Test stylometric (writing style) feature extraction."""

    def test_stylometric_readability(self, extractor, legitimate_text):
        """Test that flesch_reading_ease returns numeric value."""
        features = extractor.extract_stylometric_features(legitimate_text)
        # Can be any value, including negative for complex text
        assert isinstance(features['flesch_reading_ease'], (int, float))

    def test_stylometric_complexity(self, extractor):
        """Test that complex text has higher complexity scores."""
        simple_text = "The cat sat on the mat."
        complex_text = "The multifaceted ramifications of contemporary socioeconomic paradigms necessitate comprehensive analytical frameworks."

        simple_features = extractor.extract_stylometric_features(simple_text)
        complex_features = extractor.extract_stylometric_features(complex_text)

        # Gunning Fog should be higher for complex text
        assert complex_features['gunning_fog'] > simple_features['gunning_fog']

    def test_stylometric_lexical_diversity(self, extractor):
        """Test lexical diversity calculation."""
        # High diversity: all unique words
        diverse_text = "apple banana cherry date elderberry"
        # Low diversity: repeated words
        repetitive_text = "test test test test test"

        diverse_features = extractor.extract_stylometric_features(diverse_text)
        repetitive_features = extractor.extract_stylometric_features(repetitive_text)

        assert diverse_features['lexical_diversity'] > repetitive_features['lexical_diversity']
        assert diverse_features['lexical_diversity'] == 1.0  # All unique
        assert repetitive_features['lexical_diversity'] == 0.2  # 1 unique / 5 total

    def test_stylometric_syllable_count(self, extractor, legitimate_text):
        """Test syllable counting."""
        features = extractor.extract_stylometric_features(legitimate_text)
        assert features['syllable_count'] > 0

    def test_stylometric_difficult_words(self, extractor):
        """Test difficult word detection."""
        easy_text = "The cat is big."
        hard_text = "Antidisestablishmentarianism requires comprehension."

        easy_features = extractor.extract_stylometric_features(easy_text)
        hard_features = extractor.extract_stylometric_features(hard_text)

        # Hard text should have more difficult words
        assert hard_features['difficult_words'] >= easy_features['difficult_words']


# Test sentiment features
class TestSentimentFeatures:
    """Test sentiment/urgency feature extraction for phishing detection."""

    def test_urgency_detection(self, extractor, phishing_text):
        """Test that phishing text has urgency indicators."""
        features = extractor.extract_sentiment_features(phishing_text)
        assert features['has_urgency'] == 1
        assert features['urgency_keyword_count'] > 0

    def test_threat_detection(self, extractor, phishing_text):
        """Test threat keyword detection."""
        features = extractor.extract_sentiment_features(phishing_text)
        # "suspended" is a threat keyword
        assert features['has_threat'] == 1
        assert features['threat_keyword_count'] > 0

    def test_action_detection(self, extractor, phishing_text):
        """Test action request detection."""
        features = extractor.extract_sentiment_features(phishing_text)
        # "Click" and "verify" are action keywords
        assert features['has_action_request'] == 1
        assert features['action_keyword_count'] >= 2

    def test_legitimate_no_urgency(self, extractor, legitimate_text):
        """Test that legitimate text has no urgency indicators."""
        features = extractor.extract_sentiment_features(legitimate_text)
        assert features['has_urgency'] == 0
        assert features['urgency_keyword_count'] == 0

    def test_reward_detection(self, extractor):
        """Test reward claim detection."""
        reward_text = "Congratulations! You won a prize! Claim your free reward now!"
        features = extractor.extract_sentiment_features(reward_text)
        assert features['has_reward_claim'] == 1
        assert features['reward_keyword_count'] >= 3

    def test_personal_pronoun_ratio(self, extractor):
        """Test personal pronoun counting."""
        text = "Your account needs your attention. You must verify your identity."
        features = extractor.extract_sentiment_features(text)
        # Should have high personal pronoun ratio ("your" appears 3 times, "you" once)
        assert features['personal_pronoun_ratio'] > 0.2

    def test_impersonal_greeting(self, extractor):
        """Test impersonal greeting detection."""
        generic_greeting = "Dear Customer, your account requires attention."
        personal_greeting = "Dear John Smith, thank you for your order."

        generic_features = extractor.extract_sentiment_features(generic_greeting)
        personal_features = extractor.extract_sentiment_features(personal_greeting)

        assert generic_features['impersonal_greeting'] == 1
        assert personal_features['impersonal_greeting'] == 0


# Test integration
class TestIntegration:
    """Test complete feature extraction pipeline."""

    def test_extract_all_features(self, extractor, phishing_text):
        """Test that extract_all_features returns correct feature count."""
        features = extractor.extract_all_features(phishing_text)
        assert len(features) == 50  # 15 lexical + 15 syntactic + 10 stylometric + 10 sentiment

    def test_feature_count_consistent(self, extractor):
        """Test that feature count is consistent across different texts."""
        texts = [
            "Short",
            "Medium length text here",
            "This is a longer text with multiple sentences. It has more content. And even more details.",
        ]

        feature_counts = [len(extractor.extract_all_features(text)) for text in texts]
        assert all(count == 50 for count in feature_counts)

    def test_all_features_numeric(self, extractor, phishing_text):
        """Test that all features are numeric (int or float)."""
        features = extractor.extract_all_features(phishing_text)
        for key, value in features.items():
            assert isinstance(value, (int, float)), f"Feature {key} is not numeric: {type(value)}"

    def test_empty_text_default_features(self, extractor, empty_text):
        """Test that empty text returns default feature dict."""
        features = extractor.extract_all_features(empty_text)
        default_features = _get_default_text_features()
        assert features == default_features

    def test_whitespace_only_text(self, extractor):
        """Test that whitespace-only text returns defaults."""
        whitespace_text = "   \n\t   "
        features = extractor.extract_all_features(whitespace_text)
        default_features = _get_default_text_features()
        assert features == default_features

    def test_module_level_function(self):
        """Test module-level extract_text_features() convenience function."""
        text = "Test message"
        features = extract_text_features(text)
        assert len(features) == 50

    def test_module_level_function_with_extractor(self, extractor):
        """Test module-level function with provided extractor."""
        text = "Test message"
        features = extract_text_features(text, extractor)
        assert len(features) == 50

    def test_phishing_vs_legitimate_discrimination(self, extractor, phishing_text, legitimate_text):
        """Test that features discriminate between phishing and legitimate text."""
        phishing_features = extractor.extract_all_features(phishing_text)
        legitimate_features = extractor.extract_all_features(legitimate_text)

        # Phishing text should have more urgency/threat indicators
        assert phishing_features['has_urgency'] > legitimate_features['has_urgency']
        assert phishing_features['has_threat'] > legitimate_features['has_threat']
        assert phishing_features['urgency_keyword_count'] > legitimate_features['urgency_keyword_count']
