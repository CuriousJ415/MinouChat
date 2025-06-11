"""
Command-line interface for MiaChat.
"""

import click
from sqlalchemy.orm import Session
from .database.config import db_config, get_db
from .database.init_data import init_db

@click.group()
def cli():
    """MiaChat command-line interface."""
    pass

@cli.command()
def init_database():
    """Initialize the database with required tables and data."""
    click.echo("Initializing database...")
    
    # Create tables
    db_config.create_tables()
    click.echo("Created database tables.")
    
    # Initialize data
    with next(get_db()) as db:
        init_db(db)
    click.echo("Initialized database with predefined personalities.")

@cli.command()
def create_migration():
    """Create a new database migration."""
    click.echo("Creating new migration...")
    # TODO: Implement migration creation using Alembic

@cli.command()
def upgrade_database():
    """Upgrade database to the latest version."""
    click.echo("Upgrading database...")
    # TODO: Implement database upgrade using Alembic

if __name__ == '__main__':
    cli() 