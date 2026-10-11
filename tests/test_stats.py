#!/usr/bin/env python3
"""
Unit Tests for GitHub Profile Stats Generation
"""

import os
import sys
import unittest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from generate_stats import (
    format_bytes,
    format_number,
    validate_svg,
    generate_overview_svg,
    generate_language_svg,
)


class TestStatsFormatting(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1048576), "1.0 MB")
        self.assertEqual(format_bytes(1073741824), "1.00 GB")
        self.assertEqual(format_bytes(5242880), "5.0 MB")

    def test_format_number(self):
        self.assertEqual(format_number(0), "0")
        self.assertEqual(format_number(42), "42")
        self.assertEqual(format_number(999), "999")
        self.assertEqual(format_number(1000), "1,000")
        self.assertEqual(format_number(1759), "1,759")
        self.assertEqual(format_number(125000), "125,000")


class TestSvgValidation(unittest.TestCase):
    def test_validate_svg_valid(self):
        valid = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect/></svg>'
        self.assertTrue(validate_svg(valid))

    def test_validate_svg_invalid(self):
        self.assertFalse(validate_svg("<div>Not an svg</div>"))
        self.assertFalse(validate_svg("<svg>Unclosed"))
        self.assertFalse(validate_svg("<svg xmlns='test'>Missing viewBox</svg>"))


class TestSvgGeneration(unittest.TestCase):
    def setUp(self):
        self.sample_stats = {
            "username": "kunalsanga",
            "fetched_at": "2026-10-12T00:00:00Z",
            "source": "GitHub REST & GraphQL API",
            "is_authenticated": True,
            "user": {
                "name": "Kunal Sanga",
                "login": "kunalsanga",
                "public_repos": 70,
                "followers": 11,
                "following": 1
            },
            "repos": {
                "total_public": 70,
                "total_forks_owned": 5,
                "total_sources_owned": 65,
                "total_stars": 12,
                "total_forks_count": 4,
                "total_open_issues": 3
            },
            "languages": {
                "breakdown": {
                    "Python": 2500000,
                    "JavaScript": 1200000,
                    "TypeScript": 800000,
                    "C++": 500000
                },
                "total_bytes": 5000000,
                "percentages": {
                    "Python": 50.0,
                    "JavaScript": 24.0,
                    "TypeScript": 16.0,
                    "C++": 10.0
                }
            },
            "contributions": {
                "total_year": 1759,
                "current_streak": 5,
                "longest_streak": 39,
                "total_commits": 1400,
                "total_prs": 15,
                "total_issues": 10,
                "total_reviews": 5,
                "has_graphql_data": True
            }
        }

    def test_generate_overview_svg(self):
        svg = generate_overview_svg(self.sample_stats)
        self.assertTrue(validate_svg(svg))
        self.assertIn("kunalsanga", svg)
        self.assertIn("★ 12", svg)
        self.assertIn("1,759", svg)
        self.assertIn("Current: 5d", svg)
        self.assertIn("Max: 39d", svg)

    def test_generate_language_svg(self):
        svg = generate_language_svg(self.sample_stats)
        self.assertTrue(validate_svg(svg))
        self.assertIn("Python", svg)
        self.assertIn("50.0%", svg)
        self.assertIn("JavaScript", svg)
        self.assertIn("24.0%", svg)
        self.assertIn("TypeScript", svg)
        self.assertIn("C++", svg)

    def test_generate_svg_without_graphql(self):
        stats_no_graphql = dict(self.sample_stats)
        stats_no_graphql["contributions"] = {
            "has_graphql_data": False,
            "total_year": 0
        }
        svg = generate_overview_svg(stats_no_graphql)
        self.assertTrue(validate_svg(svg))
        self.assertIn("kunalsanga", svg)
        self.assertIn("Repository Forks", svg)


if __name__ == "__main__":
    unittest.main()
