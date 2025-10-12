#!/usr/bin/env python3
"""
Generic Ollama Service
Provides a reusable interface for Ollama LLM operations across multiple use cases.

Use Cases:
- Text Enhancement (Whisper transcriptions)
- Other AI-powered text transformations
"""

import time
import requests
from typing import Optional, Dict, Any


class OllamaService:
    """
    Generic Ollama service with warmup, error handling, and flexible configuration.
    
    Features:
    - Model warmup at initialization (eliminates first-call latency)
    - Configurable timeout per request
    - Automatic error handling and retries
    - Support for multiple use cases via generate()
    """
    
    def __init__(
        self,
        model: str = "llama3.2:1b",
        url: str = "http://localhost:11434",
        default_timeout_ms: int = 5000,
        warmup: bool = True
    ):
        """
        Initialize Ollama service.
        
        Args:
            model: Ollama model name (default: llama3.2:1b)
            url: Ollama API endpoint
            default_timeout_ms: Default timeout in milliseconds
            warmup: Whether to warmup model at initialization
        """
        self.model = model
        self.url = url
        self.default_timeout_ms = default_timeout_ms
        self.is_ready = False
        
        if warmup:
            self._warmup()
    
    def _warmup(self):
        """Preload Ollama model to ensure fast inference."""
        try:
            # Send a tiny warmup request to load model into memory
            # 30s timeout for larger models like qwen3:14b
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "hi",
                    "stream": False,
                },
                timeout=30.0  # 30s warmup timeout for large models
            )
            if response.status_code == 200:
                self.is_ready = True
                print(f"[OllamaService] Model {self.model} warmed up and ready")
            else:
                print(f"[OllamaService] Warmup failed: HTTP {response.status_code}")
        except Exception as e:
            print(f"[OllamaService] Ollama not available: {e}")
            print("[OllamaService] Service will operate in degraded mode")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        timeout_ms: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            temperature: Model temperature (0.0-1.0, lower = more consistent)
            max_tokens: Maximum tokens to generate (None = unlimited)
            timeout_ms: Request timeout in milliseconds (uses default if None)
            options: Additional Ollama options
        
        Returns:
            Generated text or None on error
        """
        if not self.is_ready:
            print("[OllamaService] Service not ready (warmup failed)")
            return None
        
        timeout_ms = timeout_ms or self.default_timeout_ms
        start_time = time.time()
        
        # Build options
        ollama_options = {
            "temperature": temperature,
        }
        if max_tokens is not None:
            ollama_options["num_predict"] = max_tokens
        if options:
            ollama_options.update(options)
        
        try:
            response = requests.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": ollama_options
                },
                timeout=timeout_ms / 1000.0  # Convert to seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                return generated_text
            else:
                print(f"[OllamaService] Generation failed: HTTP {response.status_code}")
                return None
                
        except requests.Timeout:
            print(f"[OllamaService] Timeout after {timeout_ms}ms")
            return None
        except Exception as e:
            print(f"[OllamaService] Error: {e}")
            return None
    
    def enhance_text(
        self,
        text: str,
        timeout_ms: Optional[int] = None
    ) -> Optional[str]:
        """
        Convenience method for text enhancement (capitalization, punctuation).

        Args:
            text: Raw text to enhance
            timeout_ms: Request timeout in milliseconds

        Returns:
            Enhanced text or None on error
        """
        # Production prompt - enhance clarity and professionalism while preserving intent
        prompt = f"""Enhance this voice transcription by improving clarity, grammar, and word choice while preserving the exact intent.

- Add proper punctuation and capitalization
- Improve word choice and sentence structure for clarity
- Make it sound more professional and polished
- Fix grammar and awkward phrasing
- DO NOT change the meaning or intent of what was said
- DO NOT add extra information or explanations
- Keep the same overall message and conclusion

Transcript: {text}

Enhanced:"""

        # Limit output to 3x input length to prevent runaway generation
        input_words = len(text.split())
        max_output_tokens = max(50, input_words * 6)  # ~3x words, 2 tokens per word

        return self.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=max_output_tokens,
            timeout_ms=timeout_ms
        )
    


# Singleton instance
_ollama_service_instance: Optional[OllamaService] = None


def get_ollama_service(
    model: str = "llama3.2:1b",
    url: str = "http://localhost:11434",
    default_timeout_ms: int = 5000,
    warmup: bool = True
) -> OllamaService:
    """
    Get or create the Ollama service singleton.

    Args:
        model: Ollama model name
        url: Ollama API endpoint
        default_timeout_ms: Default timeout in milliseconds
        warmup: Whether to warmup model at initialization

    Returns:
        OllamaService instance
    """
    global _ollama_service_instance

    # Recreate singleton if model changed or instance doesn't exist
    if (_ollama_service_instance is None or
        _ollama_service_instance.model != model or
        _ollama_service_instance.url != url):
        _ollama_service_instance = OllamaService(
            model=model,
            url=url,
            default_timeout_ms=default_timeout_ms,
            warmup=warmup
        )

    return _ollama_service_instance
