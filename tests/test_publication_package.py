from pathlib import Path

from scripts.package_release import find_project_root, should_include


def test_package_keeps_example_env() -> None:
    assert should_include(Path(".env.example"))


def test_package_excludes_real_env_files() -> None:
    assert not should_include(Path(".env"))
    assert not should_include(Path(".env.local"))
    assert not should_include(Path(".env.production"))


def test_package_excludes_generated_and_private_files() -> None:
    assert not should_include(Path("ants-ai-gateway.tar.gz"))
    assert not should_include(Path("config") / "models.backup.yaml")
    assert not should_include(Path("executor_credentials.json"))
    assert not should_include(Path(".pytest_cache") / "README.md")
    assert not should_include(Path("app") / "__pycache__" / "main.pyc")


def test_package_includes_project_sources() -> None:
    assert should_include(Path("app") / "main.py")
    assert should_include(Path("AGENTS.md"))
    assert should_include(Path("docs") / "publication-checklist.md")
    assert should_include(Path(".github") / "workflows" / "tests.yml")
    assert should_include(Path("Dockerfile"))


def test_find_project_root_from_project_root() -> None:
    root = Path(__file__).resolve().parents[1]
    assert find_project_root(root) == root


def test_find_project_root_from_parent() -> None:
    root = Path(__file__).resolve().parents[1]
    assert find_project_root(root.parent) == root
