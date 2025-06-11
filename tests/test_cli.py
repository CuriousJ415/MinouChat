"""
Tests for the MiaChat CLI.
"""

import os
import pytest
from click.testing import CliRunner
from miachat.cli import cli
from miachat.database.config import db_config

@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()

@pytest.fixture
def test_db():
    """Create a test database."""
    # Use an in-memory SQLite database for testing
    db_config.engine = db_config.create_engine("sqlite:///:memory:")
    yield db_config
    # Clean up
    db_config.engine.dispose()

def test_init_database(runner, test_db):
    """Test database initialization."""
    result = runner.invoke(cli, ["init-database"])
    assert result.exit_code == 0
    assert "Initializing database..." in result.output
    assert "Created database tables." in result.output
    assert "Initialized database with predefined personalities." in result.output

def test_create_migration(runner):
    """Test migration creation command."""
    result = runner.invoke(cli, ["create-migration"])
    assert result.exit_code == 0
    assert "Creating new migration..." in result.output

def test_upgrade_database(runner):
    """Test database upgrade command."""
    result = runner.invoke(cli, ["upgrade-database"])
    assert result.exit_code == 0
    assert "Upgrading database..." in result.output

def test_cli_help(runner):
    """Test CLI help command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "MiaChat command-line interface." in result.output
    assert "init-database" in result.output
    assert "create-migration" in result.output
    assert "upgrade-database" in result.output 