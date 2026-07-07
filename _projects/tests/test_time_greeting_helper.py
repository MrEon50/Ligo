"""Tests for _utils/time_greeting_helper module.

Covers all greeting periods, edge cases, language support,
and error handling for get_greeting_period() and format_greeting().
"""

import sys
from pathlib import Path
import unittest

# Ensure _projects is on sys.path
_projects_root = Path(__file__).resolve().parent.parent
if str(_projects_root) not in sys.path:
    sys.path.insert(0, str(_projects_root))

from _utils.time_greeting_helper import (
    GreetingPeriod,
    get_greeting_period,
    format_greeting,
    GREETING_TEMPLATES,
)


class TestGreetingPeriodEnum(unittest.TestCase):
    """Tests for GreetingPeriod StrEnum."""

    def test_all_values_present(self) -> None:
        """All four greeting periods must exist."""
        self.assertEqual(len(GreetingPeriod), 4)
        self.assertIn(GreetingPeriod.NIGHT, GreetingPeriod)
        self.assertIn(GreetingPeriod.MORNING, GreetingPeriod)
        self.assertIn(GreetingPeriod.AFTERNOON, GreetingPeriod)
        self.assertIn(GreetingPeriod.EVENING, GreetingPeriod)

    def test_enum_values_are_strings(self) -> None:
        """GreetingPeriod values must be valid strings."""
        self.assertIsInstance(GreetingPeriod.NIGHT, str)
        self.assertIsInstance(GreetingPeriod.MORNING, str)
        self.assertIsInstance(GreetingPeriod.AFTERNOON, str)
        self.assertIsInstance(GreetingPeriod.EVENING, str)

    def test_enum_comparison(self) -> None:
        """GreetingPeriod values must compare equal to strings."""
        self.assertEqual(GreetingPeriod.NIGHT, "night")
        self.assertEqual(GreetingPeriod.MORNING, "morning")
        self.assertEqual(GreetingPeriod.AFTERNOON, "afternoon")
        self.assertEqual(GreetingPeriod.EVENING, "evening")


class TestGetGreetingPeriod(unittest.TestCase):
    """Tests for get_greeting_period() function."""

    # --- Night: 0-5, 22-23 ---
    def test_hour_0_is_night(self) -> None:
        self.assertEqual(get_greeting_period(0), GreetingPeriod.NIGHT)

    def test_hour_1_is_night(self) -> None:
        self.assertEqual(get_greeting_period(1), GreetingPeriod.NIGHT)

    def test_hour_5_is_night(self) -> None:
        self.assertEqual(get_greeting_period(5), GreetingPeriod.NIGHT)

    def test_hour_22_is_night(self) -> None:
        self.assertEqual(get_greeting_period(22), GreetingPeriod.NIGHT)

    def test_hour_23_is_night(self) -> None:
        self.assertEqual(get_greeting_period(23), GreetingPeriod.NIGHT)

    # --- Morning: 6-11 ---
    def test_hour_6_is_morning(self) -> None:
        self.assertEqual(get_greeting_period(6), GreetingPeriod.MORNING)

    def test_hour_11_is_morning(self) -> None:
        self.assertEqual(get_greeting_period(11), GreetingPeriod.MORNING)

    # --- Afternoon: 12-17 ---
    def test_hour_12_is_afternoon(self) -> None:
        self.assertEqual(get_greeting_period(12), GreetingPeriod.AFTERNOON)

    def test_hour_17_is_afternoon(self) -> None:
        self.assertEqual(get_greeting_period(17), GreetingPeriod.AFTERNOON)

    # --- Evening: 18-21 ---
    def test_hour_18_is_evening(self) -> None:
        self.assertEqual(get_greeting_period(18), GreetingPeriod.EVENING)

    def test_hour_21_is_evening(self) -> None:
        self.assertEqual(get_greeting_period(21), GreetingPeriod.EVENING)

    # --- Boundary transitions ---
    def test_boundary_5_to_6_night_to_morning(self) -> None:
        """Transition from night to morning at hour 6."""
        self.assertEqual(get_greeting_period(5), GreetingPeriod.NIGHT)
        self.assertEqual(get_greeting_period(6), GreetingPeriod.MORNING)

    def test_boundary_11_to_12_morning_to_afternoon(self) -> None:
        """Transition from morning to afternoon at hour 12."""
        self.assertEqual(get_greeting_period(11), GreetingPeriod.MORNING)
        self.assertEqual(get_greeting_period(12), GreetingPeriod.AFTERNOON)

    def test_boundary_17_to_18_afternoon_to_evening(self) -> None:
        """Transition from afternoon to evening at hour 18."""
        self.assertEqual(get_greeting_period(17), GreetingPeriod.AFTERNOON)
        self.assertEqual(get_greeting_period(18), GreetingPeriod.EVENING)

    def test_boundary_21_to_22_evening_to_night(self) -> None:
        """Transition from evening to night at hour 22."""
        self.assertEqual(get_greeting_period(21), GreetingPeriod.EVENING)
        self.assertEqual(get_greeting_period(22), GreetingPeriod.NIGHT)

    # --- Error handling ---
    def test_negative_hour_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_greeting_period(-1)

    def test_hour_24_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_greeting_period(24)

    def test_hour_100_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_greeting_period(100)

    def test_float_hour_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_greeting_period(12.5)

    def test_string_hour_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_greeting_period("12")

    def test_none_hour_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            get_greeting_period(None)


class TestFormatGreeting(unittest.TestCase):
    """Tests for format_greeting() function."""

    # --- Polish greetings ---
    def test_polish_night(self) -> None:
        result = format_greeting("pl", GreetingPeriod.NIGHT, "Ania")
        self.assertEqual(result, "Dobranoc, Ania!")

    def test_polish_morning(self) -> None:
        result = format_greeting("pl", GreetingPeriod.MORNING, "Tomek")
        self.assertEqual(result, "Dzień dobry, Tomek!")

    def test_polish_afternoon(self) -> None:
        result = format_greeting("pl", GreetingPeriod.AFTERNOON, "Maja")
        self.assertEqual(result, "Dobry dzień, Maja!")

    def test_polish_evening(self) -> None:
        result = format_greeting("pl", GreetingPeriod.EVENING, "Kasia")
        self.assertEqual(result, "Dobry wieczór, Kasia!")

    # --- English greetings ---
    def test_english_night(self) -> None:
        result = format_greeting("en", GreetingPeriod.NIGHT, "Alice")
        self.assertEqual(result, "Good night, Alice!")

    def test_english_morning(self) -> None:
        result = format_greeting("en", GreetingPeriod.MORNING, "Bob")
        self.assertEqual(result, "Good morning, Bob!")

    def test_english_afternoon(self) -> None:
        result = format_greeting("en", GreetingPeriod.AFTERNOON, "Charlie")
        self.assertEqual(result, "Good afternoon, Charlie!")

    def test_english_evening(self) -> None:
        result = format_greeting("en", GreetingPeriod.EVENING, "Diana")
        self.assertEqual(result, "Good evening, Diana!")

    # --- Unknown language fallback to English ---
    def test_unknown_language_falls_back_to_english(self) -> None:
        result = format_greeting("xx", GreetingPeriod.MORNING, "World")
        self.assertEqual(result, "Good morning, World!")

    def test_empty_language_falls_back_to_english(self) -> None:
        result = format_greeting("", GreetingPeriod.EVENING, "World")
        self.assertEqual(result, "Good evening, World!")

    # --- Name formatting ---
    def test_name_with_spaces(self) -> None:
        result = format_greeting("pl", GreetingPeriod.MORNING, "Jan Kowalski")
        self.assertEqual(result, "Dzień dobry, Jan Kowalski!")

    def test_name_with_numbers(self) -> None:
        result = format_greeting("en", GreetingPeriod.MORNING, "User123")
        self.assertEqual(result, "Good morning, User123!")

    def test_empty_name(self) -> None:
        result = format_greeting("pl", GreetingPeriod.MORNING, "")
        self.assertEqual(result, "Dzień dobry, !")

    def test_unicode_name(self) -> None:
        result = format_greeting("pl", GreetingPeriod.MORNING, "José García")
        self.assertEqual(result, "Dzień dobry, José García!")

    # --- Period as string (StrEnum compatibility) ---
    def test_period_as_string(self) -> None:
        result = format_greeting("pl", "morning", "Ania")
        self.assertEqual(result, "Dzień dobry, Ania!")


class TestGreetingTemplates(unittest.TestCase):
    """Tests for GREETING_TEMPLATES constant."""

    def test_pl_has_all_periods(self) -> None:
        pl_templates = GREETING_TEMPLATES["pl"]
        for period in GreetingPeriod:
            self.assertIn(period, pl_templates)

    def test_en_has_all_periods(self) -> None:
        en_templates = GREETING_TEMPLATES["en"]
        for period in GreetingPeriod:
            self.assertIn(period, en_templates)

    def test_templates_are_non_empty(self) -> None:
        for lang, templates in GREETING_TEMPLATES.items():
            for period, text in templates.items():
                self.assertTrue(len(text) > 0, f"Empty template: {lang}/{period}")

    def test_templates_dont_have_trailing_comma(self) -> None:
        """Ensure templates don't have trailing comma before the name placeholder."""
        for lang, templates in GREETING_TEMPLATES.items():
            for period, text in templates.items():
                self.assertFalse(
                    text.endswith(","),
                    f"Template '{text}' in {lang}/{period} has trailing comma",
                )


class TestIntegrationGreetingFlow(unittest.TestCase):
    """Integration tests: full greeting flow (hour -> period -> message)."""

    def test_full_flow_polish(self) -> None:
        """Complete greeting flow for Polish."""
        # Simulate hour 14 (afternoon)
        hour = 14
        period = get_greeting_period(hour)
        greeting = format_greeting("pl", period, "Ania")
        
        self.assertEqual(period, GreetingPeriod.AFTERNOON)
        self.assertEqual(greeting, "Dobry dzień, Ania!")

    def test_full_flow_english(self) -> None:
        """Complete greeting flow for English."""
        hour = 3
        period = get_greeting_period(hour)
        greeting = format_greeting("en", period, "Bob")
        
        self.assertEqual(period, GreetingPeriod.NIGHT)
        self.assertEqual(greeting, "Good night, Bob!")

    def test_full_flow_boundary_hours(self) -> None:
        """Test all boundary hours produce correct periods."""
        boundaries = [
            (5, GreetingPeriod.NIGHT),
            (6, GreetingPeriod.MORNING),
            (11, GreetingPeriod.MORNING),
            (12, GreetingPeriod.AFTERNOON),
            (17, GreetingPeriod.AFTERNOON),
            (18, GreetingPeriod.EVENING),
            (21, GreetingPeriod.EVENING),
            (22, GreetingPeriod.NIGHT),
        ]
        for hour, expected_period in boundaries:
            period = get_greeting_period(hour)
            self.assertEqual(
                period,
                expected_period,
                f"Hour {hour} should be {expected_period}, got {period}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)