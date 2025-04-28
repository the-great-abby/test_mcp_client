"""
CLI for running database migrations.
"""
import asyncio
import typer
from rich import print
from app.db.migrations import (
    create_tables,
    drop_tables,
    recreate_tables,
    get_table_names,
    get_create_table_sql,
    get_drop_table_sql
)

app = typer.Typer()

@app.command()
def create():
    """Create all database tables."""
    print("[bold blue]Creating tables...[/bold blue]")
    asyncio.run(create_tables())
    print("[bold green]Tables created successfully![/bold green]")

@app.command()
def drop():
    """Drop all database tables."""
    if typer.confirm("Are you sure you want to drop all tables?"):
        print("[bold red]Dropping tables...[/bold red]")
        asyncio.run(drop_tables())
        print("[bold green]Tables dropped successfully![/bold green]")

@app.command()
def recreate():
    """Drop and recreate all tables."""
    if typer.confirm("Are you sure you want to recreate all tables? This will delete all data!"):
        print("[bold yellow]Recreating tables...[/bold yellow]")
        asyncio.run(recreate_tables())
        print("[bold green]Tables recreated successfully![/bold green]")

@app.command()
def list_tables():
    """List all tables in the database."""
    tables = asyncio.run(get_table_names())
    print("[bold blue]Current tables:[/bold blue]")
    for table in tables:
        print(f"  - {table}")

@app.command()
def show_create_sql():
    """Show SQL for creating tables."""
    sql = asyncio.run(get_create_table_sql())
    print("[bold blue]Create Table SQL:[/bold blue]")
    print(sql)

@app.command()
def show_drop_sql():
    """Show SQL for dropping tables."""
    sql = asyncio.run(get_drop_table_sql())
    print("[bold blue]Drop Table SQL:[/bold blue]")
    print(sql)

if __name__ == "__main__":
    app() 