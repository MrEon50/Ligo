"""Tests for Self-Verification Engine and Stability Score."""

import os
import tempfile
from pathlib import Path

# Ensure _projects is on sys.path
sys_path_fix = Path(__file__).resolve().parent.parent.parent  # Ligo root
if str(sys_path_fix) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(sys_path_fix))


def test_stability_score_basic():
    """Stability score computes and returns grade."""
    from registry.stability_score import compute_stability_score
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    result = compute_stability_score(root)
    
    assert 0 <= result.overall <= 100, f"Overall score out of range: {result.overall}"
    assert result.grade in ("A", "B", "C", "D", "F")
    assert isinstance(result.to_dict(), dict)


def test_stability_score_grade_boundaries():
    """Grade mapping boundaries are correct."""
    from registry.stability_score import StabilityResult, ScoreDimension

    # Grade A: >= 90
    dim = lambda w: ScoreDimension("d", weight=w, max_score=100, details={"current": 95})
    r = StabilityResult(dim(0.25), dim(0.30), dim(0.25), dim(0.20), overall=95.0)
    assert r.grade == "A"

    # Grade B: >= 75
    r = StabilityResult(dim(0.25), dim(0.30), dim(0.25), dim(0.20), overall=80.0)
    assert r.grade == "B"

    # Grade C: >= 60
    r = StabilityResult(dim(0.25), dim(0.30), dim(0.25), dim(0.20), overall=65.0)
    assert r.grade == "C"

    # Grade D: >= 40
    r = StabilityResult(dim(0.25), dim(0.30), dim(0.25), dim(0.20), overall=50.0)
    assert r.grade == "D"

    # Grade F: < 40
    r = StabilityResult(dim(0.25), dim(0.30), dim(0.25), dim(0.20), overall=20.0)
    assert r.grade == "F"


def test_stability_markdown():
    """Stability result produces markdown report."""
    from registry.stability_score import compute_stability_score
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    result = compute_stability_score(root)
    md = result.to_markdown()
    
    assert "LIGO Stability Score" in md
    assert f"Grade {result.grade}" in md
    assert "|" in md  # Has markdown table format


def test_self_verify_structure_check():
    """SelfVerifier detects correct folder structure."""
    from registry.self_verify import SelfVerifier
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    verifier = SelfVerifier(root)
    
    result = verifier.check_structure()
    assert result.passed is True, f"Structure check failed: {result.message}"


def test_self_verify_config_check():
    """SelfVerifier detects _config.py presence."""
    from registry.self_verify import SelfVerifier
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    verifier = SelfVerifier(root)
    
    result = verifier.check_config_exists()
    assert result.passed is True, f"Config check failed: {result.message}"


def test_self_verify_run_full_check():
    """Full verification run produces valid report."""
    from registry.self_verify import SelfVerifier
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    verifier = SelfVerifier(root)
    
    report = verifier.run_full_check()
    
    assert "stability_score" in report
    assert "grade" in report
    assert "checks_total" in report
    assert "checks_passed" in report
    assert report["stability_score"] >= 0


def test_self_verify_module_stateless():
    """SelfVerifier checks modules are stateless."""
    from registry.self_verify import SelfVerifier
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    verifier = SelfVerifier(root)
    
    results = verifier.check_modules_stateless()
    for r in results:
        assert isinstance(r.passed, bool), f"Expected bool, got {type(r.passed)}"


def test_self_verify_contracts_valid():
    """SelfVerifier checks contracts have abstract methods."""
    from registry.self_verify import SelfVerifier
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    verifier = SelfVerifier(root)
    
    results = verifier.check_contracts_valid()
    for r in results:
        assert isinstance(r.passed, bool), f"Expected bool, got {type(r.passed)}"


def test_self_verify_invalid_root():
    """SelfVerifier raises error on non-existent root."""
    from registry.self_verify import SelfVerifier
    
    try:
        verifier = SelfVerifier(Path("/nonexistent/path"))
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass  # Expected


def test_import_checker_basic():
    """ImportChecker finds no issues in clean project."""
    from registry.import_checker import ImportChecker
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    checker = ImportChecker(root)
    
    report = checker.check_all()
    
    assert "issues" in report
    assert "orphans" in report
    assert isinstance(report["total_issues"], int)


def test_import_checker_stdlib_filter():
    """ImportChecker doesn't flag stdlib imports."""
    from registry.import_checker import ImportChecker, ImportIssue
    
    checker = ImportChecker(Path(__file__).resolve().parent.parent.parent)
    
    # Manually check that stdlib modules are filtered
    assert checker._is_stdlib("os") is True
    assert checker._is_stdlib("__future__") is True
    assert checker._is_stdlib("pathlib") is True
    assert checker._is_stdlib("_system") is False  # Project namespace


def test_module_generator_creates_files():
    """ModuleGenerator creates contract and module files."""
    from registry.module_generator import ModuleGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        gen = ModuleGenerator(root)
        
        result = gen.generate("test_gen", "TestGenService")
        
        assert result.name == "test_gen"
        assert result.service_class == "TestGenService"
        assert len(result.files_created) >= 2
        
        # Check contract file exists and has ABC
        contract_path = Path(result.contract_path)
        assert contract_path.exists()
        content = contract_path.read_text(encoding="utf-8")
        assert "abc.ABC" in content or "ABC)" in content
        assert "TestGenServiceProtocol" in content


def test_module_generator_stateless():
    """Generated module is stateless (no instance attribute assignment)."""
    from registry.module_generator import ModuleGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        gen = ModuleGenerator(root)
        
        result = gen.generate("stateless_test", "StatelessTestService")
        
        module_path = Path(result.module_path)
        content = module_path.read_text(encoding="utf-8")
        
        # Check no self._xxx assignment patterns in the generated code
        assert "self.__dict__" not in content
        assert "self._cache" not in content
        assert "self._session" not in content


def test_module_generator_default_methods():
    """ModuleGenerator uses default get_info method when none specified."""
    from registry.module_generator import ModuleGenerator
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        gen = ModuleGenerator(root)
        
        result = gen.generate("default_test")
        
        module_path = Path(result.module_path)
        content = module_path.read_text(encoding="utf-8")
        assert "get_info" in content


def test_project_analyzer():
    """ProjectAnalyzer returns valid metrics."""
    from registry.project_analyzer import ProjectAnalyzer
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    analyzer = ProjectAnalyzer(root)
    
    report = analyzer.analyze()
    
    assert "total_python_files" in report
    assert "contracts" in report
    assert "modules" in report
    assert "tests" in report
    assert isinstance(report["total_python_files"], int)
    assert report["total_python_files"] > 0


def test_project_analyzer_markdown():
    """ProjectAnalyzer produces markdown report."""
    from registry.project_analyzer import ProjectAnalyzer
    
    root = Path(__file__).resolve().parent.parent.parent  # Ligo root
    analyzer = ProjectAnalyzer(root)
    
    md = analyzer.report_markdown()
    
    assert "LIGO Project Analysis" in md
    assert "|" in md
