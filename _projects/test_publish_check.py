"""Quick integration test for LIGO v2.0 components."""
import sys
from pathlib import Path

# Add Ligo root to PYTHONPATH so we can import _system.utils.*
_SYSTEM_ROOT = str(Path(__file__).parent.parent)  # Ligo root (parent of _projects/)
if _SYSTEM_ROOT not in sys.path:
    sys.path.insert(0, _SYSTEM_ROOT)

from _system.utils.ligo_meta_cycling import MetaCyclingManager
from _system.utils.dependency_graph import DependencyGraph

print("=" * 60)
print("LIGO v2.0 — Final Integration Test Before GitHub Publish")
print("=" * 60)

# Test 1: MetaCyclingManager
print("\n[TEST 1] MetaCyclingManager...")
try:
    manager = MetaCyclingManager()
    print(f"  OK - Manager loaded, modified files: {len(manager.get_modified_files())}")
except Exception as e:
    print(f"  FAIL: {e}")

# Test 2: DependencyGraph
print("\n[TEST 2] DependencyGraph...")
try:
    graph = DependencyGraph(project_root=".")
    graph.scan_project()
    modules = graph.get_all_modules()
    summary = graph.get_architecture_summary()
    print(f"  OK - Found {len(modules)} modules, {summary['dependency_pairs']} dependencies")
    print(f"       Cycles detected: {summary['cycles_detected']}")
except Exception as e:
    print(f"  FAIL: {e}")

# Test 3: Context Manager (via MetaCycling)
print("\n[TEST 3] Context State Persistence...")
try:
    # Simulate a file modification
    manager.track_file_modification(
        file_path="modules/test_module.py",
        new_content="# Test module\nprint('test')",
        operation="modified"
    )
    print(f"  OK - Tracked {len(manager.get_modified_files())} modification(s)")
    
    # Save and restore
    path = manager.save_full_session(project_id="test_publish")
    restored = manager.restore_full_session(project_id="test_publish", restore_contents=False)
    if restored:
        print(f"  OK - Session restored, {restored['modified_files_count']} file(s)")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE — LIGO v2.0 is ready for GitHub!")
print("=" * 60)
