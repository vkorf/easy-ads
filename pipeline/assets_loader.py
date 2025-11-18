"""Assets Loader - Load and process text and image assets from local storage"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AssetsLoaderError(Exception):
    """Custom exception for assets loader errors"""
    pass


class AssetsLoader:
    """Load text assets from local folder to enrich prompts"""

    # Supported text file extensions
    TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.text'}

    def __init__(self, assets_dir: str = "assets"):
        """
        Initialize assets loader

        Args:
            assets_dir: Path to assets directory (default: "assets")
        """
        self.assets_dir = Path(assets_dir)
        self.assets_cache: Dict[str, str] = {}

        if not self.assets_dir.exists():
            logger.warning(f"Assets directory does not exist: {assets_dir}")
        else:
            logger.info(f"Initialized assets loader with directory: {assets_dir}")

    def load_all_text_assets(self) -> Dict[str, str]:
        """
        Load all text files from assets directory

        Returns:
            Dictionary mapping filename to content

        Raises:
            AssetsLoaderError: If loading fails
        """
        if not self.assets_dir.exists():
            logger.warning(f"Assets directory not found: {self.assets_dir}")
            return {}

        assets = {}
        text_files = self._find_text_files()

        if not text_files:
            logger.info("No text assets found in assets directory")
            return {}

        logger.info(f"Found {len(text_files)} text asset(s)")

        for file_path in text_files:
            try:
                content = self._read_text_file(file_path)
                if content and content.strip():
                    assets[file_path.name] = content
                    logger.info(f"  ✓ Loaded: {file_path.name} ({len(content)} chars)")
                else:
                    logger.warning(f"  ⚠ Skipped empty file: {file_path.name}")
            except Exception as e:
                logger.warning(f"  ✗ Failed to load {file_path.name}: {str(e)}")

        self.assets_cache = assets
        return assets

    def _find_text_files(self) -> List[Path]:
        """
        Find all text files in assets directory

        Returns:
            List of text file paths
        """
        text_files = []

        # Recursively find all text files
        for ext in self.TEXT_EXTENSIONS:
            text_files.extend(self.assets_dir.rglob(f"*{ext}"))

        return sorted(text_files)

    def _read_text_file(self, file_path: Path) -> str:
        """
        Read text file with encoding fallback

        Args:
            file_path: Path to text file

        Returns:
            File content as string

        Raises:
            AssetsLoaderError: If reading fails
        """
        # Try UTF-8 first, then fall back to latin-1
        encodings = ['utf-8', 'latin-1']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise AssetsLoaderError(f"Failed to read {file_path}: {str(e)}")

        raise AssetsLoaderError(f"Could not decode {file_path} with any supported encoding")

    def format_assets_for_prompt(self, assets: Optional[Dict[str, str]] = None) -> str:
        """
        Format loaded assets into a string suitable for prompt enrichment

        Args:
            assets: Optional dict of assets (uses cache if not provided)

        Returns:
            Formatted string with all asset contents
        """
        if assets is None:
            assets = self.assets_cache

        if not assets:
            return ""

        # Build formatted output
        sections = []

        for filename, content in assets.items():
            sections.append(f"From {filename}:\n{content.strip()}")

        return "\n\n".join(sections)

    def get_assets_summary(self, assets: Optional[Dict[str, str]] = None) -> str:
        """
        Get a summary of loaded assets for logging

        Args:
            assets: Optional dict of assets (uses cache if not provided)

        Returns:
            Summary string
        """
        if assets is None:
            assets = self.assets_cache

        if not assets:
            return "No assets loaded"

        summary_lines = [f"Loaded {len(assets)} asset(s):"]
        for filename, content in assets.items():
            word_count = len(content.split())
            summary_lines.append(f"  - {filename}: {word_count} words")

        return "\n".join(summary_lines)

 