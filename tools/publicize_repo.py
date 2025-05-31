#!/usr/bin/env python3
"""
Git Repository Filter - Remove sensitive data from Git history based on gitignore patterns
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple
from collections import defaultdict
import subprocess
import tempfile
import shutil
import util

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
        
        # Statistics
        self.stats = {
            'total_commits': 0,
            'filtered_commits': 0,
            'kept_commits': 0,
            'total_files': 0,
            'filtered_files': 0,
            'explicitly_filtered_commits': 0
        }
        
        # Persistent working directory
        self.work_dir = None
        
        # File cache to track what files we've already processed
        self.file_cache = {}
    
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
    
    def _get_changed_files(self, commit: git.Commit) -> List[str]:
        """Get files that changed in this commit."""
        changed_files = set()
        
        # Get list of changed files in this commit
        if not commit.parents:
            # For initial commit, all files are "changed"
            for item in commit.tree.traverse():
                if item.type == 'blob':
                    changed_files.add(item.path)
        else:
            # For other commits, get the diff
            for parent in commit.parents:
                # Get diff from parent to commit (what changed in this commit)
                diffs = commit.diff(parent)
                for diff in diffs:
                    # Get the file path (b_path for additions/modifications, a_path for deletions)
                    if diff.b_path:
                        changed_files.add(diff.b_path)
                    if diff.a_path and diff.b_path != diff.a_path:  # renamed file
                        changed_files.add(diff.a_path)
        
        return list(changed_files)
    
    def _get_filtered_changes(self, commit: git.Commit) -> Dict[str, git.Blob]:
        """
        Get only the changed files from a commit that should be kept (not ignored).
        
        Returns:
            Dict mapping file paths to blob objects for non-ignored files that changed
        """
        changed_files = self._get_changed_files(commit)
        self.stats['total_files'] += len(changed_files)
        
        self.logger.debug(f"Commit {commit.hexsha[:8]} has {len(changed_files)} changed files")
        
        # Track changed files that should be kept
        kept_changes = {}
        for path in changed_files:
            # Skip if path should be ignored
            if self._should_ignore(path):
                self.stats['filtered_files'] += 1
                self.logger.debug(f"Ignoring changed file: {path}")
                continue
            
            try:
                # Get the blob for this file in this commit
                blob = commit.tree[path]
                kept_changes[path] = blob
            except (KeyError, ValueError):
                # File was deleted in this commit
                kept_changes[path] = None
        
        if not kept_changes:
            self.logger.debug(f"Commit {commit.hexsha[:8]} has no non-ignored changes")
        
        return kept_changes
    
    def _setup_work_environment(self, target_repo: Repo):
        """Set up a persistent working directory and index for all commits."""
        # Create a temporary directory for the working directory
        self.work_dir = tempfile.mkdtemp(prefix="git_filter_")
        self.logger.debug(f"Created persistent working directory: {self.work_dir}")
        
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
    
    def _update_working_directory(self, kept_changes: Dict[str, git.Blob], target_repo: Repo):
        """
        Update the working directory with changed files.
        Only copies files that have actually changed.
        """
        # Process all kept changes
        for path, blob in kept_changes.items():
            full_path = Path(self.work_dir) / path
            
            if blob is None:
                # File was deleted
                if full_path.exists():
                    full_path.unlink()
                    subprocess.run(
                        ['git', '--git-dir', str(target_repo.git_dir), 'rm', '--cached', path],
                        cwd=self.work_dir,
                        env=self.git_env,
                        check=False,  # Don't fail if file wasn't in index
                        capture_output=True
                    )
                continue
                
            # Check if we need to update this file
            blob_id = blob.hexsha
            cache_key = f"{path}:{blob_id}"
            
            # Skip if file hasn't changed (same content already in working dir)
            if cache_key in self.file_cache:
                continue
            
            # Get blob content
            blob_data = self.source_repo.odb.stream(blob.binsha).read()
            
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            with open(full_path, 'wb') as f:
                f.write(blob_data)
            
            # Add to cache
            self.file_cache[cache_key] = True
    
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
            return None
        
        # Get non-ignored files that changed in this commit
        kept_changes = self._get_filtered_changes(source_commit)
        
        # Skip commit if no files are kept
        if not kept_changes:
            self.logger.debug(f"Skipping commit {source_commit.hexsha[:8]} - no kept files or no kept changes")
            self.stats['filtered_commits'] += 1
            return None
        
        self.logger.debug(f"Processing commit {source_commit.hexsha[:8]} with {len(kept_changes)} changed files")
        
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
        
        # Update working directory with changed files
        self._update_working_directory(kept_changes, target_repo)
        
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
            # Get all commits in topological order (parents before children)
            commits = list(self.source_repo.iter_commits('--all', topo_order=True))
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
            
            # Update tags
            self._update_tags(target_repo)
            
            # Print statistics
            self._print_statistics()
            
        finally:
            # Clean up working directory
            self._cleanup_work_environment()
    
    def _update_branches(self, target_repo: Repo):
        """Update branches in target repository."""
        for branch in self.source_repo.branches:
            source_commit_sha = branch.commit.hexsha
            
            if source_commit_sha in self.commit_map:
                new_commit_sha = self.commit_map[source_commit_sha]
                
                if new_commit_sha:
                    # Create branch pointing to new commit
                    target_repo.create_head(branch.name, new_commit_sha)
                    self.logger.info(f"Created branch {branch.name}")
                    
                    # Set as active branch if it's the current branch in source
                    if self.source_repo.active_branch.name == branch.name:
                        target_repo.head.reference = target_repo.heads[branch.name]
    
    def _update_tags(self, target_repo: Repo):
        """Update tags in target repository."""
        for tag in self.source_repo.tags:
            source_commit_sha = tag.commit.hexsha
            
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
    
    def _print_statistics(self):
        """Print filtering statistics."""
        print("\n=== Filtering Statistics ===")
        print(f"Total commits processed: {self.stats['total_commits']}")
        print(f"Commits kept: {self.stats['kept_commits']}")
        print(f"Commits filtered out: {self.stats['filtered_commits']}")
        if self.stats['explicitly_filtered_commits'] > 0:
            print(f"  - Explicitly filtered commits: {self.stats['explicitly_filtered_commits']}")
        print(f"Files examined: {self.stats['total_files']}")
        print(f"Files filtered out: {self.stats['filtered_files']}")
        
        if self.stats['total_commits'] > 0:
            filter_rate = (self.stats['filtered_commits'] / self.stats['total_commits']) * 100
            print(f"Commit filter rate: {filter_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Filter a Git repository based on gitignore-style patterns",
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
        """
    )
    
    parser.add_argument('source', help='Path to source repository')
    parser.add_argument('target', help='Path where filtered repository will be created')
    parser.add_argument('ignore_file', help='Path to gitignore-style file with patterns')
    parser.add_argument('-f', '--filter-commits', 
                      help='Path to file containing commit references to filter out')
    parser.add_argument('-v', '--verbose', action='store_true', 
                      help='Enable verbose output')
    
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