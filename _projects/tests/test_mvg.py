"""
Verifies the full 4-layer workflow: Contract -> Module -> Registry -> Orchestrator.
"""

from __future__ import annotations

import sys
import os
import unittest

# Ensure _projects/ (project root) is on sys.path so that
# relative imports like `from registry.service_registry import ServiceRegistry`
# work correctly when tests live inside `_projects/tests/`.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from registry.service_registry import ServiceRegistry
from contracts.greeting_protocol import GreetingServiceProtocol
from modules.polish_greeting import PolishGreetingService
from modules.english_greeting import EnglishGreetingService


class TestPolishGreeting(unittest.TestCase):
    """Tests for the Polish greeting module."""

    def setUp(self) -> None:
        self.service = PolishGreetingService()

    def test_morning_greeting(self) -> None:
        result = self.service.greet("Ania", {"hour": 8})
        self.assertEqual(result, "Dzień dobry, Ania!")

    def test_afternoon_greeting(self) -> None:
        result = self.service.greet("Tomek", {"hour": 14})
        self.assertEqual(result, "Dobry dzień, Tomek!")

    def test_evening_greeting(self) -> None:
        result = self.service.greet("Maja", {"hour": 20})
        self.assertEqual(result, "Dobry wieczór, Maja!")

    def test_night_greeting(self) -> None:
        result = self.service.greet("Kasia", {"hour": 3})
        self.assertEqual(result, "Dobranoc, Kasia!")

    def test_default_no_context(self) -> None:
        """Should not raise — falls back to system clock."""
        result = self.service.greet("World")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_get_service_info(self) -> None:
        info = self.service.get_service_info()
        self.assertEqual(info["service_name"], "PolishGreetingService")
        self.assertEqual(info["language"], "pl")
        self.assertIn("version", info)


class TestEnglishGreeting(unittest.TestCase):
    """Tests for the English greeting module."""

    def setUp(self) -> None:
        self.service = EnglishGreetingService()

    def test_morning_greeting(self) -> None:
        result = self.service.greet("Alice", {"hour": 8})
        self.assertEqual(result, "Good morning, Alice!")

    def test_afternoon_greeting(self) -> None:
        result = self.service.greet("Bob", {"hour": 14})
        self.assertEqual(result, "Good afternoon, Bob!")

    def test_evening_greeting(self) -> None:
        result = self.service.greet("Charlie", {"hour": 20})
        self.assertEqual(result, "Good evening, Charlie!")

    def test_night_greeting(self) -> None:
        result = self.service.greet("Diana", {"hour": 3})
        self.assertEqual(result, "Good night, Diana!")


class TestServiceRegistry(unittest.TestCase):
    """Tests for the ServiceRegistry."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_register_and_get_service(self) -> None:
        pl = PolishGreetingService()
        self.registry.register(
            key="greet.test",
            instance=pl,
            contract_type=GreetingServiceProtocol,
        )
        retrieved = self.registry.get_service("greet.test")
        self.assertIs(retrieved, pl)

    def test_duplicate_registration_raises(self) -> None:
        svc = PolishGreetingService()
        self.registry.register(key="dup", instance=svc)
        with self.assertRaises(ValueError):
            self.registry.register(key="dup", instance=svc)

    def test_get_unregistered_service_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.registry.get_service("nonexistent")

    def test_list_services(self) -> None:
        pl = PolishGreetingService()
        en = EnglishGreetingService()
        self.registry.register(key="pl", instance=pl, contract_type=GreetingServiceProtocol)
        self.registry.register(key="en", instance=en, contract_type=GreetingServiceProtocol)

        services = self.registry.list_services()
        self.assertEqual(len(services), 2)
        # Keys are prefixed with project_id (default:)
        self.assertIn("default:pl", services)
        self.assertIn("default:en", services)

    def test_has_service(self) -> None:
        self.assertFalse(self.registry.has_service("x"))
        self.registry.register(key="x", instance=PolishGreetingService())
        self.assertTrue(self.registry.has_service("x"))


class TestEndToEndWorkflow(unittest.TestCase):
    """Full end-to-end test proving the 4-layer workflow."""

    def test_full_workflow(self) -> None:
        registry = ServiceRegistry()

        # Register
        pl = PolishGreetingService()
        en = EnglishGreetingService()
        registry.register(
            key="greeting.pl", instance=pl, contract_type=GreetingServiceProtocol
        )
        registry.register(
            key="greeting.en", instance=en, contract_type=GreetingServiceProtocol
        )

        # Retrieve and use (Orchestrator pattern)
        pl_svc = registry.get_service("greeting.pl")
        en_svc = registry.get_service("greeting.en")

        pl_result = pl_svc.greet("Ania", {"hour": 10})
        en_result = en_svc.greet("World", {"hour": 22})

        # Godzina 10 -> rano (6-11): Dzień dobry / Good morning
        # Godzina 22 -> noc (0-5, 22-23): Good night / Dobranoc
        self.assertEqual(pl_result, "Dzień dobry, Ania!")
        self.assertEqual(en_result, "Good night, World!")


if __name__ == "__main__":
    unittest.main(verbosity=2)