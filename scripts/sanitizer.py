"""
Sanitizer Module - Content Cleaning and Normalization
Purpose: Prepare Markdown for Obsidian
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import List, Tuple


class ContentSanitizer:
    """
    Cleans and normalizes Markdown content:
    - Removes HTML artifacts
    - Fixes broken links
    - Normalizes whitespace
    - Ensures Obsidian compatibility
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # Regex patterns for cleaning
        self.patterns = {
            'html_comments': re.compile(r'<!--.*?-->', re.DOTALL),
            'empty_tags': re.compile(r'<(\w+)[^>]*>\s*</\1>'),
            'style_attrs': re.compile(r'\s+style="[^"]*"'),
            'class_attrs': re.compile(r'\s+class="[^"]*"'),
            'multi_blanks': re.compile(r'\n{3,}'),
            'trailing_space': re.compile(r'[ \t]+$', re.MULTILINE),
            'broken_wikilinks': re.compile(r'\[\[([^\]]+)\]\]'),
            'zero_width': re.compile(r'[\u200b\u200c\u200d\ufeff]'),
        }

    # ==========================
    # Public API
    # ==========================

    def sanitize_file(self, filepath: Path) -> bool:
        """
        Sanitize a markdown file in-place

        Args:
            filepath: Path to markdown file

        Returns:
            True if successful, False otherwise
        """
        try:
            content = filepath.read_text(encoding='utf-8')
            cleaned = self._clean_pipeline(content)

            if cleaned != content:
                filepath.write_text(cleaned, encoding='utf-8')
                self.logger.debug(f"Sanitized: {filepath.name}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to sanitize {filepath}: {e}")
            return False

    def sanitize_batch(self, files: List[Path]) -> int:
        """
        Sanitize multiple files

        Returns:
            Number of successfully sanitized files
        """
        count = 0
        for f in files:
            if self.sanitize_file(f):
                count += 1
        return count

    # ==========================
    # Cleaning Pipeline
    # ==========================

    def _clean_pipeline(self, content: str) -> str:
        content = self._remove_html_artifacts(content)
        content = self._fix_links(content)
        content = self._normalize_whitespace(content)
        content = self._fix_tables(content)
        content = self._fix_code_blocks(content)
        content = self.patterns['zero_width'].sub('', content)
        return content

    # ==========================
    # Cleaning Steps
    # ==========================

    def _remove_html_artifacts(self, content: str) -> str:
        content = self.patterns['html_comments'].sub('', content)
        content = self.patterns['empty_tags'].sub('', content)
        content = self.patterns['style_attrs'].sub('', content)
        content = self.patterns['class_attrs'].sub('', content)

        for tag in ['div', 'span', 'font', 'center']:
            content = re.sub(f'<{tag}[^>]*>', '', content)
            content = re.sub(f'</{tag}>', '', content)

        return content

    def _fix_links(self, content: str) -> str:
        # Fix broken wikilinks
        def fix_wikilink(match):
            link_text = match.group(1).strip()
            link_text = re.sub(r'<[^>]+>', '', link_text)
            return f"[[{link_text}]]"

        content = self.patterns['broken_wikilinks'].sub(fix_wikilink, content)
        # Fix empty markdown links
        content = re.sub(r'\[([^\]]+)\]\(\s*\)', r'\1', content)
        # Fix broken images
        content = re.sub(r'!\[\]\(([^)]+)\)', r'![\1](\1)', content)
        return content

    def _normalize_whitespace(self, content: str) -> str:
        content = self.patterns['trailing_space'].sub('', content)
        content = self.patterns['multi_blanks'].sub('\n\n', content)
        content = content.rstrip() + '\n'
        content = re.sub(r'\n(#{1,6}\s+.+)\n{3,}', r'\n\n\1\n\n', content)
        return content

    def _fix_tables(self, content: str) -> str:
        lines = content.split('\n')
        fixed_lines = []
        in_table = False

        for line in lines:
            if '|' in line and not line.strip().startswith('```'):
                in_table = True
                line = re.sub(r'\s*\|\s*', ' | ', line)
                if re.match(r'^[\s\|\-:]+$', line):
                    line = re.sub(r'-+', '---', line)
            else:
                if in_table and line.strip():
                    fixed_lines.append('')
                in_table = False
            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _fix_code_blocks(self, content: str) -> str:
        content = re.sub(r'```\s*\n', '```\n', content)
        content = re.sub(r'([^\n])\n```', r'\1\n\n```', content)
        content = re.sub(r'```\n([^\n])', r'```\n\n\1', content)
        return content

    # ==========================
    # Validation
    # ==========================

    def validate_markdown(self, content: str) -> Tuple[bool, List[str]]:
        issues: List[str] = []
        code_blocks = re.findall(r'```', content)
        if len(code_blocks) % 2 != 0:
            issues.append("Unclosed code block detected")
        if re.search(r'\]\([^\)]*$', content, re.MULTILINE):
            issues.append("Malformed markdown link detected")
        if re.search(r'!\[\]!\[', content):
            issues.append("Malformed image syntax detected")
        remaining_html = re.findall(r'<(div|span|font|center)[^>]*>', content)
        if remaining_html:
            issues.append(f"Remaining HTML tags: {set(remaining_html)}")
        return len(issues) == 0, issues
