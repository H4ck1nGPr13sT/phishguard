"""Unit tests for URL feature extraction module.

Tests cover:
- Basic feature extraction functionality
- HTTPS and security features
- Edge cases (empty URLs, IP addresses, unicode)
- Character counting accuracy
- Binary indicator correctness
- Performance requirements (<50ms per URL)
"""

import time

import pytest

from src.features import (
    calculate_entropy,
    extract_binary_features,
    extract_char_features,
    extract_length_features,
    extract_structure_features,
    extract_url_features,
)


class TestExtractURLFeatures:
    """Tests for main extract_url_features() function."""

    def test_basic_http_url(self):
        """Test basic HTTP URL returns 30+ features."""
        url = 'http://example.com'
        features = extract_url_features(url)

        assert len(features) == 30, f"Expected 30 features, got {len(features)}"
        assert all(
            isinstance(v, (int, float)) for v in features.values()
        ), "All features must be numeric"

    def test_https_url(self):
        """Test HTTPS URL sets has_https=1."""
        url = 'https://example.com'
        features = extract_url_features(url)

        assert features['has_https'] == 1
        assert features['url_length'] == len(url)

    def test_url_with_ip_address(self):
        """Test URL with IP address sets has_ip=1."""
        url = 'http://192.168.1.1/admin'
        features = extract_url_features(url)

        assert features['has_ip'] == 1
        assert features['has_https'] == 0

    def test_url_with_port(self):
        """Test URL with port sets has_port=1."""
        url = 'http://example.com:8080/path'
        features = extract_url_features(url)

        assert features['has_port'] == 1

    def test_url_with_subdomain(self):
        """Test URL with subdomain sets has_subdomain=1."""
        url = 'https://www.example.com'
        features = extract_url_features(url)

        assert features['has_subdomain'] == 1
        assert features['subdomain_length'] > 0

    def test_url_with_query_params(self):
        """Test URL with query parameters sets has_query=1 and param_count>0."""
        url = 'https://example.com/search?q=test&page=1'
        features = extract_url_features(url)

        assert features['has_query'] == 1
        assert features['param_count'] == 2
        assert features['query_length'] > 0

    def test_url_with_fragment(self):
        """Test URL with fragment sets has_fragment=1."""
        url = 'https://example.com/page#section'
        features = extract_url_features(url)

        assert features['has_fragment'] == 1

    def test_url_with_suspicious_tld(self):
        """Test URL with suspicious TLD sets has_suspicious_tld=1."""
        suspicious_urls = [
            'http://phishing.tk',
            'http://scam.ml',
            'http://fake.ga',
            'http://malicious.cf',
            'http://bad.gq',
            'http://suspicious.xyz',
        ]

        for url in suspicious_urls:
            features = extract_url_features(url)
            assert (
                features['has_suspicious_tld'] == 1
            ), f"Failed for TLD in {url}"

    def test_all_features_numeric(self):
        """Test all features are numeric (int or float)."""
        url = 'https://sub.example.com/path?a=1&b=2#anchor'
        features = extract_url_features(url)

        for key, value in features.items():
            assert isinstance(
                value, (int, float)
            ), f"Feature {key} has non-numeric value: {value}"

    def test_feature_consistency(self):
        """Test feature dict has consistent keys across different URLs."""
        url1 = 'https://example.com'
        url2 = 'http://192.168.1.1:8080/path?q=1'
        url3 = 'https://sub.domain.co.uk/a/b/c'

        features1 = extract_url_features(url1)
        features2 = extract_url_features(url2)
        features3 = extract_url_features(url3)

        # All should have same keys
        assert features1.keys() == features2.keys()
        assert features2.keys() == features3.keys()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_url(self):
        """Test empty URL returns dict with all zeros/defaults."""
        url = ''
        features = extract_url_features(url)

        assert len(features) == 30
        assert features['url_length'] == 0
        assert features['is_valid'] == 0

    def test_very_long_url(self):
        """Test very long URL (2000+ chars) handles gracefully."""
        base = 'https://example.com/'
        long_path = 'a' * 2000
        url = base + long_path

        features = extract_url_features(url)

        assert features['url_length'] > 2000
        assert features['path_length'] > 2000
        assert isinstance(features['entropy'], float)

    def test_url_with_unicode(self):
        """Test URL with unicode characters (punycode domains)."""
        # Unicode domain (tldextract handles punycode)
        url = 'https://münchen.de/page'
        features = extract_url_features(url)

        assert len(features) == 30
        assert features['url_length'] > 0
        assert all(isinstance(v, (int, float)) for v in features.values())

    def test_url_with_at_symbol(self):
        """Test URL with @ symbol in path (common in phishing)."""
        url = 'http://evil.com/login@paypal.com'
        features = extract_url_features(url)

        assert features['at_count'] >= 1

    def test_url_with_multiple_subdomains(self):
        """Test URL with multiple subdomain levels."""
        url = 'https://sub1.sub2.sub3.example.com/path'
        features = extract_url_features(url)

        assert features['has_subdomain'] == 1
        assert features['subdomain_count'] >= 3


class TestIndividualFeatureFunctions:
    """Tests for individual feature extraction functions."""

    def test_calculate_entropy_empty_string(self):
        """Test entropy of empty string returns 0.0."""
        entropy = calculate_entropy('')
        assert entropy == 0.0

    def test_calculate_entropy_single_char(self):
        """Test entropy of repeated character is 0.0."""
        entropy = calculate_entropy('aaaa')
        assert entropy == 0.0

    def test_calculate_entropy_varied_chars(self):
        """Test entropy of varied characters is > 0."""
        entropy = calculate_entropy('abcd')
        assert entropy > 0

    def test_length_features_match_expected(self):
        """Test length features match manual calculation."""
        from urllib.parse import urlparse

        import tldextract

        url = 'https://www.example.com/path?query=value'
        parsed = urlparse(url)
        extracted = tldextract.extract(url)

        features = extract_length_features(url, parsed, extracted)

        assert features['url_length'] == len(url)
        assert features['domain_length'] == len('example')
        assert features['tld_length'] == len('com')
        assert features['subdomain_length'] == len('www')

    def test_char_counts_match_manual(self):
        """Test character counts match manual count."""
        url = 'https://example.com/a-b_c?x=1&y=2'

        features = extract_char_features(url)

        assert features['dot_count'] == url.count('.')
        assert features['hyphen_count'] == url.count('-')
        assert features['underscore_count'] == url.count('_')
        assert features['slash_count'] == url.count('/')
        assert features['question_count'] == url.count('?')
        assert features['equal_count'] == url.count('=')
        assert features['ampersand_count'] == url.count('&')

    def test_binary_features_correctness(self):
        """Test binary features return 0 or 1."""
        from urllib.parse import urlparse

        import tldextract

        url = 'https://sub.example.tk/path?q=1#anchor'
        parsed = urlparse(url)
        extracted = tldextract.extract(url)

        features = extract_binary_features(url, parsed, extracted)

        # All binary features must be 0 or 1
        for key, value in features.items():
            assert value in [0, 1], f"Binary feature {key} must be 0 or 1, got {value}"

        # Verify specific features
        assert features['has_https'] == 1
        assert features['has_subdomain'] == 1
        assert features['has_query'] == 1
        assert features['has_fragment'] == 1
        assert features['has_suspicious_tld'] == 1

    def test_structure_features_path_depth(self):
        """Test path_depth counts correctly."""
        from urllib.parse import urlparse

        import tldextract

        url = 'https://example.com/a/b/c'
        parsed = urlparse(url)
        extracted = tldextract.extract(url)

        features = extract_structure_features(url, parsed, extracted)

        assert features['path_depth'] == 3

    def test_structure_features_digit_ratio(self):
        """Test digit_ratio calculation."""
        from urllib.parse import urlparse

        import tldextract

        url = 'https://example123.com'
        parsed = urlparse(url)
        extracted = tldextract.extract(url)

        features = extract_structure_features(url, parsed, extracted)

        # Should have 3 digits in URL
        expected_ratio = 3 / len(url)
        assert abs(features['digit_ratio'] - expected_ratio) < 0.01


class TestPerformance:
    """Performance tests for feature extraction."""

    def test_single_url_performance(self):
        """Test extract_url_features completes in <50ms for single URL."""
        url = 'https://subdomain.example.com/path/to/resource?param1=value1&param2=value2#section'

        start_time = time.time()
        features = extract_url_features(url)
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 50, f"Extraction took {elapsed_ms:.2f}ms, expected <50ms"
        assert len(features) == 30

    def test_batch_performance(self):
        """Test feature extraction on batch of URLs."""
        urls = [
            'https://example.com',
            'http://192.168.1.1:8080/admin',
            'https://phishing.tk/login',
            'https://www.google.com/search?q=test',
            'http://subdomain.example.co.uk/path',
        ] * 10  # 50 URLs total

        start_time = time.time()
        for url in urls:
            extract_url_features(url)
        elapsed_ms = (time.time() - start_time) * 1000

        avg_ms = elapsed_ms / len(urls)
        assert avg_ms < 50, f"Average extraction took {avg_ms:.2f}ms, expected <50ms"


class TestRealWorldURLs:
    """Tests with real-world URL patterns."""

    def test_legitimate_url(self):
        """Test legitimate URL (e.g., Google)."""
        url = 'https://www.google.com/search?q=python'
        features = extract_url_features(url)

        assert features['has_https'] == 1
        assert features['has_subdomain'] == 1
        assert features['is_valid'] == 1
        assert features['has_suspicious_tld'] == 0

    def test_phishing_url_pattern(self):
        """Test common phishing URL pattern."""
        # Phishing URLs often have: long URLs, IP addresses, suspicious TLDs
        url = 'http://192.168.1.1/paypal-login@secure-verify.tk/account'
        features = extract_url_features(url)

        assert features['has_ip'] == 1
        assert features['has_https'] == 0
        assert features['at_count'] >= 1
        assert features['url_length'] > 50

    def test_url_with_deep_path(self):
        """Test URL with deep path structure."""
        url = 'https://example.com/a/b/c/d/e/f/g/h/i/j'
        features = extract_url_features(url)

        assert features['path_depth'] >= 10
        assert features['slash_count'] >= 10

    def test_url_with_many_params(self):
        """Test URL with many query parameters."""
        url = 'https://example.com/search?a=1&b=2&c=3&d=4&e=5'
        features = extract_url_features(url)

        assert features['param_count'] == 5
        assert features['ampersand_count'] == 4
        assert features['equal_count'] == 5
