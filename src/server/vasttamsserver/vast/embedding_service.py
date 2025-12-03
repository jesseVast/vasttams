"""
Embedding Service for VAST TAMS

This service provides embedding generation using external embedding providers,
primarily via the jthaloor-ai embedder library.

See ~/Developer/gitlab/jthaloor-ai for supported embedding providers and options.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from fastapi import HTTPException

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Try to import jthaloor-ai embedder library
try:
    from jthaloor.ai.embedder import UnifiedEmbedder, EmbedderConfig
    JTHALOOR_AI_AVAILABLE = True
except ImportError:
    JTHALOOR_AI_AVAILABLE = False
    logger.warning(
        "jthaloor-ai embedder library not available. "
        "Please install jthaloor-ai from ~/Developer/gitlab/jthaloor-ai"
    )


class EmbeddingService:
    """Service for generating embeddings using external embedding providers"""
    
    def __init__(self):
        self.settings = get_settings()
        self._embedder = None
        self._initialize_embedder()
    
    def _initialize_embedder(self):
        """Initialize the embedding provider based on configuration
        
        This method is optional and will not raise exceptions if initialization fails.
        Embedding operations will fail gracefully at runtime if not properly initialized.
        """
        provider = self.settings.embedding_provider or "jthaloor-ai"
        
        logger.info(
            f"Initializing embedding service: "
            f"provider={provider}, "
            f"model={self.settings.embedding_model_name}, "
            f"dimension={self.settings.embedding_model_dimension}, "
            f"endpoint={self.settings.embedding_endpoint or 'not set'}"
        )
        
        if provider == "jthaloor-ai" or not JTHALOOR_AI_AVAILABLE:
            if not JTHALOOR_AI_AVAILABLE:
                logger.warning(
                    "jthaloor-ai embedder library not available. "
                    "Embedding functionality will be limited. "
                    "Please install jthaloor-ai from ~/Developer/gitlab/jthaloor-ai"
                )
                return
            
            try:
                # Get API key from environment if configured
                api_key = None
                if self.settings.embedding_api_key_env:
                    api_key = os.getenv(self.settings.embedding_api_key_env)
                
                # Get provider-specific config from settings
                provider_config = self.settings.embedding_provider_config
                
                # Map TAMS config to jthaloor-ai EmbedderConfig
                # jthaloor-ai uses: provider, base_url, model, timeout, api_key
                # TAMS config has: embedding_provider, embedding_endpoint, embedding_model_name, embedding_timeout, embedding_api_key_env
                
                # Determine provider type (ollama, nim, openai, gemini, nvidia)
                # If embedding_endpoint is set, try to infer provider from URL
                embedder_provider = "ollama"  # default
                base_url = self.settings.embedding_endpoint or "http://10.143.2.16:11434"
                
                # Infer provider from endpoint URL if possible
                if "openai.com" in base_url.lower():
                    embedder_provider = "openai"
                elif "generativelanguage.googleapis.com" in base_url.lower():
                    embedder_provider = "gemini"
                elif "nvidia.com" in base_url.lower() or "integrate.api.nvidia.com" in base_url.lower():
                    embedder_provider = "nvidia"
                elif provider_config.get("provider"):
                    embedder_provider = provider_config.get("provider")
                
                # Create EmbedderConfig
                embedder_config = EmbedderConfig(
                    provider=embedder_provider,
                    base_url=base_url,
                    model=self.settings.embedding_model_name,
                    timeout=self.settings.embedding_timeout,
                    api_key=api_key
                )
                
                # Initialize UnifiedEmbedder
                self._embedder = UnifiedEmbedder(embedder_config)
                
                logger.info(
                    f"Initialized jthaloor-ai embedder: provider={embedder_provider}, "
                    f"model={self.settings.embedding_model_name}, url={base_url}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize jthaloor-ai embedder (non-fatal): {e}")
                logger.info("Embedding service will not be available until properly configured")
                # Don't raise - embedding is optional
                return
        
        elif provider == "custom":
            # Custom provider implementation
            if not self.settings.embedding_endpoint:
                logger.warning("embedding_endpoint not set for custom provider. Embedding will not work.")
                return
            
            logger.info(f"Using custom embedding provider: {self.settings.embedding_endpoint}")
            # Custom provider would use _create_embedding_custom method
        
        else:
            logger.warning(f"Unknown embedding provider: {provider}. Embedding may not work.")
        
        # Log final status
        if self._embedder is not None:
            logger.info("Embedding service initialized successfully")
        else:
            logger.warning("Embedding service NOT initialized - vector operations will fail")
    
    async def create_embedding(
        self,
        text: str,
        model_name: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """
        Create an embedding vector from text.
        
        Args:
            text: Text to embed
            model_name: Optional model name override
            **kwargs: Additional provider-specific parameters
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            HTTPException: If embedding generation fails
        """
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )
        
        model = model_name or self.settings.embedding_model_name
        
        try:
            if (self.settings.embedding_provider == "jthaloor-ai" or not self.settings.embedding_provider) and JTHALOOR_AI_AVAILABLE:
                # Use jthaloor-ai embedder
                if self._embedder is None:
                    raise HTTPException(
                        status_code=503,
                        detail="Embedding service not initialized. Please check configuration."
                    )
                
                # Use async embedding method
                embeddings = await self._embedder.embed_texts_async([text], model=model, **kwargs)
                
                if not embeddings or len(embeddings) == 0:
                    raise HTTPException(
                        status_code=500,
                        detail="Embedding service returned empty result"
                    )
                
                embedding = embeddings[0]
                
                # Validate dimension matches configured dimension
                if not self.validate_embedding_dimension(embedding):
                    logger.warning(
                        f"Embedding dimension mismatch: expected {self.settings.embedding_model_dimension}, "
                        f"got {len(embedding)}. Returning embedding anyway."
                    )
                
                return embedding
            
            elif self.settings.embedding_provider == "custom":
                # Use custom endpoint
                return await self._create_embedding_custom(text, model, **kwargs)
            
            else:
                raise HTTPException(
                    status_code=501,
                    detail=f"Embedding provider '{self.settings.embedding_provider}' not implemented"
                )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create embedding: {str(e)}"
            )
    
    async def _create_embedding_custom(
        self,
        text: str,
        model_name: str,
        **kwargs
    ) -> List[float]:
        """
        Create embedding using custom endpoint.
        
        This is a placeholder implementation for custom embedding providers.
        """
        import httpx
        
        endpoint = self.settings.embedding_endpoint
        if not endpoint:
            raise HTTPException(
                status_code=500,
                detail="Custom embedding endpoint not configured"
            )
        
        # Get API key from environment if configured
        api_key = None
        if self.settings.embedding_api_key_env:
            api_key = os.getenv(self.settings.embedding_api_key_env)
        
        # Prepare request
        headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Merge provider config headers
        provider_config = self.settings.embedding_provider_config
        if isinstance(provider_config, dict):
            config_headers = provider_config.get("headers", {})
            headers.update(config_headers)
        
        payload = {
            "text": text,
            "model": model_name,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.settings.embedding_timeout) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract embedding from response
                # Common response formats:
                if "embedding" in data:
                    return data["embedding"]
                elif "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                    return data["data"][0].get("embedding", [])
                elif isinstance(data, list) and len(data) > 0:
                    return data[0] if isinstance(data[0], list) else data
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Unexpected response format from embedding endpoint"
                    )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from embedding endpoint: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Embedding endpoint returned error: {e.response.text}"
            )
        except httpx.TimeoutException:
            logger.error(f"Timeout calling embedding endpoint: {endpoint}")
            raise HTTPException(
                status_code=504,
                detail="Embedding endpoint timeout"
            )
        except Exception as e:
            logger.error(f"Error calling custom embedding endpoint: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to call embedding endpoint: {str(e)}"
            )
    
    def get_model_dimension(self, model_name: Optional[str] = None) -> int:
        """
        Get the dimension (vector size) for a given model.
        
        Args:
            model_name: Optional model name (defaults to configured model)
            
        Returns:
            Model dimension
        """
        model = model_name or self.settings.embedding_model_name
        
        # Return configured dimension (can be enhanced with model-specific lookup)
        return self.settings.embedding_model_dimension
    
    def validate_embedding_dimension(self, embedding: List[float]) -> bool:
        """
        Validate that an embedding vector matches the expected dimension.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if dimension matches, False otherwise
        """
        expected_dim = self.settings.embedding_model_dimension
        actual_dim = len(embedding)
        
        if actual_dim != expected_dim:
            logger.warning(
                f"Embedding dimension mismatch: expected {expected_dim}, got {actual_dim}"
            )
            return False
        
        return True

