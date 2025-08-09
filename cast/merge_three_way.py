"""True 3-way merge implementation for Cast Sync."""

import difflib
from typing import List, Tuple, Optional


def three_way_merge(
    base: str,
    source: str, 
    dest: str,
    conflict_marker_size: int = 7
) -> Tuple[str, List[str]]:
    """Perform a true 3-way merge like Git does.
    
    This implements a line-by-line 3-way merge algorithm that:
    1. Identifies regions that changed in source, dest, or both
    2. Automatically merges non-overlapping changes
    3. Only creates conflicts for overlapping changes
    
    Args:
        base: The common ancestor content
        source: The source version content
        dest: The destination version content
        conflict_marker_size: Size of conflict markers (default 7 for Git compatibility)
        
    Returns:
        (merged_content, list_of_conflict_descriptions)
    """
    base_lines = base.splitlines(keepends=True)
    source_lines = source.splitlines(keepends=True)
    dest_lines = dest.splitlines(keepends=True)
    
    # Perform 3-way merge
    merger = Merge3(base_lines, source_lines, dest_lines)
    merged_lines, conflict_count = merger.merge_lines(conflict_marker_size)
    
    merged_content = ''.join(merged_lines)
    
    conflicts = []
    if conflict_count > 0:
        conflicts.append(f"{conflict_count} conflict(s) found")
    
    return merged_content, conflicts


class Merge3:
    """3-way merge implementation based on diff3 algorithm."""
    
    def __init__(self, base: List[str], source: List[str], dest: List[str]):
        self.base = base if base else []
        self.source = source if source else []
        self.dest = dest if dest else []
        
    def merge_lines(self, conflict_marker_size: int = 7) -> Tuple[List[str], int]:
        """Merge lines and return merged content with conflict count."""
        merged = []
        conflict_count = 0
        
        # Get matching blocks between base and each version
        base_source_matches = difflib.SequenceMatcher(None, self.base, self.source).get_matching_blocks()
        base_dest_matches = difflib.SequenceMatcher(None, self.base, self.dest).get_matching_blocks()
        
        # Process regions
        regions = self._get_merge_regions()
        
        for region_type, base_start, base_end, source_start, source_end, dest_start, dest_end in regions:
            if region_type == 'unchanged':
                # All three versions are the same
                merged.extend(self.source[source_start:source_end])
                
            elif region_type == 'source_only':
                # Only source changed
                merged.extend(self.source[source_start:source_end])
                
            elif region_type == 'dest_only':
                # Only dest changed
                merged.extend(self.dest[dest_start:dest_end])
                
            elif region_type == 'both_same':
                # Both changed in the same way
                merged.extend(self.source[source_start:source_end])
                
            elif region_type == 'conflict':
                # Both changed differently - create conflict
                conflict_count += 1
                marker = '<' * conflict_marker_size
                merged.append(f"{marker} SOURCE\n")
                merged.extend(self.source[source_start:source_end])
                merged.append(f"{'=' * conflict_marker_size}\n")
                merged.extend(self.dest[dest_start:dest_end])
                marker = '>' * conflict_marker_size
                merged.append(f"{marker} DESTINATION\n")
        
        return merged, conflict_count
    
    def _get_merge_regions(self) -> List[Tuple]:
        """Get regions for merging.
        
        Returns list of tuples:
        (region_type, base_start, base_end, source_start, source_end, dest_start, dest_end)
        
        Where region_type is one of:
        - 'unchanged': All three versions are the same
        - 'source_only': Only source changed from base
        - 'dest_only': Only dest changed from base  
        - 'both_same': Both changed in the same way
        - 'conflict': Both changed differently
        """
        regions = []
        
        # Get hunks (changed regions) for each diff
        source_hunks = self._get_hunks(self.base, self.source)
        dest_hunks = self._get_hunks(self.base, self.dest)
        
        # Merge hunks into regions
        all_hunks = []
        for hunk in source_hunks:
            all_hunks.append(('source', hunk))
        for hunk in dest_hunks:
            all_hunks.append(('dest', hunk))
        
        # Sort by base position
        all_hunks.sort(key=lambda x: x[1][0])
        
        # Process hunks to identify regions
        base_pos = 0
        source_pos = 0
        dest_pos = 0
        
        i = 0
        while i < len(all_hunks):
            hunk_type, (base_start, base_end, changed_start, changed_end) = all_hunks[i]
            
            # Add unchanged region before this hunk
            if base_pos < base_start:
                unchanged_len = base_start - base_pos
                regions.append((
                    'unchanged',
                    base_pos, base_start,
                    source_pos, source_pos + unchanged_len,
                    dest_pos, dest_pos + unchanged_len
                ))
                source_pos += unchanged_len
                dest_pos += unchanged_len
                base_pos = base_start
            
            # Check for overlapping hunks
            overlapping = []
            j = i + 1
            while j < len(all_hunks):
                next_type, (next_base_start, next_base_end, _, _) = all_hunks[j]
                if next_base_start < base_end:
                    # Overlapping hunk
                    overlapping.append(all_hunks[j])
                    j += 1
                else:
                    break
            
            if overlapping:
                # Handle overlapping changes (potential conflict)
                merged_region = self._merge_overlapping_hunks(
                    all_hunks[i], overlapping, base_pos, source_pos, dest_pos
                )
                regions.append(merged_region)
                
                # Update positions
                if hunk_type == 'source':
                    source_pos += (changed_end - changed_start)
                    dest_pos += (base_end - base_start)
                else:
                    dest_pos += (changed_end - changed_start)
                    source_pos += (base_end - base_start)
                    
                base_pos = base_end
                for _, (ob_start, ob_end, _, _) in overlapping:
                    if ob_end > base_pos:
                        base_pos = ob_end
                
                i = j
            else:
                # Non-overlapping change
                if hunk_type == 'source':
                    regions.append((
                        'source_only',
                        base_start, base_end,
                        changed_start, changed_end,
                        dest_pos, dest_pos + (base_end - base_start)
                    ))
                    source_pos = changed_end
                    dest_pos += (base_end - base_start)
                else:
                    regions.append((
                        'dest_only',
                        base_start, base_end,
                        source_pos, source_pos + (base_end - base_start),
                        changed_start, changed_end
                    ))
                    dest_pos = changed_end
                    source_pos += (base_end - base_start)
                    
                base_pos = base_end
                i += 1
        
        # Add final unchanged region
        if base_pos < len(self.base):
            unchanged_len = len(self.base) - base_pos
            regions.append((
                'unchanged',
                base_pos, len(self.base),
                source_pos, source_pos + unchanged_len,
                dest_pos, dest_pos + unchanged_len
            ))
        
        return regions
    
    def _get_hunks(self, base: List[str], changed: List[str]) -> List[Tuple[int, int, int, int]]:
        """Get hunks (changed regions) between base and changed.
        
        Returns list of (base_start, base_end, changed_start, changed_end) tuples.
        """
        hunks = []
        matcher = difflib.SequenceMatcher(None, base, changed)
        
        for tag, base_start, base_end, changed_start, changed_end in matcher.get_opcodes():
            if tag != 'equal':
                hunks.append((base_start, base_end, changed_start, changed_end))
        
        return hunks
    
    def _merge_overlapping_hunks(
        self,
        first_hunk: Tuple,
        overlapping: List[Tuple],
        base_pos: int,
        source_pos: int,
        dest_pos: int
    ) -> Tuple:
        """Merge overlapping hunks into a single region.
        
        This is where we determine if changes can be merged or if they conflict.
        """
        first_type, (base_start, base_end, changed_start, changed_end) = first_hunk
        
        # For simplicity, if we have overlapping changes, create a conflict
        # In a more sophisticated implementation, we could try to merge
        # non-conflicting line changes within the overlapping region
        
        # Find the extent of all overlapping changes
        max_base_end = base_end
        source_extent = changed_end if first_type == 'source' else source_pos + (base_end - base_pos)
        dest_extent = changed_end if first_type == 'dest' else dest_pos + (base_end - base_pos)
        
        for ov_type, (ov_base_start, ov_base_end, ov_changed_start, ov_changed_end) in overlapping:
            if ov_base_end > max_base_end:
                max_base_end = ov_base_end
            if ov_type == 'source':
                source_extent = max(source_extent, ov_changed_end)
            else:
                dest_extent = max(dest_extent, ov_changed_end)
        
        # Check if the changes are identical
        source_changes = self.source[source_pos:source_extent]
        dest_changes = self.dest[dest_pos:dest_extent]
        
        if source_changes == dest_changes:
            # Both made the same change
            return (
                'both_same',
                base_start, max_base_end,
                source_pos, source_extent,
                dest_pos, dest_extent
            )
        else:
            # Different changes - conflict
            return (
                'conflict',
                base_start, max_base_end,
                source_pos, source_extent,
                dest_pos, dest_extent
            )


def merge_with_base(base: str, source: str, dest: str) -> Tuple[str, bool]:
    """Simple wrapper for 3-way merge that returns merged content and conflict flag.
    
    Args:
        base: Base/ancestor content
        source: Source content
        dest: Destination content
        
    Returns:
        (merged_content, has_conflicts)
    """
    merged, conflicts = three_way_merge(base, source, dest)
    return merged, len(conflicts) > 0