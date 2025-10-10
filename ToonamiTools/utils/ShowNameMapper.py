"""
ShowNameMapper - Centralized show name normalization and mapping utility.

This module consolidates all show name mapping logic that was previously
duplicated across multiple ToonamiTools modules.
"""
import re
from typing import Dict, List, Set
from unidecode import unidecode
from config import show_name_mapping, show_name_mapping_2, show_name_mapping_3


class ShowNameMapper:
    """Handles all show name normalization and mapping operations."""
    
    def __init__(self):
        """Initialize with show name mappings from config."""
        self.mapping_1 = show_name_mapping
        self.mapping_2 = show_name_mapping_2
        self.mapping_3 = show_name_mapping_3
        
        # Pre-compile regex patterns for efficiency
        self._non_alnum_pattern = re.compile(r'[^a-zA-Z0-9\s]')
        self._whitespace_pattern = re.compile(r'\s+')
        self._underscore_pattern = re.compile(r'_+')
        
        # Pre-compute combined lowercase mappings (preserve original case of values)
        self._combined_lower = {}
        for mapping in [self.mapping_1, self.mapping_2, self.mapping_3]:
            for k, v in mapping.items():
                self._combined_lower[k.lower()] = v  # Keep original case of mapped value
    
    # ========== CORE METHODS ==========
    
    def clean(self, text: str, mode: str = 'standard') -> str:
        """
        Clean text according to specified mode.
        
        Args:
            text: Text to clean
            mode: Cleaning mode:
                  - 'standard': Basic normalization (unidecode, lowercase, remove special chars)
                  - 'matching': For comparison (remove all non-alphanumeric, lowercase)
                  - 'display': For display (proper capitalization)
        
        Returns:
            Cleaned text
        """
        if mode == 'standard':
            # Basic normalization (for toonamichecker)
            normalized = unidecode(text.lower())
            normalized = re.sub(r'[^\w\s]', ' ', normalized)
            normalized = re.sub(r'_', ' ', normalized)
            normalized = self._whitespace_pattern.sub(' ', normalized).strip()
            return normalized
            
        elif mode == 'matching':
            # For comparison key used across DB joins and equality checks
            # 1) Normalize unicode to ASCII (e.g., Pokémon -> Pokemon)
            normalized = unidecode(text)
            # 2) Treat common equivalences before stripping
            #    - Ampersand should behave like the word 'and' so that
            #      'Law & Order' matches 'Law and Order'
            normalized = normalized.replace('&', ' and ')
            # 3) Remove all non-alphanumeric except whitespace
            cleaned = self._non_alnum_pattern.sub('', normalized)
            # 4) Collapse whitespace and lowercase
            cleaned = self._whitespace_pattern.sub(' ', cleaned).strip().lower()
            return cleaned
            
        elif mode == 'display':
            # For display (proper capitalization)
            # Keep basic punctuation like ampersands and apostrophes for display
            # but normalize whitespace
            words = text.split()
            small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 
                          'if', 'in', 'nor', 'of', 'on', 'or', 'so', 'the', 
                          'to', 'up', 'yet'}
            
            result = []
            for i, word in enumerate(words):
                if i == 0 or word.lower() not in small_words:
                    result.append(word.capitalize())
                else:
                    result.append(word.lower())
            
            return ' '.join(result)
        
        else:
            raise ValueError(f"Unknown cleaning mode: {mode}")
    
    def map(self, show_name: str, strategy: str = 'all', case_sensitive: bool = False) -> str:
        """
        Apply show name mappings according to strategy.
        ALWAYS returns lowercase for consistency with LineupPrep processing.
        
        Args:
            show_name: Show name to map
            strategy: Mapping strategy:
                     - 'all': Apply all three mappings sequentially
                     - 'first': Only use first mapping dictionary
                     - 'first_match': Stop at first match found (PlexToDizqueTV style)
            case_sensitive: Whether to use case-sensitive matching (ignored - always case-insensitive)
            
        Returns:
            Mapped show name in lowercase
        """
        # Always work with lowercase for consistency
        result = show_name.lower()
        
        if strategy == 'all':
            # Apply mappings sequentially
            for mapping in [self.mapping_1, self.mapping_2, self.mapping_3]:
                for key, value in mapping.items():
                    if key.lower() == result:
                        result = value.lower()
                        break
            return result
                
        elif strategy == 'first':
            # Only use first mapping
            for key, value in self.mapping_1.items():
                if key.lower() == result:
                    return value.lower()
            return result
                
        elif strategy == 'first_match':
            # Check each mapping until match found
            for mapping in [self.mapping_1, self.mapping_2, self.mapping_3]:
                for key, value in mapping.items():
                    if key.lower() == result:
                        return value.lower()
            return result
                
        else:
            raise ValueError(f"Unknown mapping strategy: {strategy}")
    
    def to_block_id(self, show_name: str) -> str:
        """
        Convert show name to BLOCK_ID format.
        
        Args:
            show_name: Show name to convert
            
        Returns:
            BLOCK_ID formatted string (uppercase with underscores)
        """
        # Apply mapping first
        mapped = self.map(show_name, strategy='all')
        
        # Convert to BLOCK_ID format
        block_id = mapped.upper().replace(' ', '_')
        block_id = re.sub(r'[^A-Z0-9_]', '', block_id)
        block_id = self._underscore_pattern.sub('_', block_id)
        
        return block_id

    
    
    # ========== SPECIALIZED METHODS ==========
    
    def apply_to_filename(self, filename: str) -> str:
        """
        Apply show name mappings to filenames with word boundary matching.
        
        Args:
            filename: Filename to process
            
        Returns:
            Filename with show names mapped
        """
        result = filename
        
        # Sort by length (longest first) to handle overlapping names
        all_mappings = []
        for mapping in [self.mapping_1, self.mapping_2, self.mapping_3]:
            all_mappings.extend(mapping.items())
        
        sorted_mappings = sorted(all_mappings, key=lambda x: len(x[0]), reverse=True)
        
        for old_name, new_name in sorted_mappings:
            # Use word boundaries to ensure we only match complete words
            pattern = r'\b' + re.escape(old_name) + r'\b'
            result = re.sub(pattern, new_name, result, flags=re.IGNORECASE)
        
        return result
    
    def apply_via_replacement(self, text: str) -> str:
        """
        Apply mappings using string replacement (lineupprep style).
        Used for bump text processing.
        
        Args:
            text: Text to process
            
        Returns:
            Text with mappings applied (lowercase, cleaned for matching)
        """
        result = text.lower()
        
        # Apply all mappings via replacement
        for mapping in [self.mapping_1, self.mapping_2, self.mapping_3]:
            sorted_keys = sorted(mapping.keys(), key=len, reverse=True)
            for key in sorted_keys:
                value = mapping[key]
                # Replace case-insensitively
                pattern = re.compile(re.escape(key), re.IGNORECASE)
                result = pattern.sub(value.lower(), result)
        
        # Clean for matching after replacement - remove ALL special characters
        return self.clean(result, mode='matching')
    
    def get_block_id_prefixes(self, show_name: str) -> Set[str]:
        """
        Generate all possible BLOCK_ID prefixes for a show (merger.py style).
        
        Args:
            show_name: The show name to generate prefixes for
            
        Returns:
            Set of all possible BLOCK_ID prefixes
        """
        prefixes = set()
        
        # First, add the show itself (normalized with first mapping only)
        normalized_show = self.map(show_name, strategy='first', case_sensitive=False)
        block_format = self._non_alnum_pattern.sub('_', normalized_show).upper()
        prefixes.add(block_format)
        
        # Also try the original show name (before normalization)
        original_format = self._non_alnum_pattern.sub('_', show_name).upper()
        if original_format != block_format:
            prefixes.add(original_format)
        
        # Find all keys in mapping_1 that normalize to this show
        for mapping_key, mapping_value in self.mapping_1.items():
            if mapping_value == normalized_show and mapping_key != normalized_show:
                # This key maps to our normalized show
                key_format = self._non_alnum_pattern.sub('_', mapping_key).upper()
                prefixes.add(key_format)
        
        return prefixes
    
    # ========== CONVENIENCE METHODS ==========
    
    def normalize_and_map(self, show_name: str) -> str:
        """
        Normalize and map show name (toonamichecker style).
        
        Args:
            show_name: Show name to process
            
        Returns:
            Normalized and mapped show name
        """
        # First normalize
        normalized = self.clean(show_name, mode='standard')
        
        # Then map
        return self.map(normalized, strategy='all', case_sensitive=False)
    
    def get_all_variants(self, show_name: str) -> Set[str]:
        """
        Get all possible variants of a show name.
        Useful for fuzzy matching and search operations.
        
        Args:
            show_name: Base show name
            
        Returns:
            Set of all variants (original, normalized, mapped, reverse mapped)
        """
        variants = {show_name}
        show_lower = show_name.lower()
        
        # Add cleaned versions
        variants.add(self.clean(show_name, mode='standard'))
        variants.add(self.clean(show_name, mode='matching'))
        
        # Add mapped versions
        for strategy in ['all', 'first', 'first_match']:
            mapped = self.map(show_name, strategy=strategy)
            variants.add(mapped)
            variants.add(mapped.lower())
        
        # Find reverse mappings (all keys that map to this show)
        for mapping in [self.mapping_1, self.mapping_2, self.mapping_3]:
            for key, value in mapping.items():
                if value.lower() == show_lower:
                    variants.add(key)
                    variants.add(value)
        
        return variants


# Create a global instance for easy importing
show_name_mapper = ShowNameMapper()
