"""
Module for translating subtitles using OpenRouter API.
"""
import os
import time
import requests
from typing import List, Optional
from subtitle_parser import SubtitleEntry


class OpenRouterTranslator:
    """Translate subtitles using OpenRouter API."""

    def __init__(
        self,
        api_key: str,
        model: str,
        source_language: str = "english",
        target_language: str = "polish"
    ):
        """
        Initialize OpenRouter translator.

        Args:
            api_key: OpenRouter API key
            model: Model to use (e.g., 'anthropic/claude-3.5-sonnet')
            source_language: Source language name
            target_language: Target language name
        """
        self.api_key = api_key
        self.model = model
        self.source_language = source_language
        self.target_language = target_language
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def translate_batch(
        self,
        entries: List[SubtitleEntry],
        batch_number: int,
        total_batches: int
    ) -> List[SubtitleEntry]:
        """
        Translate a batch of subtitle entries.

        Args:
            entries: List of subtitle entries to translate
            batch_number: Current batch number (for logging)
            total_batches: Total number of batches

        Returns:
            List of translated subtitle entries
        """
        if not entries:
            return []

        print(f"\nTranslating batch {batch_number}/{total_batches} "
              f"({len(entries)} entries)...")

        # Prepare the prompt
        prompt = self._create_translation_prompt(entries)

        # Call OpenRouter API
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._call_api(prompt)
                translated_text = response.strip()

                # Parse the response
                translated_entries = self._parse_translation_response(
                    translated_text,
                    entries
                )

                if len(translated_entries) != len(entries):
                    print(f"Warning: Response has {len(translated_entries)} entries "
                          f"but expected {len(entries)}. Retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        # Last attempt failed, return original
                        print("Translation failed after retries. Using original text.")
                        return entries

                print(f"✓ Batch {batch_number}/{total_batches} translated successfully")
                return translated_entries

            except Exception as e:
                print(f"Error translating batch {batch_number} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"Failed to translate batch {batch_number} after {max_retries} attempts")
                    return entries

        return entries

    def _create_translation_prompt(self, entries: List[SubtitleEntry]) -> str:
        """Create a translation prompt for a batch of subtitles."""
        # Format entries for translation
        formatted_entries = []
        for entry in entries:
            formatted_entries.append(f"{entry.index}|{entry.text}")

        entries_text = "\n".join(formatted_entries)

        prompt = f"""You are a professional subtitle translator. Translate the following subtitles from {self.source_language} to {self.target_language}.

CRITICAL INSTRUCTIONS:
1. Translate ONLY the text content, preserving the exact format
2. Each line has format: INDEX|TEXT
3. Maintain natural dialogue flow and timing
4. Keep the same number of lines in your response
5. Do not add explanations, notes, or extra text
6. Preserve the INDEX numbers exactly as they are
7. Keep translations concise to fit subtitle timing

Input subtitles:
{entries_text}

Return ONLY the translated subtitles in the exact same format (INDEX|TRANSLATED_TEXT), one per line, nothing else:"""

        return prompt

    def _call_api(self, prompt: str) -> str:
        """Call OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yourusername/mkv-translator",
            "X-Title": "MKV Subtitle Translator"
        }

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature for more consistent translations
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=data,
            timeout=120
        )

        if response.status_code != 200:
            raise Exception(
                f"API request failed with status {response.status_code}: "
                f"{response.text}"
            )

        result = response.json()

        if 'choices' not in result or len(result['choices']) == 0:
            raise Exception(f"Unexpected API response format: {result}")

        return result['choices'][0]['message']['content']

    def _parse_translation_response(
        self,
        response: str,
        original_entries: List[SubtitleEntry]
    ) -> List[SubtitleEntry]:
        """
        Parse the translation response and create new subtitle entries.

        Args:
            response: API response text
            original_entries: Original subtitle entries (for timestamps)

        Returns:
            List of translated subtitle entries
        """
        lines = response.strip().split('\n')
        translated_entries = []

        # Create a mapping of index to original entry
        index_to_entry = {entry.index: entry for entry in original_entries}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse format: INDEX|TEXT
            if '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2:
                    try:
                        index = int(parts[0].strip())
                        translated_text = parts[1].strip()

                        # Get original entry for timestamps
                        if index in index_to_entry:
                            original = index_to_entry[index]

                            # Create new entry with translated text
                            translated_entry = SubtitleEntry(
                                index=original.index,
                                start_time=original.start_time,
                                end_time=original.end_time,
                                text=translated_text,
                                start_ms=original.start_ms,
                                end_ms=original.end_ms
                            )
                            translated_entries.append(translated_entry)
                    except ValueError:
                        continue

        return translated_entries

    def translate_all(
        self,
        entries: List[SubtitleEntry],
        batches: List[List[SubtitleEntry]],
        delay_between_batches: float = 1.0
    ) -> List[SubtitleEntry]:
        """
        Translate all subtitle entries in batches.

        Args:
            entries: All subtitle entries (for reference)
            batches: List of batches to translate
            delay_between_batches: Delay in seconds between API calls

        Returns:
            List of all translated entries
        """
        all_translated = []
        total_batches = len(batches)

        print(f"\nStarting translation of {len(entries)} entries in {total_batches} batches...")
        print(f"Model: {self.model}")
        print(f"Translation: {self.source_language} → {self.target_language}")

        for i, batch in enumerate(batches, 1):
            translated_batch = self.translate_batch(batch, i, total_batches)
            all_translated.extend(translated_batch)

            # Delay between batches to avoid rate limiting
            if i < total_batches:
                time.sleep(delay_between_batches)

        print(f"\n✓ Translation complete! Translated {len(all_translated)} entries.")
        return all_translated
