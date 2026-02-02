"""
Metadata Injector Module - YAML Frontmatter Intelligence
Purpose: Make Markdown notes queryable and future-proof for Obsidian Dataview
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import yaml


class MetadataInjector:
    """
    Injects structured YAML frontmatter into markdown files.

    Key Features:
    - Searchable by Dataview plugin
    - Filterable by date, source, tags
    - Future-proof for advanced Obsidian workflows
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    # ==========================
    # Public API
    # ==========================

    def inject_metadata(self, filepath: Path) -> bool:
        """
        Inject YAML frontmatter into a markdown file
        """
        try:
            content = filepath.read_text(encoding='utf-8')

            # Skip if frontmatter already exists
            if content.startswith('---'):
                self.logger.debug(f"Frontmatter already exists: {filepath.name}")
                return True

            metadata = self._extract_metadata(content, filepath)
            frontmatter = self._generate_frontmatter(metadata)

            new_content = f"{frontmatter}\n{content}"
            filepath.write_text(new_content, encoding='utf-8')

            self.logger.debug(f"Injected metadata: {filepath.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to inject metadata into {filepath}: {e}")
            return False

    def update_metadata(self, filepath: Path, updates: Dict) -> bool:
        """
        Update existing frontmatter
        """
        try:
            content = filepath.read_text(encoding='utf-8')

            if not content.startswith('---'):
                self.logger.warning(f"No frontmatter to update: {filepath}")
                return False

            parts = content.split('---', 2)
            if len(parts) < 3:
                return False

            yaml_content = parts[1]
            body = parts[2]

            metadata = yaml.safe_load(yaml_content) or {}
            metadata.update(updates)

            new_frontmatter = self._generate_frontmatter(metadata)
            new_content = f"{new_frontmatter}\n{body.lstrip()}"

            filepath.write_text(new_content, encoding='utf-8')
            return True

        except Exception as e:
            self.logger.error(f"Failed to update metadata: {e}")
            return False

    # ==========================
    # Metadata Extraction
    # ==========================

    def _extract_metadata(self, content: str, filepath: Path) -> Dict:
        metadata = {}
        metadata['title'] = self._extract_title(content, filepath)
        metadata['created'] = self._extract_creation_date(content, filepath)
        metadata['modified'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        metadata['tags'] = self._extract_tags(content)
        metadata['source'] = self._identify_source(filepath, content)
        metadata['migration_status'] = 'completed'
        metadata['migrated_at'] = datetime.now().strftime('%Y-%m-%d')
        metadata['type'] = self._classify_note_type(content)
        return metadata

    def _extract_title(self, content: str, filepath: Path) -> str:
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'[*_`]', '', title)
            return title
        return filepath.stem.replace('_', ' ').replace('-', ' ').title()

    def _extract_creation_date(self, content: str, filepath: Path) -> str:
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\w+ \d{1,2},? \d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, content[:500])
            if match:
                date_str = match.group(1)
                if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                    return date_str
        try:
            stat = filepath.stat()
            created = datetime.fromtimestamp(stat.st_ctime)
            return created.strftime('%Y-%m-%d')
        except (FileNotFoundError, OSError) as e:
            self.logger.error(f"Error reading file: {e}")
            return datetime.now().strftime('%Y-%m-%d')

    def _extract_tags(self, content: str) -> List[str]:
        tags = set(re.findall(r'(?<!^)(?<!#)#(\w+)', content, re.MULTILINE))
        topic_keywords = {
            'python': 'programming/python',
            'javascript': 'programming/javascript',
            'tutorial': 'learning/tutorial',
            'documentation': 'reference/docs',
            'api': 'reference/api',
            'guide': 'learning/guide',
        }
        content_lower = content.lower()
        for keyword, tag in topic_keywords.items():
            if keyword in content_lower:
                tags.add(tag)
        tags.add('migrated')
        return sorted(list(tags))

    def _identify_source(self, filepath: Path, content: str) -> str:
        if 'evernote' in content.lower():
            return 'evernote'
        url_match = re.search(r'https?://[\w\.-]+', content[:1000])
        if url_match:
            return f"web/{url_match.group(0)}"
        if 'export' in filepath.name.lower():
            return 'evernote_export'
        return 'unknown'

    def _classify_note_type(self, content: str) -> str:
        code_blocks = len(re.findall(r'```', content))
        tables = len(re.findall(r'\|.*\|', content))
        word_count = len(content.split())
        if code_blocks >= 2:
            return 'snippet'
        elif tables >= 2:
            return 'documentation'
        elif word_count > 500:
            return 'article'
        else:
            return 'note'

    # ==========================
    # Frontmatter Generation
    # ==========================

    def _generate_frontmatter(self, metadata: Dict) -> str:
        fm = {
            'title': metadata.get('title', 'Untitled'),
            'created': metadata.get('created'),
            'modified': metadata.get('modified'),
            'tags': metadata.get('tags', []),
            'source': metadata.get('source', 'unknown'),
            'type': metadata.get('type', 'note'),
            'migration_status': metadata.get('migration_status', 'completed'),
            'migrated_at': metadata.get('migrated_at'),
        }
        yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return f"---\n{yaml_str}---"
