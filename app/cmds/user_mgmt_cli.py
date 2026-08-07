"""CLI command: user_mgmt - User management commands."""

from __future__ import annotations

import asyncio

import click
import structlog

from app.storage.database import get_session

logger = structlog.get_logger()


@click.group(name="user_mgmt")
def user_mgmt_group():
    """Manage user_mgmt."""


@user_mgmt_group.command(name="list")
@click.option("--status", default=None, help="Filter by status")
@click.option("--page", default=1, type=int, help="Page number")
@click.option("--page-size", default=20, type=int, help="Items per page")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def list_user_mgmt(status: str | None, page: int, page_size: int, json_output: bool):
    """List user_mgmt items."""
    async def _list():
        async with get_session():
            click.echo(f"Listing user_mgmt items (page {page})...")

    asyncio.run(_list())


@user_mgmt_group.command(name="create")
@click.option("--name", required=True, help="Name")
@click.option("--description", default="", help="Description")
@click.option("--tags", default="", help="Comma-separated tags")
def create_user_mgmt(name: str, description: str, tags: str):
    """Create a new user_mgmt item."""
    async def _create():
        async with get_session():
            click.echo(f"Creating user_mgmt: {name}")

    asyncio.run(_create())


@user_mgmt_group.command(name="get")
@click.argument("item_id", type=int)
@click.option("--json-output", is_flag=True, help="Output as JSON")
def get_user_mgmt(item_id: int, json_output: bool):
    """Get user_mgmt by ID."""
    async def _get():
        async with get_session():
            click.echo(f"Fetching user_mgmt {item_id}...")

    asyncio.run(_get())


@user_mgmt_group.command(name="update")
@click.argument("item_id", type=int)
@click.option("--name", default=None, help="New name")
@click.option("--description", default=None, help="New description")
@click.option("--status", default=None, help="New status")
def update_user_mgmt(item_id: int, name: str | None, description: str | None, status: str | None):
    """Update user_mgmt item."""
    async def _update():
        async with get_session():
            click.echo(f"Updating user_mgmt {item_id}...")

    asyncio.run(_update())


@user_mgmt_group.command(name="delete")
@click.argument("item_id", type=int)
@click.option("--hard", is_flag=True, help="Hard delete")
@click.confirmation_option(prompt="Are you sure?")
def delete_user_mgmt(item_id: int, hard: bool):
    """Delete user_mgmt item."""
    async def _delete():
        async with get_session():
            click.echo(f"Deleting user_mgmt {item_id}...")

    asyncio.run(_delete())


@user_mgmt_group.command(name="export")
@click.argument("item_id", type=int)
@click.option("--output", default="-", help="Output file path")
def export_user_mgmt(item_id: int, output: str):
    """Export user_mgmt data."""
    async def _export():
        async with get_session():
            click.echo(f"Exporting user_mgmt {item_id}...")

    asyncio.run(_export())


@user_mgmt_group.command(name="import")
@click.argument("file_path")
@click.option("--dry-run", is_flag=True, help="Preview without importing")
def import_user_mgmt(file_path: str, dry_run: bool):
    """Import user_mgmt data."""
    async def _import():
        click.echo(f"Importing from {file_path}...")

    asyncio.run(_import())


@user_mgmt_group.command(name="stats")
def stats_user_mgmt():
    """Show user_mgmt statistics."""
    async def _stats():
        async with get_session():
            click.echo("user_mgmt statistics")

    asyncio.run(_stats())


@user_mgmt_group.command(name="cleanup")
@click.option("--days", default=30, type=int, help="Remove items older than N days")
@click.confirmation_option(prompt="Proceed with cleanup?")
def cleanup_user_mgmt(days: int):
    """Clean up old user_mgmt items."""
    async def _cleanup():
        click.echo(f"Cleaning up user_mgmt items older than {days} days...")

    asyncio.run(_cleanup())
