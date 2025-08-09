"""Cast CLI - Command-line interface for Cast sync service."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cast import __version__
from cast.config import GlobalConfig, VaultConfig
from cast.ids import add_cast_ids
from cast.index import build_index
from cast.plan import create_plan
from cast.sync import SyncEngine
from cast.resolve import ConflictResolver
from cast.util import setup_logging

app = typer.Typer(
    name="cast",
    help="Knowledge-aware sync for Markdown vaults",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()


@app.callback()
def callback(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error output"),
) -> None:
    """Cast - Knowledge-aware sync for Markdown vaults."""
    setup_logging(verbose=verbose, quiet=quiet)


@app.command()
def version() -> None:
    """Show Cast version."""
    console.print(f"Cast version {__version__}")


@app.command()
def install() -> None:
    """Create global configuration and register vaults."""
    config = GlobalConfig.create_default()
    config.save()
    console.print("[green]✓[/green] Global configuration created")
    console.print(f"  Location: {config.config_path}")


@app.command()
def config() -> None:
    """Open global configuration in default text editor."""
    import os
    import subprocess
    
    config = GlobalConfig.load_or_create()
    config_path = config.config_path
    
    # Ensure config file exists
    if not config_path.exists():
        config.save()
    
    # Use EDITOR env var, fallback to common defaults
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    
    try:
        subprocess.run([editor, str(config_path)])
    except Exception as e:
        console.print(f"[red]Failed to open config with {editor}: {e}[/red]")
        console.print(f"Config location: {config_path}")


@app.command()
def vaults() -> None:
    """List all configured vaults."""
    config = GlobalConfig.load()
    
    if not config.vaults:
        console.print("[yellow]No vaults configured.[/yellow]")
        console.print("Use 'cast init' in a vault directory to register it.")
        return
    
    table = Table(title="Configured Vaults")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Path", style="dim")
    table.add_column("Status", style="green")
    
    for vault_id, vault_path in config.vaults.items():
        path = Path(vault_path)
        if path.exists():
            if (path / ".cast").exists():
                status = "✓ Initialized"
            else:
                status = "⚠ Not initialized"
        else:
            status = "✗ Missing"
        
        table.add_row(vault_id, str(vault_path), status)
    
    console.print(table)


@app.command()
def init(
    path: Path = typer.Argument(Path.cwd(), help="Vault root directory"),
    vault_id: Optional[str] = typer.Option(None, "--id", help="Vault ID for global config"),
) -> None:
    """Initialize Cast in a vault directory."""
    # Use provided ID or derive from directory name
    final_vault_id = vault_id or path.name
    
    vault_config = VaultConfig.create_default(path, final_vault_id)
    vault_config.save()
    
    # Create .cast directory structure
    cast_dir = path / ".cast"
    (cast_dir / "objects").mkdir(parents=True, exist_ok=True)
    (cast_dir / "peers").mkdir(parents=True, exist_ok=True)
    (cast_dir / "logs").mkdir(parents=True, exist_ok=True)
    (cast_dir / "locks").mkdir(parents=True, exist_ok=True)
    
    # Register in global config
    global_config = GlobalConfig.load_or_create()
    global_config.register_vault(final_vault_id, str(path.absolute()))
    global_config.save()
    
    console.print(f"[green]✓[/green] Initialized Cast in {path}")
    console.print(f"  Vault ID: {final_vault_id}")
    console.print(f"  Registered in global config")


# Create a sub-app for vault commands
vault_app = typer.Typer(name="vault", help="Vault management commands")
app.add_typer(vault_app)


@vault_app.command(name="create")
def vault_create(
    path: Path = typer.Argument(..., help="Path for new vault"),
    template: str = typer.Option("default", help="Vault template to use"),
) -> None:
    """Create a new vault with recommended structure."""
    from cast.vault import create_vault_structure
    
    create_vault_structure(path, template)
    console.print(f"[green]✓[/green] Created vault structure at {path}")


# Create a sub-app for ids commands
ids_app = typer.Typer(name="ids", help="UUID management commands")
app.add_typer(ids_app)


@ids_app.command(name="add")
def ids_add(
    path: Path = typer.Argument(Path.cwd(), help="Vault root directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without applying"),
) -> None:
    """Add cast-id UUIDs to files missing them."""
    results = add_cast_ids(path, dry_run=dry_run)
    
    if dry_run:
        console.print("[yellow]Dry run mode - no changes made[/yellow]")
    
    table = Table(title="Cast ID Assignment")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("UUID", style="dim")
    
    for result in results:
        table.add_row(
            str(result["path"].relative_to(path)),
            result["status"],
            result.get("uuid", "-"),
        )
    
    console.print(table)
    console.print(f"\n[green]✓[/green] Processed {len(results)} files")


@app.command()
def index(
    path: Path = typer.Argument(Path.cwd(), help="Vault root directory"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force full index rebuild"),
) -> None:
    """Build or update the vault index."""
    index_data = build_index(path, rebuild=rebuild)
    
    console.print(f"[green]✓[/green] Index updated")
    console.print(f"  Files indexed: {len(index_data)}")
    console.print(f"  Location: {path / '.cast' / 'index.json'}")


@app.command()
def plan(
    source: str = typer.Argument(..., help="Source vault ID (from global config)"),
    dest: str = typer.Argument(..., help="Destination vault ID (from global config)"),
    rule: Optional[str] = typer.Option(None, "--rule", "-r", help="Sync rule ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save plan to file"),
) -> None:
    """Create a sync plan without applying changes."""
    try:
        plan_data = create_plan(source, dest, rule_id=rule)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Available vaults:[/yellow]")
        config = GlobalConfig.load()
        for name, path in config.vaults.items():
            console.print(f"  • {name}: {path}")
        raise typer.Exit(1)
    
    # Display summary
    table = Table(title="Sync Plan")
    table.add_column("Action", style="bold")
    table.add_column("Count", justify="right")
    
    action_counts = {}
    for action in plan_data["actions"]:
        action_counts[action["type"]] = action_counts.get(action["type"], 0) + 1
    
    for action_type, count in action_counts.items():
        color = {
            "CREATE": "green",
            "UPDATE": "blue", 
            "MERGE": "yellow",
            "CONFLICT": "red",
            "SKIP": "dim",
        }.get(action_type, "white")
        table.add_row(f"[{color}]{action_type}[/{color}]", str(count))
    
    console.print(table)
    
    if output:
        import json
        output.write_text(json.dumps(plan_data, indent=2))
        console.print(f"\n[green]✓[/green] Plan saved to {output}")


@app.command()
def sync(
    source: str = typer.Argument(..., help="Source vault ID (from global config)"),
    dest: str = typer.Argument(..., help="Destination vault ID (from global config)"),
    rule: Optional[str] = typer.Option(None, "--rule", "-r", help="Sync rule ID"),
    apply: bool = typer.Option(False, "--apply", help="Apply changes (otherwise dry run)"),
    force: bool = typer.Option(False, "--force", help="Force sync even with conflicts"),
) -> None:
    """Synchronize vaults according to rules."""
    engine = SyncEngine()
    
    try:
        results = engine.sync(source, dest, rule_id=rule, apply=apply, force=force)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[yellow]Available vaults:[/yellow]")
        config = GlobalConfig.load()
        for name, path in config.vaults.items():
            console.print(f"  • {name}: {path}")
        raise typer.Exit(1)
    
    # Display results
    if not apply:
        console.print("[yellow]Dry run mode - no changes applied[/yellow]\n")
    
    table = Table(title="Sync Results")
    table.add_column("File", style="cyan")
    table.add_column("Action", style="bold")
    table.add_column("Status")
    
    for result in results:
        status_color = "green" if result["success"] else "red"
        table.add_row(
            result["file"],
            result["action"],
            f"[{status_color}]{result['status']}[/{status_color}]",
        )
    
    console.print(table)
    
    conflicts = [r for r in results if r["action"] == "CONFLICT"]
    if conflicts:
        console.print(f"\n[red]⚠ {len(conflicts)} conflicts detected[/red]")
        if apply:
            console.print("[yellow]Conflict files created:[/yellow]")
            for conflict in conflicts:
                console.print(f"  • {conflict.get('file', 'Unknown')}")
            console.print("\n[dim]Run 'cast conflicts' to list all conflicts[/dim]")
            console.print("[dim]Run 'cast resolve' to resolve conflicts interactively[/dim]")
        else:
            console.print("[yellow]Conflicts would be created for:[/yellow]")
            for conflict in conflicts:
                console.print(f"  • {conflict.get('file', 'Unknown')}")
            console.print("\n[dim]Use --apply --force to create conflict files[/dim]")


@app.command()
def resolve(
    vault: Optional[str] = typer.Argument(None, help="Vault ID or path"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Vault path"),
    files: Optional[list[Path]] = typer.Argument(None, help="Specific files to resolve"),
    interactive: bool = typer.Option(True, "--interactive/--batch", help="Interactive mode"),
    auto: str = typer.Option("source", help="Auto-resolve mode: source, dest, base"),
) -> None:
    """Resolve sync conflicts interactively."""
    # Determine vault path
    if vault:
        config = GlobalConfig.load()
        vault_path = config.get_vault_path(vault)
        if not vault_path:
            vault_path = Path(vault)
    elif path:
        vault_path = path
    else:
        vault_path = Path.cwd()
    
    resolver = ConflictResolver()
    results = resolver.resolve(
        vault_path, 
        files=files, 
        interactive=interactive,
        auto_mode=auto if not interactive else "ask"
    )
    
    if not results:
        return
    
    resolved_count = sum(1 for r in results if r["resolved"])
    if resolved_count > 0:
        console.print(f"\n[green]✓ Successfully resolved {resolved_count} conflict(s)[/green]")
    else:
        console.print(f"\n[yellow]No conflicts were resolved[/yellow]")


@app.command(name="conflicts")
def list_conflicts(
    vault: Optional[str] = typer.Argument(None, help="Vault ID or path"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Vault path"),
) -> None:
    """List all conflict files in a vault."""
    # Determine vault path
    if vault:
        config = GlobalConfig.load()
        vault_path = config.get_vault_path(vault)
        if not vault_path:
            vault_path = Path(vault)
    elif path:
        vault_path = path
    else:
        vault_path = Path.cwd()
    
    resolver = ConflictResolver()
    conflict_files = resolver.list_conflicts(vault_path)
    
    if not conflict_files:
        console.print("[green]No conflicts found![/green]")
    else:
        console.print(f"[yellow]Found {len(conflict_files)} conflict file(s)[/yellow]\n")
        for file in conflict_files:
            console.print(f"  • {file.relative_to(vault_path)}")


@app.command()
def commit(
    path: Path = typer.Argument(Path.cwd(), help="Vault root directory"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Commit message"),
    git: bool = typer.Option(False, "--git", help="Also create git commit"),
) -> None:
    """Create a snapshot of current vault state."""
    from cast.snapshot import create_snapshot
    
    snapshot_path = create_snapshot(path, message=message)
    console.print(f"[green]✓[/green] Snapshot created: {snapshot_path}")
    
    if git:
        import subprocess
        
        try:
            subprocess.run(["git", "add", ".cast/"], cwd=path, check=True)
            subprocess.run(
                ["git", "commit", "-m", message or f"Cast snapshot {snapshot_path.name}"],
                cwd=path,
                check=True,
            )
            console.print("[green]✓[/green] Git commit created")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗[/red] Git commit failed: {e}")


@app.command(name="obsidian-init")
def obsidian_init(
    path: Path = typer.Argument(Path.cwd(), help="Vault root directory"),
    profile: str = typer.Option("default", help="Obsidian profile to use"),
) -> None:
    """Initialize Obsidian configuration for the vault."""
    from cast.obsidian import init_obsidian_config
    
    init_obsidian_config(path, profile)
    console.print(f"[green]✓[/green] Obsidian configuration initialized")


@app.command()
def reset(
    vault: Optional[str] = typer.Argument(None, help="Vault ID to reset (from global config)"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Vault path to reset"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    keep_config: bool = typer.Option(False, "--keep-config", help="Keep vault configuration"),
) -> None:
    """Reset a vault's Cast state (.cast directory).
    
    This will:
    - Clear the index
    - Remove all peer states
    - Delete object store
    - Clear logs and locks
    - Optionally keep vault configuration
    
    Use with caution as this cannot be undone!
    """
    import shutil
    
    # Determine vault path
    if vault:
        # Use vault ID from global config
        config = GlobalConfig.load()
        vault_path = config.get_vault_path(vault)
        if not vault_path:
            console.print(f"[red]Error: Vault '{vault}' not found in global config[/red]")
            console.print("\n[yellow]Available vaults:[/yellow]")
            for name, vpath in config.vaults.items():
                console.print(f"  • {name}: {vpath}")
            raise typer.Exit(1)
    elif path:
        vault_path = path
    else:
        vault_path = Path.cwd()
    
    # Check if vault exists and has .cast directory
    cast_dir = vault_path / ".cast"
    if not cast_dir.exists():
        console.print(f"[yellow]No .cast directory found in {vault_path}[/yellow]")
        raise typer.Exit(1)
    
    # Show what will be deleted
    console.print(f"\n[bold]Vault to reset:[/bold] {vault_path}")
    console.print(f"[bold]Cast directory:[/bold] {cast_dir}")
    
    # Count items to be deleted
    index_file = cast_dir / "index.json"
    peers_dir = cast_dir / "peers"
    objects_dir = cast_dir / "objects"
    logs_dir = cast_dir / "logs"
    locks_dir = cast_dir / "locks"
    config_file = cast_dir / "config.yaml"
    
    items_to_delete = []
    if index_file.exists():
        items_to_delete.append("• Index file")
    if peers_dir.exists():
        peer_count = len(list(peers_dir.glob("*.json")))
        if peer_count > 0:
            items_to_delete.append(f"• {peer_count} peer state file(s)")
    if objects_dir.exists():
        obj_count = sum(1 for _ in objects_dir.rglob("*") if _.is_file())
        if obj_count > 0:
            items_to_delete.append(f"• {obj_count} object(s) in store")
    if logs_dir.exists() and any(logs_dir.iterdir()):
        items_to_delete.append("• Log files")
    if locks_dir.exists() and any(locks_dir.iterdir()):
        items_to_delete.append("• Lock files")
    
    if items_to_delete:
        console.print("\n[yellow]The following will be deleted:[/yellow]")
        for item in items_to_delete:
            console.print(f"  {item}")
    else:
        console.print("\n[green]Cast directory is already clean[/green]")
        return
    
    if keep_config:
        console.print("\n[cyan]Vault configuration will be preserved[/cyan]")
    elif config_file.exists():
        console.print("\n[yellow]Vault configuration will also be deleted[/yellow]")
    
    # Confirmation prompt
    if not force:
        console.print("\n[bold red]This action cannot be undone![/bold red]")
        confirm = typer.confirm("Are you sure you want to reset this vault's Cast state?")
        if not confirm:
            console.print("[yellow]Reset cancelled[/yellow]")
            raise typer.Exit(0)
    
    # Perform reset
    console.print("\n[bold]Resetting vault...[/bold]")
    
    # Save config if requested
    saved_config = None
    if keep_config and config_file.exists():
        saved_config = config_file.read_text()
    
    # Delete directories and files
    if index_file.exists():
        index_file.unlink()
        console.print("  [green]✓[/green] Index cleared")
    
    if peers_dir.exists():
        shutil.rmtree(peers_dir)
        console.print("  [green]✓[/green] Peer states removed")
    
    if objects_dir.exists():
        shutil.rmtree(objects_dir)
        console.print("  [green]✓[/green] Object store deleted")
    
    if logs_dir.exists():
        shutil.rmtree(logs_dir)
        console.print("  [green]✓[/green] Logs cleared")
    
    if locks_dir.exists():
        shutil.rmtree(locks_dir)
        console.print("  [green]✓[/green] Locks removed")
    
    # Recreate directory structure
    cast_dir.mkdir(exist_ok=True)
    (cast_dir / "peers").mkdir(exist_ok=True)
    (cast_dir / "objects").mkdir(exist_ok=True)
    (cast_dir / "logs").mkdir(exist_ok=True)
    (cast_dir / "locks").mkdir(exist_ok=True)
    
    # Restore config if saved
    if saved_config:
        config_file.write_text(saved_config)
        console.print("  [green]✓[/green] Configuration preserved")
    
    # Create empty index
    index_file.write_text("{}")
    
    console.print(f"\n[green]✓[/green] Vault reset complete: {vault_path}")
    console.print("[dim]Run 'cast index' to rebuild the index[/dim]")


def main() -> None:
    """Main entry point for the CLI."""
    app()