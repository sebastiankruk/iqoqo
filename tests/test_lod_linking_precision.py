# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
"""Precision regression fixture test suite for Linked Open Data (LOD) entity resolution.

Ensures strict precision gates for true positives (accepted >= 0.82), ambiguous matches
(suggested in [0.55, 0.82)), and false positives/disambiguation pages (rejected < 0.55 or 0.0).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.cache import cache
from app.core.lod_linking_service import (
    AGENT_CLASSES,
    CREATIVE_WORK_CLASSES,
    DBpediaClient,
    GeoNamesClient,
    compute_composite_score,
    is_disambiguation,
    normalize_title_for_comparison,
)

# ==============================================================================
# Fixtures & Test Data
# ==============================================================================

TRUE_POSITIVE_WORK_CASES = [
    {
        "target_title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "candidate_label": "Dune (novel)",
        "candidate_comment": "Dune is a 1965 science fiction novel by American author Frank Herbert.",
        "rank_margin": 0.8,
        "has_class_match": True,
        "expected_min_score": 0.82,
    },
    {
        "target_title": "Solaris",
        "author": "Stanisław Lem",
        "year": 1961,
        "candidate_label": "Solaris (novel)",
        "candidate_comment": "Solaris is a 1961 science fiction novel by Polish writer Stanisław Lem.",
        "rank_margin": 0.75,
        "has_class_match": True,
        "expected_min_score": 0.82,
    },
    {
        "target_title": "Neuromancer",
        "author": "William Gibson",
        "year": 1984,
        "candidate_label": "Neuromancer",
        "candidate_comment": "Neuromancer is a 1984 science fiction novel by William Gibson.",
        "rank_margin": 0.9,
        "has_class_match": True,
        "expected_min_score": 0.82,
    },
]

FALSE_POSITIVE_AND_DISAMBIGUATION_CASES = [
    # Disambiguation pages must score 0.0
    {
        "target_title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "candidate_label": "Dune (disambiguation)",
        "candidate_comment": "Dune may refer to:",
        "rank_margin": 0.8,
        "has_class_match": True,
        "expected_score": 0.0,
    },
    {
        "target_title": "Solaris",
        "author": "Stanisław Lem",
        "year": 1961,
        "candidate_label": "Solaris",
        "candidate_comment": "Solaris frequently refers to:",
        "rank_margin": 0.5,
        "has_class_match": True,
        "expected_score": 0.0,
    },
    # Incompatible ontology class (e.g. software, band, place instead of creative work)
    {
        "target_title": "Solaris",
        "author": "Stanisław Lem",
        "year": 1961,
        "candidate_label": "Solaris (operating system)",
        "candidate_comment": "Solaris is a proprietary Unix operating system originally developed by Sun Microsystems.",
        "rank_margin": 0.4,
        "has_class_match": False,
        "expected_score": 0.0,
    },
    {
        "target_title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "candidate_label": "Dune (band)",
        "candidate_comment": "Dune is a German electronic dance music band formed in 1995.",
        "rank_margin": 0.3,
        "has_class_match": False,
        "expected_score": 0.0,
    },
    # Substring / variant drift with wrong author and year
    {
        "target_title": "Dune",
        "author": "Frank Herbert",
        "year": 1965,
        "candidate_label": "Dune: Part Two",
        "candidate_comment": "Dune: Part Two is a 2024 American epic science fiction film directed by Denis Villeneuve.",
        "year_candidate": 2024,
        "rank_margin": 0.1,
        "has_class_match": True,
        "max_score": 0.55,
    },
]

SUGGESTION_TIER_CASES = [
    # Title matches exactly, class matches, but author is unknown/missing -> suggestion [0.55, 0.82)
    {
        "target_title": "The Road",
        "author": "Unconfirmed Author",
        "year": None,
        "candidate_label": "The Road",
        "candidate_comment": "The Road is a 2006 post-apocalyptic novel by Cormac McCarthy.",
        "rank_margin": 0.5,
        "has_class_match": True,
    },
    # Title matches well, but competitive second candidate narrows rank margin
    {
        "target_title": "Foundation",
        "author": "Isaac Asimov",
        "year": None,
        "candidate_label": "Foundation series",
        "candidate_comment": "The Foundation series is a science fiction book series written by Isaac Asimov.",
        "rank_margin": 0.05,
        "has_class_match": True,
    },
]


# ==============================================================================
# Precision Tests: Composite Scoring Gates
# ==============================================================================


@pytest.mark.parametrize("case", TRUE_POSITIVE_WORK_CASES)
def test_true_positive_composite_scoring_precision(case):
    """Ensure known true positives exceed the LOD auto-apply threshold (>= 0.82)."""
    score = compute_composite_score(
        candidate_label=case["candidate_label"],
        target_title=case["target_title"],
        author=case["author"],
        candidate_comment=case["candidate_comment"],
        year=case["year"],
        rank_margin=case["rank_margin"],
        has_class_match=case["has_class_match"],
    )
    assert (
        score >= case["expected_min_score"]
    ), f"Failed precision gate for '{case['target_title']}': got {score:.3f}, expected >= {case['expected_min_score']}"


@pytest.mark.parametrize("case", FALSE_POSITIVE_AND_DISAMBIGUATION_CASES)
def test_false_positive_rejection_precision(case):
    """Ensure disambiguation pages and out-of-domain entities are rejected (< 0.55 or 0.0)."""
    score = compute_composite_score(
        candidate_label=case["candidate_label"],
        target_title=case["target_title"],
        author=case["author"],
        candidate_comment=case["candidate_comment"],
        year=case.get("year"),
        rank_margin=case["rank_margin"],
        has_class_match=case["has_class_match"],
    )
    if "expected_score" in case:
        assert score == case["expected_score"], f"Expected {case['expected_score']}, got {score} for {case['candidate_label']}"
    if "max_score" in case:
        assert score < case["max_score"], f"Expected < {case['max_score']}, got {score} for {case['candidate_label']}"


@pytest.mark.parametrize("case", SUGGESTION_TIER_CASES)
def test_ambiguous_matches_fall_into_suggestion_tier(case):
    """Ensure ambiguous or uncorroborated candidates fall strictly into suggestion range [0.55, 0.82)."""
    score = compute_composite_score(
        candidate_label=case["candidate_label"],
        target_title=case["target_title"],
        author=case["author"],
        candidate_comment=case["candidate_comment"],
        year=case["year"],
        rank_margin=case["rank_margin"],
        has_class_match=case["has_class_match"],
    )
    assert 0.55 <= score < 0.82, f"Candidate '{case['candidate_label']}' should be suggested: score was {score:.3f}"


# ==============================================================================
# Precision Tests: Disambiguation and Title Normalization
# ==============================================================================


def test_disambiguation_detection():
    """Verify disambiguation markers in label, comment, and URI."""
    assert is_disambiguation("http://dbpedia.org/resource/Dune_(disambiguation)", "Dune", "")
    assert is_disambiguation("", "Dune (disambiguation)", "")
    assert is_disambiguation("", "Dune", "Dune may refer to several articles:")
    assert is_disambiguation("", "Solaris", "Solaris frequently refers to the following:")
    assert not is_disambiguation("http://dbpedia.org/resource/Dune_(novel)", "Dune (novel)", "Dune is a 1965 novel.")


def test_title_normalization_precision():
    """Verify punctuation, subtitle, and case normalization."""
    assert normalize_title_for_comparison("The Hobbit: Or There and Back Again") == "the hobbit or there and back again"
    assert normalize_title_for_comparison("A Tale of Two Cities") == "a tale of two cities"
    assert normalize_title_for_comparison("Solaris (novel)") == "solaris"


# ==============================================================================
# Precision Tests: DBpedia Client Class Filtering
# ==============================================================================


def test_dbpedia_client_rejects_non_creative_works(app):
    """DBpedia lookup rejects candidates that do not belong to CREATIVE_WORK_CLASSES."""
    with app.app_context():
        cache.delete("lod:dbpedia:work:foundation:dbo:Book::")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Return only a company and a place for query "Foundation"
        mock_resp.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/Foundation_Inc"],
                    "label": ["Foundation Inc"],
                    "score": [150.0],
                    "comment": ["Foundation Inc is an American software company."],
                    "typeName": ["dbo:Organisation", "dbo:Company"],
                },
                {
                    "resource": ["http://dbpedia.org/resource/Foundation_Island"],
                    "label": ["Foundation Island"],
                    "score": [120.0],
                    "comment": ["Foundation Island is an island in the Pacific."],
                    "typeName": ["dbo:Place", "dbo:Island"],
                },
            ]
        }

        with patch("requests.get", return_value=mock_resp):
            result = DBpediaClient.resolve_work("Foundation", media_category="book")
            assert result is None, "Should reject candidate with non-creative-work classes"


def test_dbpedia_client_agent_resolution_precision(app):
    """DBpedia author resolution only matches AGENT_CLASSES and rejects non-agents."""
    with app.app_context():
        cache.delete("lod:dbpedia:person:stanisław lem")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "docs": [
                {
                    "resource": ["http://dbpedia.org/resource/Stanis%C5%82aw_Lem_Street"],
                    "label": ["Stanisław Lem Street"],
                    "score": [130.0],
                    "comment": ["A street in Kraków named after Stanisław Lem."],
                    "typeName": ["dbo:RouteOfTransportation", "dbo:Place"],
                },
                {
                    "resource": ["http://dbpedia.org/resource/Stanis%C5%82aw_Lem"],
                    "label": ["Stanisław Lem"],
                    "score": [120.0],
                    "comment": ["Stanisław Herman Lem was a Polish writer of science fiction."],
                    "typeName": ["dbo:Person", "dbo:Writer"],
                },
            ]
        }

        with patch("requests.get", return_value=mock_resp):
            result = DBpediaClient.resolve_person("Stanisław Lem")
            assert result is not None
            assert result["uri"] == "http://dbpedia.org/resource/Stanis%C5%82aw_Lem"
            assert result["confidence"] >= 0.82


# ==============================================================================
# Precision Tests: GeoNames Location Precision
# ==============================================================================


def test_geonames_feature_class_p_filter(app):
    """GeoNames resolution requests featureClass='P' (populated places)."""
    with app.app_context():
        cache.delete("lod:geonames:randomnonexistentplace")
        with patch.object(GeoNamesClient, "_resolve_local", return_value=None), patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "geonames": [
                    {
                        "geonameId": 2643743,
                        "name": "RandomPlace",
                        "countryCode": "GB",
                        "lat": "51.50853",
                        "lng": "-0.12574",
                        "fcl": "P",
                        "fcode": "PPLC",
                    }
                ]
            }
            mock_get.return_value = mock_resp

            result = GeoNamesClient.resolve_location("randomnonexistentplace")
            assert result is not None
            assert result["label"] == "RandomPlace"

            # Check that requests.get was called with featureClass='P'
            call_kwargs = mock_get.call_args[1]
            assert "params" in call_kwargs
            assert call_kwargs["params"].get("featureClass") == "P"
