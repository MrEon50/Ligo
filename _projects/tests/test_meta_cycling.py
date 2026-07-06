"""Tests for Meta-Cycling features (Context Manager + Dependency Graph).

Verifies that LIGO can safely manage its own evolution between AI sessions.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))  # Ligo root — for _system.utils.* imports

from _system.utils.context_manager import ContextManager
from _system.utils.dependency_graph import DependencyGraph
from _system.utils.session_manager import SessionManager


class TestContextManager(unittest.TestCase):
    """Tests for Context Manager — tracks file modifications between AI sessions."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.context_dir = os.path.join(self.tmp_dir, "contexts")
        self.manager = ContextManager(context_dir=self.context_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_track_modification(self) -> None:
        """Verify that track_modification records file changes."""
        result = self.manager.track_modification(
            file_path="test_file.py",
            new_content="# Test content\nprint('hello')",
            operation="modified",
        )

        self.assertEqual(result["file_path"], "test_file.py")
        self.assertEqual(result["operation"], "modified")
        self.assertIn("timestamp", result)
        self.assertTrue(result.get("content_hash"))  # Hash should be present

    def test_save_and_load_context(self) -> None:
        """Verify that context snapshots can be saved and loaded."""
        self.manager.track_modification(
            file_path="modules/test.py",
            new_content="# Test module\nx = 1",
        )

        path = self.manager.save_context_snapshot(project_id="test")
        self.assertTrue(os.path.exists(path))

        loaded = self.manager.load_context(project_id="test")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["project_id"], "test")
        self.assertEqual(loaded["modified_files_count"], 1)

    def test_get_context_summary(self) -> None:
        """Verify context summary generation."""
        self.manager.track_modification("file1.py", new_content="content1")
        self.manager.save_context_snapshot(project_id="default")

        summary = self.manager.get_context_summary()
        self.assertEqual(summary["status"], "loaded")
        self.assertEqual(summary["total_modifications"], 1)

    def test_clear_modifications(self) -> None:
        """Verify that clear_modifications empties the tracking list."""
        self.manager.track_modification("file.py", new_content="content")
        self.assertTrue(self.manager.has_modifications())

        self.manager.clear_modifications()
        self.assertFalse(self.manager.has_modifications())


class TestDependencyGraph(unittest.TestCase):
    """Tests for Dependency Graph — scans imports and builds dependency analysis."""

    def setUp(self) -> None:
        # Utwórz testowy projekt z kilkoma modułami i importami
        self.tmp_dir = tempfile.mkdtemp()
        
        # modules/dependency_a.py
        os.makedirs(os.path.join(self.tmp_dir, "modules"))
        with open(os.path.join(self.tmp_dir, "modules", "dependency_a.py"), "w") as f:
            f.write("""
from modules.dependency_b import DependencyB

class DependencyA(DependencyB):
    def method_a(self):
        pass
""")

        # modules/dependency_b.py — base class imported by A
        with open(os.path.join(self.tmp_dir, "modules", "dependency_b.py"), "w") as f:
            f.write("""
class DependencyB:
    def method_b(self):
        pass
""")

        self.graph = DependencyGraph(project_root=self.tmp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_scan_project(self) -> None:
        """Verify that scan_project populates modules dict."""
        self.graph.scan_project()
        self.assertTrue(len(self.graph.get_all_modules()) > 0)

    def test_dependency_detection(self) -> None:
        """Verify that dependencies are correctly identified."""
        self.graph.scan_project()
        
        # dependency_a.py imports from dependency_b.py, so dependency_a depends on b
        deps = self.graph.get_dependents("modules/dependency_b.py")
        self.assertIn("modules/dependency_a.py", deps)

    def test_check_safety_safe(self) -> None:
        """Verify safety check passes for non-dependant file."""
        # Tworzymy nowy plik bez zależności
        with open(os.path.join(self.tmp_dir, "modules", "standalone.py"), "w") as f:
            f.write("class Standalone:\n    pass\n")
        
        self.graph.scan_project()
        result = self.graph.check_safety("modules/standalone.py")
        self.assertTrue(result.safe)

    def test_detect_cycles(self) -> None:
        """Verify cycle detection works for circular imports."""
        # Add cyclic import: c -> d -> c
        with open(os.path.join(self.tmp_dir, "modules", "cycle_c.py"), "w") as f:
            f.write("from modules.cycle_d import CycleD\nclass CycleC(CycleD):\n    pass\n")
        
        with open(os.path.join(self.tmp_dir, "modules", "cycle_d.py"), "w") as f:
            f.write("from modules.cycle_c import CycleC\nclass CycleD:\n    pass\n")

        self.graph.scan_project()
        cycles = self.graph.detect_cycles()
        
        # Should find at least one cycle between c and d
        has_cycle = any(
            "modules/cycle_c.py" in cyc and "modules/cycle_d.py" in cyc
            for cyc in cycles
        )
        self.assertTrue(has_cycle, f"Cycles detected: {cycles}")


class TestSessionManager(unittest.TestCase):
    """Tests for Session Manager — verifies auto-save functionality."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.session_dir = os.path.join(self.tmp_dir, "sessions")
        self.manager = SessionManager(session_dir=self.session_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_auto_save_on_modification(self) -> None:
        """Verify that auto_save writes both state and modification log."""
        services = {"test_service": {"class_name": "TestService"}}
        contracts = {"test_service": "ITest"}
        
        mod_log = [{"op": "modified", "file": "x.py"}, {"op": "created", "file": "y.py"}]

        result_path, count = self.manager.auto_save_on_modification(
            project_id="default",
            services=services,
            contracts=contracts,
            modification_log=mod_log,
        )

        self.assertEqual(count, 2)
        # Should have written mod log file
        mod_log_file = os.path.join(self.session_dir, "default_modifications.json")
        self.assertTrue(os.path.exists(mod_log_file))


class TestMetaCyclingIntegration(unittest.TestCase):
    """Integration tests for full Meta-Cycling workflow."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        
        # Utwórz prosty projekt testowy
        os.makedirs(os.path.join(self.tmp_dir, "modules"))
        
        with open(os.path.join(self.tmp_dir, "modules", "base_module.py"), "w") as f:
            f.write("class BaseModule:\n    def base_method(self):\n        pass\n")

        with open(os.path.join(self.tmp_dir, "modules", "derived_module.py"), "w") as f:
            f.write(
                "from modules.base_module import BaseModule\n"
                "class DerivedModule(BaseModule):\n"
                "    def derived_method(self):\n"
                "        pass\n"
            )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_full_meta_cycling_workflow(self) -> None:
        """Verify the full workflow: track -> check safety -> save."""
        from _system.utils.ligo_meta_cycling import MetaCyclingManager

        manager = MetaCyclingManager(
            project_root=self.tmp_dir,
            context_dir=os.path.join(self.tmp_dir, "contexts"),
            session_dir=os.path.join(self.tmp_dir, "sessions"),
        )

        # 1. Track file modification (simulating AI editing code)
        new_content = """from modules.base_module import BaseModule

class DerivedModule(BaseModule):
    def derived_method(self):
        pass
    
    def new_method(self):  # NEW METHOD ADDED BY AI!
        return 'new functionality'
"""

        manager.track_file_modification(
            file_path="modules/derived_module.py",
            new_content=new_content,
            operation="modified",
        )

        # 2. Check safety before saving (should be safe — only added a method)
        result = manager.check_safety_before_save()

        # Since we only ADDED a method (no breaking changes), it should be safe
        self.assertTrue(result["safe"], f"Expected safe but got violations: {result['violations']}")

        # 3. Save full session (context + modifications)
        context_path, _ = manager.save_full_session()
        self.assertTrue(os.path.exists(context_path))

        # 4. Verify summary is accurate
        summary = manager.get_session_summary()
        self.assertEqual(summary["modified_files"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
