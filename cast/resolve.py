"""Conflict resolution for Cast."""

import re
from pathlib import Path
from typing import Any
from datetime import datetime

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel


class ConflictResolver:
    """Interactive conflict resolver."""
    
    def __init__(self):
        """Initialize resolver."""
        self.console = Console()
    
    def list_conflicts(self, vault_root: Path) -> list[Path]:
        """List all conflict files with details."""
        conflict_files = self._find_conflict_files(vault_root)
        
        if not conflict_files:
            self.console.print("[green]No conflicts found![/green]")
            return []
        
        # Separate old-style and in-file conflicts
        old_style = [f for f in conflict_files if ".conflicted-" in f.name]
        in_file = [f for f in conflict_files if ".conflicted-" not in f.name]
        
        if old_style:
            # Create table for old-style conflicts
            table = Table(title=f"Old-style Conflicts (.conflicted-* files)")
            table.add_column("File", style="cyan")
            table.add_column("Original", style="yellow")
            table.add_column("Created", style="dim")
            table.add_column("Conflicts", style="red")
            
            for conflict_file in old_style:
                # Parse filename to get original
                original = self._get_target_file(conflict_file)
                
                # Get timestamp from filename
                match = re.search(r"conflicted-(\d{8})-(\d{6})", conflict_file.name)
                if match:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    timestamp = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}"
                else:
                    timestamp = "Unknown"
                
                # Count conflicts in file
                content = conflict_file.read_text(encoding="utf-8")
                conflicts = self._parse_conflicts(content)
                
                table.add_row(
                    conflict_file.name,
                    original.name,
                    timestamp,
                    str(len(conflicts))
                )
            
            self.console.print(table)
        
        if in_file:
            # Create table for in-file conflicts
            table = Table(title=f"Files with Conflict Markers")
            table.add_column("File", style="cyan")
            table.add_column("Conflicts", style="red")
            
            for conflict_file in in_file:
                # Count conflicts in file
                content = conflict_file.read_text(encoding="utf-8")
                conflicts = self._parse_conflicts(content)
                
                table.add_row(
                    str(conflict_file.relative_to(vault_root)),
                    str(len(conflicts))
                )
            
            self.console.print(table)
        
        self.console.print(f"\n[yellow]Total: {len(conflict_files)} file(s) with conflicts[/yellow]")
        self.console.print("[dim]Run 'cast resolve' to resolve conflicts interactively[/dim]")
        
        return conflict_files
    
    def resolve(
        self,
        vault_root: Path,
        files: list[Path] | None = None,
        interactive: bool = True,
        auto_mode: str = "ask",  # ask, source, dest
    ) -> list[dict[str, Any]]:
        """Resolve conflicts in files.
        
        Args:
            vault_root: Vault root directory
            files: Specific files to resolve (or find all)
            interactive: Use interactive mode
            auto_mode: How to auto-resolve (ask, source, dest)
            
        Returns:
            List of resolution results
        """
        # Find conflict files if not specified
        if not files:
            files = self._find_conflict_files(vault_root)
        
        if not files:
            self.console.print("[green]No conflicts to resolve![/green]")
            return []
        
        # Show what we're resolving
        self.console.print(f"\n[bold]Found {len(files)} conflict file(s) to resolve[/bold]\n")
        
        results = []
        
        for i, file_path in enumerate(files, 1):
            self.console.print(f"[bold cyan]File {i}/{len(files)}: {file_path.name}[/bold cyan]")
            
            if interactive:
                result = self._resolve_interactive(file_path, vault_root)
            else:
                result = self._resolve_auto(file_path, vault_root, mode=auto_mode)
            
            results.append(result)
            
            if result["resolved"]:
                self.console.print(f"[green]✓ Resolved: {result['target']}[/green]\n")
            else:
                self.console.print(f"[yellow]⊘ Skipped: {file_path.name}[/yellow]\n")
        
        # Summary
        resolved_count = sum(1 for r in results if r["resolved"])
        self.console.print(f"\n[bold]Resolution Summary:[/bold]")
        self.console.print(f"  Resolved: {resolved_count}/{len(results)}")
        
        if resolved_count > 0:
            self.console.print("\n[green]✓ Conflicts resolved successfully![/green]")
            self.console.print("[dim]Run 'cast index' to update the index[/dim]")
        
        return results
    
    def _find_conflict_files(self, vault_root: Path) -> list[Path]:
        """Find all files with conflicts (either .conflicted-* or files with conflict markers)."""
        conflict_files = []
        
        # First, find old-style .conflicted-* files
        pattern = "*.conflicted-*.md"
        conflict_files.extend(vault_root.glob(f"**/{pattern}"))
        
        # Also find regular .md files that contain conflict markers
        for md_file in vault_root.glob("**/*.md"):
            # Skip .conflicted-* files and .cast directory
            if ".conflicted-" in md_file.name or ".cast" in str(md_file):
                continue
            
            try:
                content = md_file.read_text(encoding="utf-8")
                if "<<<<<<< " in content and "=======" in content and ">>>>>>> " in content:
                    conflict_files.append(md_file)
            except (UnicodeDecodeError, IOError):
                continue
        
        return sorted(set(conflict_files))
    
    def _resolve_interactive(self, file_path: Path, vault_root: Path) -> dict[str, Any]:
        """Resolve a conflict file interactively."""
        result = {
            "file": str(file_path),
            "resolved": False,
            "action": "skipped",
            "target": None,
        }
        
        # Read conflict file
        content = file_path.read_text(encoding="utf-8")
        
        # Parse conflicts
        conflicts = self._parse_conflicts(content)
        
        if not conflicts:
            self.console.print(f"[yellow]No conflicts found in {file_path}[/yellow]")
            return result
        
        # Show conflict details
        # Check if this is a .conflicted-* file or a regular file with conflicts
        if ".conflicted-" in file_path.name:
            original_file = self._get_target_file(file_path)
            self.console.print(f"[dim]Original file: {original_file.relative_to(vault_root)}[/dim]")
        else:
            original_file = file_path
            self.console.print(f"[dim]File: {original_file.relative_to(vault_root)}[/dim]")
        
        self.console.print(f"[dim]Number of conflicts: {len(conflicts)}[/dim]\n")
        
        resolved_content = content
        
        for i, conflict in enumerate(conflicts, 1):
            self.console.print(f"[bold yellow]━━━ Conflict {i}/{len(conflicts)} ━━━[/bold yellow]")
            
            # Show each version in panels (2-way conflicts only)
            self.console.print("\n[bold cyan]1) SOURCE version:[/bold cyan] [dim](from sync source)[/dim]")
            self._show_content(conflict["source"], "markdown")
            
            self.console.print("\n[bold green]2) DESTINATION version:[/bold green] [dim](your local changes)[/dim]")
            self._show_content(conflict["dest"], "markdown")
            
            choices = ["1", "2", "edit", "skip"]
            choice_map = {"1": "source", "2": "dest"}
            
            # Get choice
            choice = Prompt.ask(
                "\n[bold]Choose resolution[/bold]",
                choices=choices,
                default="1",
            )
            
            if choice in choice_map:
                # Use selected version
                selected = conflict[choice_map[choice]]
                resolved_content = resolved_content.replace(conflict["full"], selected)
                self.console.print(f"[green]→ Using {choice_map[choice].upper()} version[/green]")
            elif choice == "edit":
                # Edit manually
                self.console.print("[yellow]Enter your custom resolution (Ctrl+D when done):[/yellow]")
                lines = []
                try:
                    while True:
                        lines.append(input())
                except EOFError:
                    pass
                edited = "\n".join(lines)
                resolved_content = resolved_content.replace(conflict["full"], edited)
                self.console.print("[green]→ Using custom resolution[/green]")
            else:
                # Skip
                self.console.print("[yellow]→ Keeping conflict markers[/yellow]")
        
        # Ask to save
        self.console.print("\n" + "─" * 40)
        if Confirm.ask("\n[bold]Save resolved file?[/bold]", default=True):
            # Determine target file
            if ".conflicted-" in file_path.name:
                # Old-style conflict file - save to original location
                target = self._get_target_file(file_path)
                
                # Remove original if it exists (no backup needed)
                if target.exists():
                    target.unlink()
                
                # Write resolved content
                target.write_text(resolved_content, encoding="utf-8")
                
                # Remove conflict file
                file_path.unlink()
            else:
                # In-place conflict resolution - save directly
                target = file_path
                
                # Write resolved content (overwrites the file)
                target.write_text(resolved_content, encoding="utf-8")
            
            # Update peer states to mark as resolved
            self._update_peer_states(target, vault_root)
            
            result["resolved"] = True
            result["action"] = "saved"
            result["target"] = str(target.relative_to(vault_root))
        
        return result
    
    def _resolve_auto(self, file_path: Path, vault_root: Path, mode: str = "source") -> dict[str, Any]:
        """Resolve conflicts automatically."""
        result = {
            "file": str(file_path),
            "resolved": False,
            "action": f"auto-{mode}",
            "target": None,
        }
        
        # Read conflict file
        content = file_path.read_text(encoding="utf-8")
        
        # Parse conflicts
        conflicts = self._parse_conflicts(content)
        resolved_content = content
        
        for conflict in conflicts:
            if mode == "source":
                resolved_content = resolved_content.replace(conflict["full"], conflict["source"])
            elif mode == "dest":
                resolved_content = resolved_content.replace(conflict["full"], conflict["dest"])
        
        # Save resolved file
        if ".conflicted-" in file_path.name:
            # Old-style conflict file
            target = self._get_target_file(file_path)
            
            if target.exists():
                target.unlink()
            
            target.write_text(resolved_content, encoding="utf-8")
            file_path.unlink()
        else:
            # In-place resolution
            target = file_path
            target.write_text(resolved_content, encoding="utf-8")
        
        # Update peer states
        self._update_peer_states(target, vault_root)
        
        result["resolved"] = True
        result["target"] = str(target.relative_to(vault_root))
        
        return result
    
    def _parse_conflicts(self, content: str) -> list[dict[str, Any]]:
        """Parse conflict markers from content."""
        conflicts = []
        
        # Pattern for 2-way conflicts (Git-style)
        pattern_2way = re.compile(
            r"<<<<<<< ([^\n]+)\n(.*?)\n=======\n(.*?)\n>>>>>>> ([^\n]+)",
            re.DOTALL,
        )
        
        # Find 2-way conflicts
        for match in pattern_2way.finditer(content):
            conflicts.append({
                "full": match.group(0),
                "source_label": match.group(1),
                "source": match.group(2),
                "dest": match.group(3),
                "dest_label": match.group(4),
            })
        
        return conflicts
    
    def _get_target_file(self, conflict_file: Path) -> Path:
        """Get target file path from conflict file name."""
        # Remove .conflicted-TIMESTAMP suffix
        name = conflict_file.name
        
        # Pattern: original.conflicted-YYYYMMDD-HHMMSS.md
        match = re.match(r"(.+)\.conflicted-\d{8}-\d{6}\.md$", name)
        
        if match:
            original_name = match.group(1) + ".md"
            return conflict_file.parent / original_name
        
        # Fallback
        return conflict_file.with_suffix("")
    
    def _show_content(self, content: str, language: str = "markdown"):
        """Display content with syntax highlighting."""
        # Limit display length
        if len(content) > 500:
            display = content[:500] + "\n... (truncated)"
        else:
            display = content
        
        # Show in a panel with syntax highlighting
        syntax = Syntax(display, language, theme="monokai", line_numbers=False)
        panel = Panel(syntax, border_style="dim")
        self.console.print(panel)
    
    def _update_peer_states(self, resolved_file: Path, vault_root: Path):
        """Update peer states to clear conflict status."""
        from cast.ids import get_cast_id
        from cast.peers import PeerState
        
        # Get cast-id from resolved file
        cast_id = get_cast_id(resolved_file)
        if not cast_id:
            return
        
        # Find all peer state files
        peers_dir = vault_root / ".cast" / "peers"
        if not peers_dir.exists():
            return
        
        for peer_file in peers_dir.glob("*.json"):
            peer_id = peer_file.stem
            peer_state = PeerState(vault_root, peer_id)
            peer_state.load()
            
            # Update file state if it exists
            file_state = peer_state.get_file_state(cast_id)
            if file_state and file_state.get("last_result") == "CONFLICT":
                # Mark as resolved
                peer_state.update_file_state(
                    cast_id,
                    last_result="RESOLVED",
                )
                peer_state.save()
                
                self.console.print(f"[dim]Updated peer state for {peer_id}[/dim]")