"""Tests for ServiceRegistry — the central "glue" of the LIGO system.

Covers registration, retrieval, validation, contract checking,
error handling, and the full service lifecycle.
"""

import sys
from pathlib import Path
import unittest

# Ensure _projects is on sys.path
_projects_root = Path(__file__).resolve().parent.parent
if str(_projects_root) not in sys.path:
    sys.path.insert(0, str(_projects_root))

from registry.service_registry import ServiceRegistry
from contracts.greeting_protocol import GreetingServiceProtocol
from modules.polish_greeting import PolishGreetingService
from modules.english_greeting import EnglishGreetingService


class TestServiceRegistryBasic(unittest.TestCase):
    """Basic ServiceRegistry operations."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_initial_state_empty(self) -> None:
        """Registry starts empty."""
        services = self.registry.list_services()
        self.assertEqual(len(services), 0)

    def test_has_service_false_for_missing(self) -> None:
        """has_service returns False for non-existent key."""
        self.assertFalse(self.registry.has_service("nonexistent"))

    def test_get_service_raises_key_error(self) -> None:
        """get_service raises KeyError for missing key."""
        with self.assertRaises(KeyError):
            self.registry.get_service("nonexistent")


class TestServiceRegistryRegister(unittest.TestCase):
    """ServiceRegistry registration tests."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_register_polish_service(self) -> None:
        """Register and retrieve Polish greeting service."""
        svc = PolishGreetingService()
        self.registry.register(
            key="greeting.pl",
            instance=svc,
            contract_type=GreetingServiceProtocol,
        )
        retrieved = self.registry.get_service("greeting.pl")
        self.assertIs(retrieved, svc)
        self.assertIsInstance(retrieved, PolishGreetingService)

    def test_register_english_service(self) -> None:
        """Register and retrieve English greeting service."""
        svc = EnglishGreetingService()
        self.registry.register(
            key="greeting.en",
            instance=svc,
            contract_type=GreetingServiceProtocol,
        )
        retrieved = self.registry.get_service("greeting.en")
        self.assertIs(retrieved, svc)
        self.assertIsInstance(retrieved, EnglishGreetingService)

    def test_register_without_contract(self) -> None:
        """Register without contract_type works."""
        svc = PolishGreetingService()
        self.registry.register(key="pl", instance=svc)
        retrieved = self.registry.get_service("pl")
        self.assertIs(retrieved, svc)

    def test_duplicate_registration_raises_value_error(self) -> None:
        """Registering same key twice raises ValueError."""
        svc = PolishGreetingService()
        self.registry.register(key="dup", instance=svc)
        with self.assertRaises(ValueError):
            self.registry.register(key="dup", instance=svc)

    def test_register_same_instance_twice_raises(self) -> None:
        """Registering same instance under different keys raises on second."""
        svc = PolishGreetingService()
        self.registry.register(key="key1", instance=svc)
        with self.assertRaises(ValueError):
            self.registry.register(key="key2", instance=svc)


class TestServiceRegistryListServices(unittest.TestCase):
    """ServiceRegistry list_services() tests."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_list_empty(self) -> None:
        """list_services returns empty dict when nothing registered."""
        services = self.registry.list_services()
        self.assertIsInstance(services, dict)
        self.assertEqual(len(services), 0)

    def test_list_after_registration(self) -> None:
        """list_services returns correct services after registration."""
        pl = PolishGreetingService()
        en = EnglishGreetingService()
        self.registry.register(
            key="pl", instance=pl, contract_type=GreetingServiceProtocol
        )
        self.registry.register(
            key="en", instance=en, contract_type=GreetingServiceProtocol
        )
        services = self.registry.list_services()
        self.assertEqual(len(services), 2)
        self.assertIn("default:pl", services)
        self.assertIn("default:en", services)
        self.assertIs(services["default:pl"], pl)
        self.assertIs(services["default:en"], en)

    def test_list_prefixed_with_project_id(self) -> None:
        """Keys are prefixed with project_id."""
        svc = PolishGreetingService()
        self.registry.register(key="test", instance=svc)
        services = self.registry.list_services()
        self.assertIn("default:test", services)


class TestServiceRegistryHasService(unittest.TestCase):
    """ServiceRegistry has_service() tests."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_has_service_after_register(self) -> None:
        """has_service returns True after registration."""
        svc = PolishGreetingService()
        self.registry.register(key="x", instance=svc)
        self.assertTrue(self.registry.has_service("x"))

    def test_has_service_false_after_delete(self) -> None:
        """has_service returns False after unregister."""
        svc = PolishGreetingService()
        self.registry.register(key="x", instance=svc)
        self.registry.unregister("x")
        self.assertFalse(self.registry.has_service("x"))


class TestServiceRegistryUnregister(unittest.TestCase):
    """ServiceRegistry unregister() tests."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_unregister_existing(self) -> None:
        """Unregister existing service works."""
        svc = PolishGreetingService()
        self.registry.register(key="x", instance=svc)
        self.registry.unregister("x")
        with self.assertRaises(KeyError):
            self.registry.get_service("x")

    def test_unregister_nonexistent_raises(self) -> None:
        """Unregister non-existent service raises KeyError."""
        with self.assertRaises(KeyError):
            self.registry.unregister("nonexistent")


class TestServiceRegistryContractValidation(unittest.TestCase):
    """Contract validation tests."""

    def test_contract_validation_passes(self) -> None:
        """Service that implements protocol passes validation."""
        registry = ServiceRegistry()
        svc = PolishGreetingService()
        # Should not raise
        registry.register(
            key="pl", instance=svc, contract_type=GreetingServiceProtocol
        )

    def test_contract_validation_fails(self) -> None:
        """Service that doesn't implement protocol raises TypeError."""
        registry = ServiceRegistry()

        class FakeService:
            """Service missing required methods."""
            pass

        fake = FakeService()
        with self.assertRaises(TypeError):
            registry.register(
                key="fake", instance=fake, contract_type=GreetingServiceProtocol
            )

    def test_contract_validation_partial_fails(self) -> None:
        """Service with partial implementation raises TypeError."""
        registry = ServiceRegistry()

        class PartialService:
            """Service with only one method."""
            def greet(self, name: str, context: dict | None = None) -> str:
                return f"Hello, {name}!"
            # Missing get_service_info()

        partial = PartialService()
        with self.assertRaises(TypeError):
            registry.register(
                key="partial", instance=partial, contract_type=GreetingServiceProtocol
            )


class TestServiceRegistryEdgeCases(unittest.TestCase):
    """Edge cases and error handling."""

    def setUp(self) -> None:
        self.registry = ServiceRegistry()

    def test_register_none_as_instance(self) -> None:
        """Registering None should raise TypeError."""
        with self.assertRaises(TypeError):
            self.registry.register(key="none", instance=None)

    def test_register_non_callable_without_contract(self) -> None:
        """Registering non-instance without contract works (no validation)."""
        # Without contract_type, any instance is accepted
        registry = ServiceRegistry()

        class SimpleService:
            pass

        svc = SimpleService()
        registry.register(key="simple", instance=svc)
        retrieved = registry.get_service("simple")
        self.assertIs(retrieved, svc)

    def test_multiple_registrations_different_keys(self) -> None:
        """Multiple different services can be registered."""
        for i in range(10):
            svc = PolishGreetingService()
            self.registry.register(key=f"svc_{i}", instance=svc)
        
        services = self.registry.list_services()
        self.assertEqual(len(services), 10)


class TestServiceRegistryIntegration(unittest.TestCase):
    """Integration tests: full workflow with registry."""

    def test_full_workflow_with_registry(self) -> None:
        """Complete workflow: register -> retrieve -> use."""
        registry = ServiceRegistry()

        # Register services
        pl = PolishGreetingService()
        en = EnglishGreetingService()
        registry.register(
            key="greeting.pl", instance=pl, contract_type=GreetingServiceProtocol
        )
        registry.register(
            key="greeting.en", instance=en, contract_type=GreetingServiceProtocol
        )

        # Retrieve and use
        pl_svc = registry.get_service("greeting.pl")
        en_svc = registry.get_service("greeting.en")

        pl_result = pl_svc.greet("Ania", {"hour": 10})
        en_result = en_svc.greet("World", {"hour": 22})

        # Verify results (godzina 10 = rano, godzina 22 = noc)
        self.assertEqual(pl_result, "Dzień dobry, Ania!")
        self.assertEqual(en_result, "Good night, World!")

    def test_workflow_with_list_and_filter(self) -> None:
        """List services and use them dynamically."""
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

        # List and use all greeting services
        services = registry.list_services()
        for key, svc in services.items():
            if hasattr(svc, "greet"):
                result = svc.greet("Tester", {"hour": 12})
                self.assertIsInstance(result, str)
                self.assertTrue(len(result) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)