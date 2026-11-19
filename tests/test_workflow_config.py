from pathlib import Path

WORKFLOW = Path(".github/workflows/daily_update.yml")


def test_daily_workflow_runs_at_hong_kong_8am():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "cron: '0 0 * * *'" in text
    assert "workflow_dispatch" in text


def test_daily_workflow_deploys_only_web():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "publish_dir: ./web" in text
    assert "keep_files: true" in text
    assert "publish_branch: gh-pages" in text
    assert "contents: write" in text
    assert "publish_dir: ./docs" not in text


def test_daily_workflow_uses_personal_config():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "cp data/config.personal.json data/config.json" in text


def test_docs_deploy_workflow_is_disabled():
    assert not Path(".github/workflows/deploy-docs.yml").exists()
    assert Path(".github/workflows/deploy-docs.yml.disabled").exists()
