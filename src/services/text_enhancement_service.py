"""
Text Enhancement Service

Provides post-processing for transcribed text including:
- Smart capitalization (avoids over-capitalizing short commands)
- Punctuation fixes
- Optional local LLM enhancement for longer text

Design philosophy:
- Rule-based for speed (instant)
- Optional LLM for quality (1-2s overhead)
- User-configurable thresholds
"""

import re
from typing import Optional
from ..config import CONFIG


class TextEnhancementService:
    """Enhances transcribed text with smart capitalization and punctuation."""

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize text enhancement service.

        Args:
            config: Optional configuration dict
        """
        self.config = config or CONFIG.get('text_enhancement_settings', {})

        # Enhancement engine: "ollama", "rules", or "disabled"
        self.engine = self.config.get('engine', 'ollama')
        self.ollama_model = self.config.get('ollama_model', 'llama3.2:1b')
        self.ollama_url = self.config.get('ollama_url', 'http://localhost:11434')
        self.max_latency_ms = self.config.get('max_latency_ms', 100)

        # Thresholds for different processing strategies
        self.min_words_for_enhancement = self.config.get('min_words_for_enhancement', 3)

        # Words that should always be lowercase (unless at start)
        self.lowercase_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
                                'on', 'at', 'to', 'from', 'by', 'in', 'of', 'with'}

        # Common sentence starters that should be capitalized
        self.sentence_starters = {'i', 'you', 'he', 'she', 'it', 'we', 'they',
                                   'what', 'when', 'where', 'why', 'how', 'who',
                                   'open', 'close', 'start', 'stop', 'create', 'delete'}

        # Preload model at startup if using Ollama
        self._ollama_ready = False
        if self.engine == 'ollama':
            self._warmup_ollama()

    def _warmup_ollama(self):
        """Preload Ollama model to ensure fast inference."""
        try:
            import requests
            # Send a tiny warmup request to load model into memory
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": "hi",
                    "stream": False
                },
                timeout=5
            )
            if response.status_code == 200:
                self._ollama_ready = True
                print(f"[TextEnhancement] Ollama model {self.ollama_model} warmed up")
            else:
                print(f"[TextEnhancement] Ollama warmup failed: {response.status_code}")
        except Exception as e:
            print(f"[TextEnhancement] Ollama not available: {e}")
            print("[TextEnhancement] Falling back to rule-based enhancement")

    def enhance(self, text: str) -> str:
        """
        Main enhancement entry point.

        Args:
            text: Raw transcribed text

        Returns:
            Enhanced text with smart capitalization and punctuation
        """
        if not text or not text.strip():
            return text

        text = text.strip()
        word_count = len(text.split())

        # Very short text - minimal processing
        if word_count < self.min_words_for_enhancement:
            return self._process_short_text(text)

        # Route to appropriate engine
        if self.engine == 'ollama' and self._ollama_ready:
            return self._enhance_with_ollama(text)
        elif self.engine == 'rules' or not self._ollama_ready:
            return self._process_with_rules(text)
        else:
            return text  # No enhancement

    def _enhance_with_ollama(self, text: str) -> str:
        """
        Enhance text using Ollama local LLM.

        Args:
            text: Raw transcribed text

        Returns:
            Enhanced text with proper punctuation/capitalization
        """
        import time
        import requests

        start_time = time.time()

        # Minimal prompt for speed
        prompt = f"""Fix punctuation and capitalization. Output ONLY the corrected text, no explanations.

Input: {text}
Output:"""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temp for consistency
                        "num_predict": 100,  # Limit output length
                    }
                },
                timeout=self.max_latency_ms / 1000.0  # Convert to seconds
            )

            if response.status_code == 200:
                result = response.json()
                enhanced = result.get('response', '').strip()

                latency_ms = (time.time() - start_time) * 1000
                print(f"[TextEnhancement] Ollama latency: {latency_ms:.0f}ms")

                # Basic validation - if result is garbage, fall back
                if enhanced and len(enhanced) > len(text) * 0.5:
                    return enhanced

        except requests.Timeout:
            print(f"[TextEnhancement] Ollama timeout (>{self.max_latency_ms}ms), falling back to rules")
        except Exception as e:
            print(f"[TextEnhancement] Ollama error: {e}")

        # Fallback to rules
        return self._process_with_rules(text)

    def _process_short_text(self, text: str) -> str:
        """
        Process very short text (1-2 words).

        Rules:
        - Single words: lowercase unless proper noun
        - Two words: capitalize if it's a sentence starter

        Args:
            text: Short text

        Returns:
            Processed text
        """
        words = text.split()

        if len(words) == 1:
            # Single word - keep lowercase unless it's a proper noun or sentence starter
            word = words[0].lower()
            if word in self.sentence_starters or self._is_proper_noun(word):
                return word.capitalize()
            return word

        # Two words - capitalize first if sentence starter
        first_word = words[0].lower()
        if first_word in self.sentence_starters:
            words[0] = first_word.capitalize()

        return ' '.join(words)

    def _process_with_rules(self, text: str) -> str:
        """
        Process text using rule-based capitalization.

        Rules:
        1. Capitalize first word
        2. Capitalize after periods, question marks, exclamation marks
        3. Capitalize proper nouns (heuristic: already capitalized in input)
        4. Keep common words lowercase
        5. Add period at end if missing

        Args:
            text: Medium-length text

        Returns:
            Enhanced text
        """
        # Split into sentences (rough heuristic)
        sentences = re.split(r'([.!?]\s+)', text)
        enhanced_sentences = []

        for i, segment in enumerate(sentences):
            if not segment.strip():
                continue

            # If this is a delimiter (period, etc), keep it
            if re.match(r'^[.!?]\s+$', segment):
                enhanced_sentences.append(segment)
                continue

            # Process sentence
            words = segment.split()
            processed_words = []

            for j, word in enumerate(words):
                # First word of sentence - capitalize
                if j == 0:
                    # Check if it's already mixed case (likely proper noun)
                    if word[0].isupper() and any(c.isupper() for c in word[1:]):
                        processed_words.append(word)
                    else:
                        processed_words.append(word.capitalize())

                # Already has capitals (proper noun/acronym) - keep as is
                elif any(c.isupper() for c in word):
                    processed_words.append(word)

                # Common lowercase words - keep lowercase
                elif word.lower() in self.lowercase_words:
                    processed_words.append(word.lower())

                # Default - keep as is
                else:
                    processed_words.append(word)

            enhanced_sentences.append(' '.join(processed_words))

        result = ''.join(enhanced_sentences)

        # Add period at end if no punctuation
        if result and result[-1] not in '.!?':
            result += '.'

        return result

    def _is_proper_noun(self, word: str) -> bool:
        """
        Heuristic to detect if a word is likely a proper noun.

        Args:
            word: Single word

        Returns:
            True if likely a proper noun
        """
        # Very simple heuristic - expand as needed
        common_proper_nouns = {'amazon', 'google', 'apple', 'microsoft', 'claude',
                                'jarvis', 'siri', 'alexa', 'python', 'java'}
        return word.lower() in common_proper_nouns


# Singleton instance for convenience
_service_instance = None


def get_text_enhancement_service(config: Optional[dict] = None) -> TextEnhancementService:
    """
    Get or create the text enhancement service singleton.

    Args:
        config: Optional configuration dict

    Returns:
        TextEnhancementService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = TextEnhancementService(config)
    return _service_instance


def enhance_text(text: str) -> str:
    """
    Convenience function for text enhancement.

    Args:
        text: Raw transcribed text

    Returns:
        Enhanced text
    """
    service = get_text_enhancement_service()
    return service.enhance(text)
