"""Simple and reliable 3-way merge using difflib."""

import difflib
from typing import List, Tuple


def simple_three_way_merge(
    base: str,
    source: str,
    dest: str
) -> Tuple[str, List[str]]:
    """Perform a simple 3-way merge using difflib.
    
    This implementation:
    1. Uses SequenceMatcher to find changes
    2. Automatically merges non-conflicting changes
    3. Creates conflicts only for overlapping changes
    
    Args:
        base: The common ancestor content
        source: The source version content
        dest: The destination version content
        
    Returns:
        (merged_content, list_of_conflict_descriptions)
    """
    # Split into lines
    base_lines = base.splitlines(keepends=True)
    source_lines = source.splitlines(keepends=True)
    dest_lines = dest.splitlines(keepends=True)
    
    # Get the changes from base to each version
    source_matcher = difflib.SequenceMatcher(None, base_lines, source_lines)
    dest_matcher = difflib.SequenceMatcher(None, base_lines, dest_lines)
    
    source_opcodes = source_matcher.get_opcodes()
    dest_opcodes = dest_matcher.get_opcodes()
    
    # Merge the changes
    merged = []
    conflicts = []
    
    # Convert opcodes to change regions
    source_changes = []
    for tag, i1, i2, j1, j2 in source_opcodes:
        if tag != 'equal':
            source_changes.append((tag, i1, i2, j1, j2))
    
    dest_changes = []
    for tag, i1, i2, j1, j2 in dest_opcodes:
        if tag != 'equal':
            dest_changes.append((tag, i1, i2, j1, j2))
    
    # Process all positions
    base_pos = 0
    source_pos = 0
    dest_pos = 0
    
    # Combine and sort all change points
    change_points = set()
    for _, i1, i2, _, _ in source_changes:
        change_points.add(i1)
        change_points.add(i2)
    for _, i1, i2, _, _ in dest_changes:
        change_points.add(i1)
        change_points.add(i2)
    change_points.add(len(base_lines))
    change_points = sorted(change_points)
    
    last_point = 0
    for point in change_points:
        if point == last_point:
            continue
            
        # Check what happened in this region for each version
        source_region = None
        dest_region = None
        
        for tag, i1, i2, j1, j2 in source_changes:
            if i1 <= last_point and i2 >= point:
                source_region = (tag, i1, i2, j1, j2)
                break
        
        for tag, i1, i2, j1, j2 in dest_changes:
            if i1 <= last_point and i2 >= point:
                dest_region = (tag, i1, i2, j1, j2)
                break
        
        # Determine how to merge this region
        if source_region is None and dest_region is None:
            # No changes - use base
            merged.extend(base_lines[last_point:point])
            
        elif source_region is not None and dest_region is None:
            # Only source changed
            tag, i1, i2, j1, j2 = source_region
            # Add the changed content from source
            if last_point == i1:
                merged.extend(source_lines[j1:j2])
                source_pos = j2
            else:
                # Add unchanged part, then changed part
                merged.extend(base_lines[last_point:i1])
                merged.extend(source_lines[j1:j2])
                source_pos = j2
                
        elif source_region is None and dest_region is not None:
            # Only dest changed
            tag, i1, i2, j1, j2 = dest_region
            # Add the changed content from dest
            if last_point == i1:
                merged.extend(dest_lines[j1:j2])
                dest_pos = j2
            else:
                # Add unchanged part, then changed part
                merged.extend(base_lines[last_point:i1])
                merged.extend(dest_lines[j1:j2])
                dest_pos = j2
                
        else:
            # Both changed - check if it's the same change
            stag, si1, si2, sj1, sj2 = source_region
            dtag, di1, di2, dj1, dj2 = dest_region
            
            source_content = source_lines[sj1:sj2]
            dest_content = dest_lines[dj1:dj2]
            
            if source_content == dest_content:
                # Same change - no conflict
                merged.extend(source_content)
            else:
                # Different changes - conflict
                conflicts.append(f"Conflict at lines {last_point+1}-{point}")
                merged.append("<<<<<<< SOURCE\n")
                merged.extend(source_content)
                merged.append("=======\n")
                merged.extend(dest_content)
                merged.append(">>>>>>> DESTINATION\n")
        
        last_point = point
    
    merged_content = ''.join(merged)
    return merged_content, conflicts


def smart_three_way_merge(
    base: str,
    source: str,
    dest: str
) -> Tuple[str, List[str]]:
    """Smarter 3-way merge that handles more cases automatically.
    
    This uses a simpler approach:
    1. If only one side changed, use that
    2. If both changed the same, use that
    3. If both changed differently at the same place, conflict
    4. If changes are in different places, merge both
    """
    # Handle empty base case
    if not base:
        if source == dest:
            return source, []
        else:
            # No base to compare - create conflict
            conflicts = ["No baseline available - manual merge required"]
            merged = f"<<<<<<< SOURCE\n{source}\n=======\n{dest}\n>>>>>>> DESTINATION\n"
            return merged, conflicts
    
    # Quick checks
    if source == dest:
        return source, []
    if source == base:
        return dest, []
    if dest == base:
        return source, []
    
    # Use unified diff to understand changes better
    base_lines = base.splitlines(keepends=True)
    source_lines = source.splitlines(keepends=True) 
    dest_lines = dest.splitlines(keepends=True)
    
    # Create diff3-style merge
    merged_lines = []
    conflicts = []
    
    # Get hunks for each change
    source_diff = list(difflib.unified_diff(base_lines, source_lines, n=0))
    dest_diff = list(difflib.unified_diff(base_lines, dest_lines, n=0))
    
    # If no actual changes detected, use simple comparison
    if len(source_diff) <= 3:  # Just headers, no actual diff
        return dest, []
    if len(dest_diff) <= 3:
        return source, []
    
    # Parse hunks from diffs
    source_hunks = parse_unified_diff(source_diff)
    dest_hunks = parse_unified_diff(dest_diff)
    
    # Apply changes
    result_lines = base_lines.copy()
    offset = 0
    
    # Sort all hunks by position
    all_hunks = []
    for hunk in source_hunks:
        all_hunks.append(('source', hunk))
    for hunk in dest_hunks:
        all_hunks.append(('dest', hunk))
    all_hunks.sort(key=lambda x: x[1]['base_start'])
    
    # Process hunks
    applied = set()
    for i, (origin, hunk) in enumerate(all_hunks):
        if i in applied:
            continue
            
        # Check for overlapping hunks
        overlaps = []
        for j, (other_origin, other_hunk) in enumerate(all_hunks[i+1:], i+1):
            if other_hunk['base_start'] < hunk['base_start'] + hunk['base_count']:
                overlaps.append((j, other_origin, other_hunk))
        
        if overlaps:
            # Overlapping changes - check if they're the same
            if len(overlaps) == 1:
                j, other_origin, other_hunk = overlaps[0]
                if hunk['lines'] == other_hunk['lines']:
                    # Same change from both sides
                    apply_hunk(result_lines, hunk, offset)
                    offset += len(hunk['lines']) - hunk['base_count']
                    applied.add(i)
                    applied.add(j)
                else:
                    # Different overlapping changes - conflict
                    conflicts.append(f"Conflict at line {hunk['base_start']}")
                    # Create conflict block
                    if origin == 'source':
                        source_lines_h = hunk['lines']
                        dest_lines_h = other_hunk['lines']
                    else:
                        source_lines_h = other_hunk['lines']
                        dest_lines_h = hunk['lines']
                    
                    conflict_block = ["<<<<<<< SOURCE\n"]
                    conflict_block.extend(source_lines_h)
                    conflict_block.append("=======\n")
                    conflict_block.extend(dest_lines_h)
                    conflict_block.append(">>>>>>> DESTINATION\n")
                    
                    # Replace the affected region
                    start = hunk['base_start'] - 1 + offset
                    end = start + max(hunk['base_count'], other_hunk['base_count'])
                    result_lines[start:end] = conflict_block
                    offset += len(conflict_block) - max(hunk['base_count'], other_hunk['base_count'])
                    applied.add(i)
                    applied.add(j)
        else:
            # Non-overlapping change - apply it
            apply_hunk(result_lines, hunk, offset)
            offset += len(hunk['lines']) - hunk['base_count']
            applied.add(i)
    
    return ''.join(result_lines), conflicts


def parse_unified_diff(diff_lines: List[str]) -> List[dict]:
    """Parse unified diff output into hunks."""
    hunks = []
    current_hunk = None
    
    for line in diff_lines:
        if line.startswith('@@'):
            # Parse hunk header: @@ -base_start,base_count +new_start,new_count @@
            parts = line.split()
            base_part = parts[1][1:]  # Remove leading '-'
            if ',' in base_part:
                base_start, base_count = map(int, base_part.split(','))
            else:
                base_start = int(base_part)
                base_count = 1
            
            current_hunk = {
                'base_start': base_start,
                'base_count': base_count,
                'lines': []
            }
            hunks.append(current_hunk)
        elif current_hunk is not None:
            if line.startswith('+'):
                # Added line
                current_hunk['lines'].append(line[1:])
            elif line.startswith('-'):
                # Removed line (track but don't include in result)
                pass
            # Context lines starting with ' ' are ignored in unified diff n=0
    
    return hunks


def apply_hunk(lines: List[str], hunk: dict, offset: int):
    """Apply a hunk to the lines with the given offset."""
    start = hunk['base_start'] - 1 + offset
    end = start + hunk['base_count']
    lines[start:end] = hunk['lines']