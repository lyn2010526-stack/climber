"""CLI: branch - Command line interface."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group(name='branch')
def branch_cli():
    """Branch commands."""
    pass


@branch_cli.command(name='list')
@click.option('--page', default=1, help='Page number')
@click.option('--page-size', default=20, help='Items per page')
@click.option('--status', default=None, help='Filter by status')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']))
def list_branch(page: int, page_size: int, status: str | None, output_format: str):
    """List items."""
    items = [{'id': i, 'name': f'Item {i}', 'status': 'active'} for i in range(1, 11)]
    if output_format == 'json':
        console.print_json(data=items)
    else:
        table = Table(title='Branch List')
        table.add_column('ID', style='cyan')
        table.add_column('Name', style='green')
        table.add_column('Status', style='yellow')
        for item in items:
            table.add_row(str(item['id']), item['name'], item['status'])
        console.print(table)


@branch_cli.command(name='get')
@click.argument('id', type=int)
def get_branch(id: int):
    """Get item by ID."""
    item = {'id': id, 'name': f'Item {id}', 'status': 'active'}
    console.print_json(data=item)


@branch_cli.command(name='create')
@click.option('--name', required=True, help='Item name')
@click.option('--description', default='', help='Item description')
@click.option('--status', default='active', help='Item status')
def create_branch(name: str, description: str, status: str):
    """Create item."""
    item = {'id': 1, 'name': name, 'description': description, 'status': status}
    console.print(f'[green]Created {name}[/green]')
    console.print_json(data=item)


@branch_cli.command(name='update')
@click.argument('id', type=int)
@click.option('--name', default=None, help='New name')
@click.option('--description', default=None, help='New description')
@click.option('--status', default=None, help='New status')
def update_branch(id: int, name: str | None, description: str | None, status: str | None):
    """Update item."""
    item = {'id': id, 'name': name or f'Item {id}', 'status': status or 'active'}
    console.print(f'[green]Updated {id}[/green]')
    console.print_json(data=item)


@branch_cli.command(name='delete')
@click.argument('id', type=int)
@click.confirmation_option(prompt='Are you sure?')
def delete_branch(id: int):
    """Delete item."""
    console.print(f'[red]Deleted {id}[/red]')


@branch_cli.command(name='export')
@click.argument('output_file', type=click.Path())
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'csv']))
def export_branch(output_file: str, output_format: str):
    """Export items."""
    console.print(f'[green]Exported to {output_file}[/green]')


@branch_cli.command(name='import')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True, help='Preview changes')
def import_branch(input_file: str, dry_run: bool):
    """Import items."""
    console.print(f'[green]Imported from {input_file}[/green]')
