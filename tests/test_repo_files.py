from pathlib import Path


def test_precommit_config_exists():
    assert Path(".pre-commit-config.yaml").exists(), "Missing .pre-commit-config.yaml"


def test_ci_workflow_exists():
    assert Path(
        ".github/workflows/ci.yaml"
    ).exists(), "Missing .github/workflows/ci.yaml"
