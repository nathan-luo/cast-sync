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
    import platform
    import subprocess
    
    config = GlobalConfig.load_or_create()
    config_path = config.config_path
    
    # Ensure config file exists
    if not config_path.exists():
        config.save()
    
    # Use EDITOR env var, fallback to platform-specific defaults
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    
    if not editor:
        system = platform.system()
        if system == "Windows":
            # Use notepad on Windows
            try:
                subprocess.run(["notepad", str(config_path)])
                return
            except Exception as e:
                console.print(f"[red]Failed to open config with notepad: {e}[/red]")
                console.print(f"Config location: {config_path}")
                return
        elif system == "Darwin":
            # Use open command on macOS
            try:
                subprocess.run(["open", str(config_path)])
                return
            except Exception as e:
                console.print(f"[red]Failed to open config with default editor: {e}[/red]")
                console.print(f"Config location: {config_path}")
                return
        else:
            # Default to nano on Linux/Unix
            editor = "nano"
    
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
def register(
    name: str = typer.Argument(..., help="Vault name for global registry"),
    path: Path = typer.Argument(..., help="Path to vault"),
) -> None:
    """Register a vault in the global config."""
    config = GlobalConfig.load()
    config.register_vault(name, str(path.resolve()))
    config.save()
    console.print(f"[green]✓[/green] Registered vault '{name}' at {path}")


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
    
    # Create .cast directory structure (simplified)
    cast_dir = path / ".cast"
    cast_dir.mkdir(parents=True, exist_ok=True)
    
    # Create empty sync state file
    sync_state_file = cast_dir / "sync_state.json"
    if not sync_state_file.exists():
        sync_state_file.write_text("{}")
    
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
    fix: bool = typer.Option(False, "--fix", help="Automatically add cast-id to files with cast metadata"),
) -> None:
    """Build or update the vault index."""
    index_data = build_index(path, rebuild=rebuild, auto_fix=fix)
    
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
    vault: Optional[str] = typer.Argument(None, help="Vault ID or path (defaults to current directory)"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Vault path"),
    overpower: bool = typer.Option(False, "--overpower", help="Force current vault's version to all others"),
    batch: bool = typer.Option(False, "--batch", help="Non-interactive mode"),
    legacy: bool = typer.Option(False, "--legacy", help="Use legacy two-vault sync"),
    source: Optional[str] = typer.Option(None, "--source", help="Source vault (legacy mode)"),
    dest: Optional[str] = typer.Option(None, "--dest", help="Destination vault (legacy mode)"),
    apply: bool = typer.Option(True, "--apply/--dry-run", help="Apply changes (default) or dry run"),
    force: bool = typer.Option(False, "--force", help="Proceed even if conflicts are detected (legacy mode)"),
) -> None:
    """Synchronize current vault with all connected vaults.
    
    Simple and reliable sync:
    - Detects differences between vaults
    - Shows both versions for conflicts and lets you choose
    - Use --overpower to force current vault's version everywhere
    - Use --batch for non-interactive mode
    """
    # Handle legacy mode
    if legacy or (source and dest):
        if not source or not dest:
            console.print("[red]Error: Legacy mode requires --source and --dest[/red]")
            raise typer.Exit(1)
        
        engine = SyncEngine()
        
        try:
            results = engine.sync(source, dest, apply=apply, force=force)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("\n[yellow]Available vaults:[/yellow]")
            config = GlobalConfig.load()
            for name, path in config.vaults.items():
                console.print(f"  • {name}: {path}")
            raise typer.Exit(1)
        
        # Display legacy results
        if not apply:
            console.print("[yellow]Dry run mode - no changes applied[/yellow]\n")
        
        table = Table(title="Sync Results (Legacy)")
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
        return
    
    # Simple sync
    from cast.sync_simple import SimpleSyncEngine
    
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
    
    # Verify it's a Cast vault
    if not (vault_path / ".cast" / "config.yaml").exists():
        console.print(f"[red]Error: {vault_path} is not a Cast vault[/red]")
        console.print("Run 'cast init' to initialize a vault first.")
        raise typer.Exit(1)
    
    engine = SimpleSyncEngine()
    
    try:
        result = engine.sync_all(vault_path, overpower=overpower, interactive=not batch)
    except KeyboardInterrupt:
        console.print("\n[yellow]Sync cancelled by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    
    # Display results
    console.print(f"\n[bold]Sync Results:[/bold]")
    
    if result["status"] == "no_other_vaults":
        console.print(f"[dim]{result['message']}[/dim]")
        return
    
    # Show results for each vault
    for vault_name, vault_result in result["vaults"].items():
        synced = vault_result["synced"]
        conflicts = vault_result["conflicts"]
        
        if synced > 0 or conflicts > 0:
            console.print(f"\n[cyan]{vault_name}:[/cyan]")
            if synced > 0:
                console.print(f"  [green]✓[/green] {synced} files synced")
            if conflicts > 0:
                console.print(f"  [yellow]⚠[/yellow] {conflicts} conflicts remain")
            
            # Show actions taken
            if vault_result["actions"]:
                for action in vault_result["actions"][:5]:  # Show first 5
                    action_type = action["type"]
                    if action_type == "COPY_TO_VAULT1":
                        console.print(f"    ← Pulled {action['file']}")
                    elif action_type == "COPY_TO_VAULT2":
                        console.print(f"    → Pushed {action['file']}")
                    elif action_type == "OVERPOWER":
                        console.print(f"    ⚡ Forced {action['file']}")
                    elif action_type == "USE_VAULT1":
                        console.print(f"    ✓ Used current version of {action['file']}")
                    elif action_type == "USE_VAULT2":
                        console.print(f"    ✓ Used {vault_name} version of {action['file']}")
                    elif action_type == "AUTO_MERGE_VAULT1":
                        console.print(f"    ⚡ Auto-merged (used current) {action['file']}")
                    elif action_type == "AUTO_MERGE_VAULT2":
                        console.print(f"    ⚡ Auto-merged (used {vault_name}) {action['file']}")
                    elif action_type == "CONFLICT":
                        console.print(f"    ⚠ Conflict: {action['file']}")
                    elif action_type == "SKIP":
                        console.print(f"    ○ Skipped {action['file']}")
                
                if len(vault_result["actions"]) > 5:
                    console.print(f"    ... and {len(vault_result['actions']) - 5} more")
        else:
            console.print(f"\n[dim]{vault_name}: Already in sync[/dim]")
    
    # Summary
    total_synced = result["synced"]
    total_conflicts = result["conflicts"]
    
    console.print(f"\n[bold]Summary:[/bold]")
    if total_synced > 0:
        console.print(f"  [green]✓ {total_synced} files synced successfully[/green]")
    if total_conflicts > 0:
        console.print(f"  [yellow]⚠ {total_conflicts} conflicts remaining[/yellow]")
        console.print(f"  [dim]Run 'cast sync' again to resolve remaining conflicts[/dim]")
    if total_synced == 0 and total_conflicts == 0:
        console.print(f"  [green]✓ All vaults are in sync![/green]")




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
    sync_state_file = cast_dir / "sync_state.json"
    config_file = cast_dir / "config.yaml"
    
    items_to_delete = []
    if index_file.exists():
        items_to_delete.append("• Index file")
    if sync_state_file.exists():
        items_to_delete.append("• Sync state file")
    
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
    
    # Delete directories that may exist from legacy versions
    to_remove_dirs = ["objects", "peers", "logs", "locks", "snapshots"]
    for d in to_remove_dirs:
        dir_path = cast_dir / d
        if dir_path.exists():
            shutil.rmtree(dir_path, ignore_errors=True)
            console.print(f"  [green]✓[/green] Removed .cast/{d}/")
    
    # Delete files
    if index_file.exists():
        index_file.unlink()
        console.print("  [green]✓[/green] Index cleared")
    
    if sync_state_file.exists():
        sync_state_file.unlink()
        console.print("  [green]✓[/green] Sync state cleared")
    
    # Recreate directory structure
    cast_dir.mkdir(exist_ok=True)
    
    # Restore config if saved
    if saved_config:
        config_file.write_text(saved_config)
        console.print("  [green]✓[/green] Configuration preserved")
    
    # Create empty index and sync state
    index_file.write_text("{}")
    sync_state_file.write_text("{}")
    
    console.print(f"\n[green]✓[/green] Vault reset complete: {vault_path}")
    console.print("[dim]Run 'cast index' to rebuild the index[/dim]")


def main() -> None:
    """Main entry point for the CLI."""
    app()