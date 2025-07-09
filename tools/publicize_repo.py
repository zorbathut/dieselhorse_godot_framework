#!/usr/bin/env python3
"""
Git Repository Filter - Remove sensitive data from Git history based on gitignore patterns
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple, DefaultDict
from collections import defaultdict
import subprocess
import tempfile
import shutil
import util
import build_utils

util.cwdhack()

try:
    import git
    from git import Repo, Actor, NULL_TREE
except ImportError:
    print("Error: GitPython is required. Install with: pip install GitPython")
    sys.exit(1)

try:
    import pathspec
except ImportError:
    print("Error: pathspec is required. Install with: pip install pathspec")
    sys.exit(1)


class GitRepoFilter:
    def __init__(self, source_repo_path: str, target_repo_path: str, 
                 ignore_file_path: str, filter_commits_file: Optional[str] = None, 
                 verbose: bool = False):
        """
        Initialize the Git repository filter.
        
        Args:
            source_repo_path: Path to source repository
            target_repo_path: Path where filtered repository will be created
            ignore_file_path: Path to gitignore-style file with patterns
            filter_commits_file: Optional path to file containing commit SHAs to filter
            verbose: Enable verbose logging
        """
        self.source_repo = Repo(source_repo_path)
        self.target_repo_path = Path(target_repo_path)
        self.ignore_file_path = Path(ignore_file_path)
        self.filter_commits_file = filter_commits_file
        self.verbose = verbose
        
        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Load ignore patterns
        self.pathspec = self._load_pathspec()
        
        # Load filtered commits if provided
        self.filtered_commits = self._load_filtered_commits()
        
        # Mapping from old commit SHA to new commit SHA
        self.commit_map: Dict[str, Optional[str]] = {}
        
        # Mapping to track tags that point to filtered commits
        self.filtered_commit_tags: DefaultDict[str, List[git.TagReference]] = defaultdict(list)
        
        # Cache for mapping filtered commits to their next valid descendants
        self.next_valid_commit_cache: Dict[str, Optional[str]] = {}
        
        # Statistics
        self.stats = {
            'total_commits': 0,
            'filtered_commits': 0,
            'kept_commits': 0,
            'total_files': 0,
            'filtered_files': 0,
            'explicitly_filtered_commits': 0,
            'propagated_tags': 0
        }
        
        # Persistent working directory
        self.work_dir = None
        
        # Map of file paths to their current blob hexsha in working directory
        # Format: {path: hexsha}
        self.working_dir_state = {}
    
    def _load_pathspec(self) -> pathspec.PathSpec:
        """Load gitignore-style patterns from file."""
        with open(self.ignore_file_path, 'r') as f:
            patterns = f.read().splitlines()
        
        # Filter out empty lines and comments
        patterns = [p.strip() for p in patterns if p.strip() and not p.strip().startswith('#')]
        
        # Always add patterns to ignore index and .git
        patterns.extend(['index', '.git', '.git/**'])
        
        self.logger.info(f"Loaded {len(patterns)} ignore patterns")
        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    
    def _resolve_commit_ref(self, commit_ref: str) -> Optional[str]:
        """
        Resolve a commit reference (which might be a prefix) to a full SHA.
        
        Args:
            commit_ref: A commit reference (full SHA, prefix, tag, branch, etc.)
            
        Returns:
            Full SHA if found, None otherwise
        """
        try:
            # This will work with full SHAs, prefixes, tags, branches, etc.
            commit = self.source_repo.commit(commit_ref)
            return commit.hexsha
        except (ValueError, git.exc.BadName, git.exc.BadObject):
            return None
    
    def _load_filtered_commits(self) -> Set[str]:
        """Load list of commits to filter from file."""
        filtered_commits = set()
        
        if self.filter_commits_file:
            try:
                with open(self.filter_commits_file, 'r') as f:
                    for line in f:
                        # Strip and clean the line
                        commit_ref = line.strip()
                        
                        # Skip empty lines and comments
                        if not commit_ref or commit_ref.startswith('#'):
                            continue
                        
                        # Resolve the commit reference to a full SHA
                        commit_sha = self._resolve_commit_ref(commit_ref)
                        if commit_sha:
                            filtered_commits.add(commit_sha)
                        else:
                            self.logger.warning(f"Commit reference '{commit_ref}' not found in repository, skipping")
                
                self.logger.info(f"Loaded {len(filtered_commits)} commits to explicitly filter")
            except Exception as e:
                self.logger.error(f"Error loading filtered commits file: {e}")
        
        return filtered_commits
    
    def _should_ignore(self, file_path: str) -> bool:
        """Check if a file path should be ignored based on patterns."""
        # Normalize path separators for consistent matching
        file_path = file_path.replace(os.sep, '/')
        return self.pathspec.match_file(file_path)
    
    def _should_filter_commit(self, commit: git.Commit) -> bool:
        """Check if a commit should be explicitly filtered."""
        return commit.hexsha in self.filtered_commits
    
    def _get_filtered_tree_for_commit(self, commit: git.Commit) -> Dict[str, git.Blob]:
        """
        Get the complete filtered file tree for a commit.
        Returns a dict mapping file paths to blob objects for all non-ignored files.
        """
        filtered_tree = {}
        filtered_count = 0
        
        # Traverse the entire tree for this commit
        for item in commit.tree.traverse():
            if item.type == 'blob':
                # Check if this file should be ignored
                if not self._should_ignore(item.path):
                    filtered_tree[item.path] = item
                else:
                    filtered_count += 1
        
        # Only count filtered files once per commit (not cumulative)
        if filtered_count > 0:
            self.stats['filtered_files'] += filtered_count
            self.logger.debug(f"Filtered out {filtered_count} files from commit {commit.hexsha[:8]}")
        
        return filtered_tree
    
    
    def _setup_work_environment(self, target_repo: Repo):
        """Set up a persistent working directory and index for all commits."""
        # Create a temporary directory for the working directory
        self.work_dir = tempfile.mkdtemp(prefix="git_filter_")
        self.logger.debug(f"Created persistent working directory: {self.work_dir}")
        
        # Reset working directory state tracking
        self.working_dir_state = {}
        
        # Create a temp directory for git index outside the working directory
        index_dir = tempfile.mkdtemp(prefix="git_filter_index_")
        index_path = os.path.join(index_dir, "index")
        
        # Set up environment for git operations
        self.git_env = os.environ.copy()
        self.git_env['GIT_INDEX_FILE'] = index_path
        
        # Create an empty git index
        subprocess.run(
            ['git', '--git-dir', str(target_repo.git_dir), 'read-tree', '--empty'],
            env=self.git_env,
            check=True,
            capture_output=True
        )
        
        # Create a .gitignore file in the working directory to prevent indexing unwanted files
        gitignore_path = os.path.join(self.work_dir, '.gitignore')
        with open(gitignore_path, 'w') as f:
            f.write("# Automatically added by publicize_repo.py\n")
            f.write("index\n")
            f.write(".git\n")
            f.write(".git/**\n")
        
        # Store index_dir for cleanup
        self.index_dir = index_dir
    
    def _cleanup_work_environment(self):
        """Clean up the persistent working directory."""
        # Clean up working directory
        if self.work_dir and os.path.exists(self.work_dir):
            self.logger.debug(f"Removing working directory: {self.work_dir}")
            shutil.rmtree(self.work_dir, ignore_errors=True)
            self.work_dir = None
        
        # Clean up index directory
        if hasattr(self, 'index_dir') and self.index_dir and os.path.exists(self.index_dir):
            self.logger.debug(f"Removing index directory: {self.index_dir}")
            shutil.rmtree(self.index_dir, ignore_errors=True)
            self.index_dir = None
    
    def _update_working_directory(self, desired_tree: Dict[str, git.Blob], target_repo: Repo):
        """
        Update the working directory to match the desired tree state.
        Only modifies files that have changed, been added, or need to be deleted.
        
        Args:
            desired_tree: Dict mapping file paths to blob objects representing desired state
            target_repo: Target repository object
        """
        # Find files to delete (exist in working dir but not in desired tree)
        files_to_delete = set(self.working_dir_state.keys()) - set(desired_tree.keys())
        
        # Delete files that shouldn't exist
        for path in files_to_delete:
            full_path = Path(self.work_dir) / path
            if full_path.exists():
                full_path.unlink()
                self.logger.debug(f"Deleted file: {path}")
                
                # Clean up empty parent directories
                try:
                    parent = full_path.parent
                    while parent != Path(self.work_dir) and parent.exists():
                        if not any(parent.iterdir()):  # Directory is empty
                            parent.rmdir()
                            parent = parent.parent
                        else:
                            break
                except OSError:
                    pass  # Directory not empty or other error, that's fine
                    
            # Remove from our state tracking
            del self.working_dir_state[path]
        
        # Update or create files
        files_updated = 0
        for path, blob in desired_tree.items():
            # Check if file needs updating
            if path in self.working_dir_state and self.working_dir_state[path] == blob.hexsha:
                # File hasn't changed, skip it
                continue
            
            full_path = Path(self.work_dir) / path
            
            # Get blob content
            blob_data = self.source_repo.odb.stream(blob.binsha).read()
            
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(full_path, 'wb') as f:
                f.write(blob_data)
            
            # Preserve file permissions (Git tracks executable bit)
            # Git file modes: 100644 (regular file), 100755 (executable file)
            if blob.mode == 0o100755:  # Executable file
                os.chmod(full_path, 0o755)
            else:
                os.chmod(full_path, 0o644)
            
            # Update our state tracking
            self.working_dir_state[path] = blob.hexsha
            self.logger.debug(f"Updated file: {path}")
            files_updated += 1
        
        # Update statistics
        self.stats['total_files'] += files_updated + len(files_to_delete)
    
    def _collect_tags_for_commit(self, commit: git.Commit):
        """
        Collect tags that point to this commit for later propagation.
        Only called when a commit will be filtered out.
        """
        # Find all tags that point to this commit
        collected = 0
        for tag in self.source_repo.tags:
            if tag.commit.hexsha == commit.hexsha:
                # Store the tag with its commit SHA for later propagation
                self.filtered_commit_tags[commit.hexsha].append(tag)
                collected += 1
                self.logger.debug(f"Tag {tag.name} points to filtered commit {commit.hexsha[:8]}, will be propagated")
        
        if collected > 0:
            # Log a summary if multiple tags were collected
            if collected > 1:
                self.logger.info(f"Collected {collected} tags from filtered commit {commit.hexsha[:8]}")
            else:
                self.logger.debug(f"Collected 1 tag from filtered commit {commit.hexsha[:8]}")
    
    def _create_filtered_commit(self, source_commit: git.Commit, target_repo: Repo) -> Optional[git.Commit]:
        """
        Create a filtered version of a commit using the persistent working directory.
        
        Returns:
            New commit object if any files were kept, None otherwise
        """
        # Check if this commit should be explicitly filtered
        if self._should_filter_commit(source_commit):
            self.logger.info(f"Explicitly filtering commit {source_commit.hexsha[:8]} - {source_commit.message.splitlines()[0]}")
            self.stats['explicitly_filtered_commits'] += 1
            self.stats['filtered_commits'] += 1
            self._collect_tags_for_commit(source_commit)
            return None
        
        # Get the complete filtered tree for this commit
        filtered_tree = self._get_filtered_tree_for_commit(source_commit)
        
        # Skip commit if no files are kept
        if not filtered_tree:
            self.logger.debug(f"Skipping commit {source_commit.hexsha[:8]} - no files remain after filtering")
            self.stats['filtered_commits'] += 1
            self._collect_tags_for_commit(source_commit)
            return None
        
        self.logger.debug(f"Processing commit {source_commit.hexsha[:8]} with {len(filtered_tree)} files")
        
        # Map parent commits - traverse up the chain to find non-filtered parents
        new_parents = []
        processed_ancestors = set()  # Avoid infinite loops
        
        def find_non_filtered_ancestors(commit_sha):
            """Recursively find non-filtered ancestors"""
            if commit_sha in processed_ancestors:
                return
            processed_ancestors.add(commit_sha)
            
            if commit_sha in self.commit_map:
                mapped_sha = self.commit_map[commit_sha]
                if mapped_sha:
                    # This commit exists in filtered repo
                    if mapped_sha not in new_parents:
                        new_parents.append(mapped_sha)
                else:
                    # This commit was filtered out, check its parents
                    source_commit_obj = self.source_repo.commit(commit_sha)
                    for parent in source_commit_obj.parents:
                        find_non_filtered_ancestors(parent.hexsha)
        
        # Find ancestors for each parent
        for parent in source_commit.parents:
            find_non_filtered_ancestors(parent.hexsha)
        
        if source_commit.parents:
            self.logger.debug(f"Mapped {len(source_commit.parents)} parents to {len(new_parents)} parents")
        
        # Update working directory to match the filtered tree
        self._update_working_directory(filtered_tree, target_repo)
        
        # Add all files to index using a single command for better performance
        subprocess.run(
            ['git', '--git-dir', str(target_repo.git_dir), 'add', '-A', '--ignore-errors'],
            cwd=self.work_dir,
            env=self.git_env,
            check=True,
            capture_output=True
        )
        
        # Write tree
        result = subprocess.run(
            ['git', '--git-dir', str(target_repo.git_dir), 'write-tree'],
            cwd=self.work_dir,
            env=self.git_env,
            check=True,
            capture_output=True,
            text=True
        )
        tree_sha = result.stdout.strip()
        
        # Check if this tree is identical to all parent trees
        # For merge commits, only filter if it matches ALL parents (not just one)
        if new_parents:
            if len(new_parents) == 1:
                # Single parent - filter if tree matches
                parent_commit = target_repo.commit(new_parents[0])
                if parent_commit.tree.hexsha == tree_sha:
                    self.logger.debug(f"Skipping commit {source_commit.hexsha[:8]} - tree identical to parent after filtering")
                    self.stats['filtered_commits'] += 1
                    self._collect_tags_for_commit(source_commit)
                    return None
            else:
                # Multiple parents (merge commit) - only filter if matches ALL parents
                all_match = True
                for parent_sha in new_parents:
                    parent_commit = target_repo.commit(parent_sha)
                    if parent_commit.tree.hexsha != tree_sha:
                        all_match = False
                        break
                
                if all_match:
                    self.logger.debug(f"Skipping merge commit {source_commit.hexsha[:8]} - tree identical to all parents after filtering")
                    self.stats['filtered_commits'] += 1
                    self._collect_tags_for_commit(source_commit)
                    return None
        else:
            # For initial commits, check if the tree is empty
            # Git's well-known empty tree SHA
            EMPTY_TREE_SHA = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
            
            if tree_sha == EMPTY_TREE_SHA:
                self.logger.debug(f"Skipping commit {source_commit.hexsha[:8]} - empty tree after filtering")
                self.stats['filtered_commits'] += 1
                self._collect_tags_for_commit(source_commit)
                return None
        
        # Create commit
        commit_env = self.git_env.copy()
        commit_env.update({
            'GIT_AUTHOR_NAME': source_commit.author.name or 'Unknown',
            'GIT_AUTHOR_EMAIL': source_commit.author.email or 'unknown@example.com',
            'GIT_AUTHOR_DATE': source_commit.authored_datetime.strftime('%s %z'),
            'GIT_COMMITTER_NAME': source_commit.committer.name or 'Unknown',
            'GIT_COMMITTER_EMAIL': source_commit.committer.email or 'unknown@example.com',
            'GIT_COMMITTER_DATE': source_commit.committed_datetime.strftime('%s %z')
        })
        
        # Build commit-tree command
        cmd = ['git', '--git-dir', str(target_repo.git_dir), 'commit-tree', tree_sha]
        for parent_sha in new_parents:
            cmd.extend(['-p', parent_sha])
        
        # Create commit
        result = subprocess.run(
            cmd,
            input=source_commit.message,
            env=commit_env,
            check=True,
            capture_output=True,
            text=True
        )
        new_commit_sha = result.stdout.strip()
        
        # Get the commit object
        new_commit = target_repo.commit(new_commit_sha)
        
        self.stats['kept_commits'] += 1
        self.logger.debug(f"Created commit {new_commit.hexsha[:8]} from {source_commit.hexsha[:8]} with {len(new_parents)} parent(s)")
        
        return new_commit
    
    def _find_next_valid_commit(self, filtered_commit_sha: str) -> Optional[str]:
        """
        Find the next valid (non-filtered) commit in the chain.
        This is used to propagate tags from filtered commits to their descendants.
        
        Args:
            filtered_commit_sha: SHA of a filtered commit
            
        Returns:
            SHA of the next valid commit, or None if not found
        """
        # Check cache first
        if filtered_commit_sha in self.next_valid_commit_cache:
            return self.next_valid_commit_cache[filtered_commit_sha]
            
        # Find all children of the filtered commit using git rev-list
        # This is much faster than iterating through all commits
        try:
            result = subprocess.run(
                ['git', 'rev-list', '--all', '--children'],
                cwd=self.source_repo.working_dir,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Parse the output: each line is "commit child1 child2 ..."
            children = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if parts and parts[0] == filtered_commit_sha and len(parts) > 1:
                    # Found children of our filtered commit
                    for child_sha in parts[1:]:
                        try:
                            child = self.source_repo.commit(child_sha)
                            children.append(child)
                        except (git.exc.BadName, ValueError):
                            continue
                    break
        
            # If no children, we can't propagate
            if not children:
                self.next_valid_commit_cache[filtered_commit_sha] = None
                return None
            
            # Sort children by commit date to find the "next" one
            children.sort(key=lambda c: c.committed_date)
            
            # Look for a valid child
            for child in children:
                if child.hexsha in self.commit_map and self.commit_map[child.hexsha]:
                    # Found a direct child that's kept
                    self.next_valid_commit_cache[filtered_commit_sha] = self.commit_map[child.hexsha]
                    return self.commit_map[child.hexsha]
                elif child.hexsha in self.commit_map:
                    # Child is filtered, try to find its next valid descendant
                    next_valid = self._find_next_valid_commit(child.hexsha)
                    if next_valid:
                        self.next_valid_commit_cache[filtered_commit_sha] = next_valid
                        return next_valid
            
            # No valid descendant found
            self.next_valid_commit_cache[filtered_commit_sha] = None
            return None
            
        except Exception as e:
            self.logger.warning(f"Error finding children for commit {filtered_commit_sha[:8]}: {e}")
            self.next_valid_commit_cache[filtered_commit_sha] = None
            return None
    
    def _propagate_tags(self, target_repo: Repo):
        """
        Propagate tags from filtered commits to their next valid (non-filtered) commit.
        This is called after all commits have been processed.
        """
        propagated = 0
        skipped = 0
        failed = 0
        
        # Gather existing tag names in target repo to avoid conflicts
        existing_tag_names = set(tag.name for tag in target_repo.tags)
        
        self.logger.info(f"Propagating tags from {len(self.filtered_commit_tags)} filtered commits...")
        
        for commit_sha, tags in self.filtered_commit_tags.items():
            # Skip if no tags to propagate
            if not tags:
                continue
                
            self.logger.debug(f"Finding next valid commit for filtered commit {commit_sha[:8]} with {len(tags)} tags")
            next_valid_commit_sha = self._find_next_valid_commit(commit_sha)
            
            if not next_valid_commit_sha:
                skipped += len(tags)
                self.logger.debug(f"No valid descendant found for filtered commit {commit_sha[:8]}, skipping {len(tags)} tags")
                continue
            
            for tag in tags:
                # Skip if tag already exists in target repo
                if tag.name in existing_tag_names:
                    self.logger.debug(f"Tag {tag.name} already exists in target repo, skipping propagation")
                    skipped += 1
                    continue
                    
                try:
                    # Get original commit message for reference
                    source_commit = self.source_repo.commit(commit_sha)
                    commit_msg = source_commit.message.splitlines()[0] if source_commit.message else "Unknown"
                    
                    # Create tag pointing to the next valid commit
                    if hasattr(tag, 'tag') and tag.tag:
                        # Annotated tag
                        tag_msg = tag.tag.message if tag.tag.message else ""
                        propagation_note = (
                            f"\n\nNote: This tag was originally on filtered commit {commit_sha[:8]}"
                            f"\nOriginal commit message: {commit_msg}"
                        )
                        target_repo.create_tag(
                            tag.name, 
                            ref=next_valid_commit_sha,
                            message=f"{tag_msg}{propagation_note}"
                        )
                    else:
                        # Lightweight tag
                        target_repo.create_tag(tag.name, ref=next_valid_commit_sha)
                    
                    # Add to existing tags set to avoid duplicates
                    existing_tag_names.add(tag.name)
                    
                    self.logger.info(f"Propagated tag {tag.name} from filtered commit {commit_sha[:8]} to {next_valid_commit_sha[:8]}")
                    propagated += 1
                except Exception as e:
                    self.logger.warning(f"Could not propagate tag {tag.name}: {e}")
                    failed += 1
        
        self.stats['propagated_tags'] = propagated
        
        if propagated > 0 or skipped > 0 or failed > 0:
            self.logger.info(f"Tag propagation summary: {propagated} propagated, {skipped} skipped, {failed} failed")
        else:
            self.logger.info("No tags needed propagation")
    
    def filter_repository(self):
        """Main method to filter the repository."""
        # Create target repository
        if self.target_repo_path.exists():
            if input(f"Target path {self.target_repo_path} exists. Remove it? (y/n): ").lower() != 'y':
                self.logger.error("Target path exists, aborting")
                return
            shutil.rmtree(self.target_repo_path)
        
        self.target_repo_path.mkdir(parents=True)
        target_repo = Repo.init(self.target_repo_path)
        
        # Set up persistent working directory
        self._setup_work_environment(target_repo)
        
        try:
            # Get only commits from the dev branch in topological order
            # First check if 'dev' branch exists
            dev_branch = None
            for branch in self.source_repo.branches:
                if branch.name == 'dev':
                    dev_branch = branch
                    break
            
            if not dev_branch:
                self.logger.error("No 'dev' branch found in source repository")
                return
            
            commits = list(self.source_repo.iter_commits(dev_branch, topo_order=True))
            commits.reverse()  # Process in chronological order
            
            self.stats['total_commits'] = len(commits)
            self.logger.info(f"Processing {len(commits)} commits...")
            
            # Process each commit
            for i, commit in enumerate(commits):
                if i % 10 == 0 or i == len(commits) - 1:
                    self.logger.info(f"Progress: {i+1}/{len(commits)} commits processed")
                
                try:
                    # Create filtered commit
                    new_commit = self._create_filtered_commit(commit, target_repo)
                    
                    if new_commit:
                        # Store mapping to new commit
                        self.commit_map[commit.hexsha] = new_commit.hexsha
                    else:
                        # If commit was skipped, we need to handle parent mapping carefully
                        # This commit doesn't exist in the new repo, so we need to help its children
                        # find their ancestors by storing what this commit's parents map to
                        
                        # Don't store a mapping - let children traverse up to find parents
                        self.commit_map[commit.hexsha] = None
                        self.logger.debug(f"Commit {commit.hexsha[:8]} was filtered out")
                except Exception as e:
                    self.logger.error(f"Error processing commit {commit.hexsha[:8]}: {e}")
                    self.commit_map[commit.hexsha] = None
            
            # Update branches
            self._update_branches(target_repo)
            
            # First create tags for non-filtered commits
            self._update_tags(target_repo)
            
            # Then propagate tags from filtered commits to their next valid commit
            self._propagate_tags(target_repo)
            
            # Check out the dev branch to populate the working directory
            self.logger.info("Checking out dev branch in target repository...")
            try:
                # Reset hard to dev branch to populate working directory
                target_repo.git.checkout('dev', force=True)
                target_repo.head.reset(index=True, working_tree=True)
                self.logger.info("Successfully checked out dev branch")
                
                # Post-process: Replace project name with 'nutdealer'
                self._replace_project_name(target_repo)
                
            except Exception as e:
                self.logger.error(f"Error checking out dev branch: {e}")
            
            # Add remote and fetch
            self.logger.info("Adding remote origin and fetching...")
            try:
                target_repo.git.remote('add', 'origin', 'git@github.com:zorbathut/dieselhorse_godot_framework.git')
                self.logger.info("Added remote origin")
                
                # Fetch from remote
                target_repo.git.fetch('origin')
                self.logger.info("Fetched from remote origin")
            except Exception as e:
                self.logger.error(f"Error setting up remote: {e}")
            
            # Print statistics
            self._print_statistics()
            
        finally:
            # Clean up working directory
            self._cleanup_work_environment()
    
    def _update_branches(self, target_repo: Repo):
        """Update only the dev branch in target repository."""
        # Find the dev branch in source repo
        dev_branch = None
        for branch in self.source_repo.branches:
            if branch.name == 'dev':
                dev_branch = branch
                break
        
        if not dev_branch:
            self.logger.error("No 'dev' branch found in source repository")
            return
        
        # Find the last included commit on the dev branch
        # Start from HEAD and walk backwards until we find a non-filtered commit
        current_commit = dev_branch.commit
        last_valid_commit_sha = None
        
        # Walk through the commit history
        for commit in self.source_repo.iter_commits(dev_branch):
            if commit.hexsha in self.commit_map and self.commit_map[commit.hexsha]:
                # Found a commit that was included (not filtered)
                last_valid_commit_sha = self.commit_map[commit.hexsha]
                break
        
        if last_valid_commit_sha:
            # Log if we had to skip filtered commits at the tip
            if current_commit.hexsha != dev_branch.commit.hexsha or \
               (current_commit.hexsha in self.commit_map and not self.commit_map[current_commit.hexsha]):
                skipped_count = 0
                for commit in self.source_repo.iter_commits(dev_branch):
                    if commit.hexsha in self.commit_map and self.commit_map[commit.hexsha]:
                        break
                    skipped_count += 1
                self.logger.info(f"Skipped {skipped_count} filtered commit(s) at the tip of dev branch")
            
            # Create dev branch pointing to the last valid commit
            target_repo.create_head('dev', last_valid_commit_sha)
            self.logger.info(f"Created branch 'dev' pointing to {last_valid_commit_sha[:8]}")
            
            # Set dev as the active branch
            target_repo.head.reference = target_repo.heads['dev']
        else:
            self.logger.error("No valid commits found on dev branch")
    
    def _update_tags(self, target_repo: Repo):
        """Update tags in target repository for non-filtered commits."""
        for tag in self.source_repo.tags:
            source_commit_sha = tag.commit.hexsha
            
            # Skip tags on filtered commits - they will be handled by _propagate_tags
            if source_commit_sha in self.filtered_commit_tags:
                continue
            
            if source_commit_sha in self.commit_map:
                new_commit_sha = self.commit_map[source_commit_sha]
                
                if new_commit_sha:
                    try:
                        # Create tag pointing to new commit
                        if hasattr(tag, 'tag') and tag.tag:
                            # Annotated tag
                            target_repo.create_tag(
                                tag.name, 
                                ref=new_commit_sha,
                                message=tag.tag.message
                            )
                        else:
                            # Lightweight tag
                            target_repo.create_tag(tag.name, ref=new_commit_sha)
                        self.logger.info(f"Created tag {tag.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not create tag {tag.name}: {e}")
    
    def _replace_project_name(self, target_repo: Repo):
        """Replace all instances of the original project name with 'nutdealer'."""
        try:
            original_name = build_utils.get_project_name()
            self.logger.info(f"Replacing project name '{original_name}' with 'nutdealer'...")
            
            target_path = str(target_repo.working_dir)
            
            # Replace lowercase version
            subprocess.run([
                'find', target_path, '-type', 'f', 
                '-not', '-path', '*/\\.git/*',
                '-exec', 'sed', '-i', f's/{original_name}/nutdealer/g', '{}', '+'
            ], capture_output=True)
            
            # Replace capitalized version
            subprocess.run([
                'find', target_path, '-type', 'f',
                '-not', '-path', '*/\\.git/*', 
                '-exec', 'sed', '-i', f's/{original_name.capitalize()}/Nutdealer/g', '{}', '+'
            ], capture_output=True)
            
            # Rename files containing the project name
            find_result = subprocess.run([
                'find', target_path, '-name', f'*{original_name}*',
                '-not', '-path', '*/\\.git/*'
            ], capture_output=True, text=True)
            
            if find_result.returncode == 0 and find_result.stdout.strip():
                for old_path in find_result.stdout.strip().split('\n'):
                    if old_path:  # Skip empty lines
                        new_path = old_path.replace(original_name, 'nutdealer')
                        if old_path != new_path:
                            os.rename(old_path, new_path)
                            self.logger.debug(f"Renamed: {old_path} -> {new_path}")
            
            # Commit the changes
            target_repo.git.add('-A')
            if target_repo.index.diff('HEAD'):
                target_repo.index.commit(f"Replace project name with 'nutdealer'")
                self.logger.info("Committed project name replacement")
                
        except Exception as e:
            self.logger.error(f"Error replacing project name: {e}")
    
    def _print_statistics(self):
        """Print filtering statistics."""
        print("\n=== Filtering Statistics ===")
        print(f"Total commits processed: {self.stats['total_commits']}")
        print(f"Commits kept: {self.stats['kept_commits']}")
        print(f"Commits filtered out: {self.stats['filtered_commits']}")
        if self.stats['explicitly_filtered_commits'] > 0:
            print(f"  - Explicitly filtered commits: {self.stats['explicitly_filtered_commits']}")
        print(f"File operations performed: {self.stats['total_files']}")
        print(f"Files filtered out (cumulative): {self.stats['filtered_files']}")
        
        # Tag statistics
        if hasattr(self, 'filtered_commit_tags'):
            filtered_tags_count = sum(len(tags) for tags in self.filtered_commit_tags.values())
            if filtered_tags_count > 0:
                print(f"\n=== Tag Statistics ===")
                print(f"Tags on filtered commits: {filtered_tags_count}")
                print(f"Tags successfully propagated: {self.stats['propagated_tags']}")
                if filtered_tags_count > self.stats['propagated_tags']:
                    print(f"Tags not propagated: {filtered_tags_count - self.stats['propagated_tags']}")
                    print("  (Tags may not be propagated if no valid descendant commit was found)")
        
        # Overall filter rates
        if self.stats['total_commits'] > 0:
            filter_rate = (self.stats['filtered_commits'] / self.stats['total_commits']) * 100
            print(f"\nCommit filter rate: {filter_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Filter a Git repository based on gitignore patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python publicize_repo.py /path/to/source/repo /path/to/filtered/repo patterns.ignore

Ignore file format (same as .gitignore):
    # Comments start with #
    *.log           # Ignore all .log files
    secret/         # Ignore secret directory
    !important.log  # But keep important.log
    docs/**/*.pdf   # Ignore all PDFs in docs

Filter commits file:
    # One commit reference per line (prefixes, full SHAs, tags, branches, etc.)
    # Comments start with #
    abc123          # Filter commit with SHA starting with abc123
    HEAD~3          # Filter the commit 3 before HEAD
    v1.0^           # Filter the parent of the v1.0 tag

Tag Propagation:
    When a commit is filtered out (either because it contains only ignored files 
    or is explicitly filtered), any tags pointing to that commit will be
    propagated to the next valid descendant commit. This ensures that tags are
    not lost when filtering out commits.
    
    For annotated tags, the tag message will be preserved and a note will be
    added to indicate the original commit that was tagged.
        """
    )
    
    parser.add_argument('-source', help='Path to source repository', default=".")
    parser.add_argument('-target', help='Path where filtered repository will be created', default="publicize")
    parser.add_argument('-ignore_file', help='Path to gitignore-style file with patterns', default="tools/publicize_repo.gitignore")
    parser.add_argument('-f', '--filter-commits', help='Path to file containing commit references to filter out', default="tools/publicize_repo.blacklist")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not Path(args.source).exists():
        print(f"Error: Source repository not found: {args.source}")
        sys.exit(1)
    
    if not Path(args.ignore_file).exists():
        print(f"Error: Ignore file not found: {args.ignore_file}")
        sys.exit(1)
    
    if args.filter_commits and not Path(args.filter_commits).exists():
        print(f"Error: Filter commits file not found: {args.filter_commits}")
        sys.exit(1)
    
    # Check if git is available
    try:
        subprocess.run(['git', '--version'], check=True, capture_output=True)
    except:
        print("Error: git command not found. Please ensure git is installed.")
        sys.exit(1)
    
    # Run filter
    filter = GitRepoFilter(
        source_repo_path=args.source,
        target_repo_path=args.target,
        ignore_file_path=args.ignore_file,
        filter_commits_file=args.filter_commits,
        verbose=args.verbose
    )
    
    try:
        filter.filter_repository()
        print(f"\nFiltered repository created at: {args.target}")
    except Exception as e:
        print(f"Error during filtering: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()