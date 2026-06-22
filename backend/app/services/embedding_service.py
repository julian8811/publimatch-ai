import logging

from google import genai

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Gemini text-embedding-004.

    Produces 768-dimension embeddings for semantic similarity scoring.
    Gracefully degrades when API key is missing or API calls fail.
    """

    def __init__(self):
        from app.core.config import settings

        self.api_key = settings.GEMINI_API_KEY
        self.model = "text-embedding-004"
        self._client = None

    @property
    def client(self):
        if self._client is None and self.api_key:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a 768-dim embedding using Gemini text-embedding-004.

        Returns an empty list if no API key is configured or the API call fails.
        """
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Cannot generate embedding.")
            return []

        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation.")
            return []

        try:
            result = self.client.models.embed_content(
                model=self.model,
                contents=text,
            )
            embedding = result.embeddings[0].values
            logger.info(
                "Generated embedding with %d dimensions for text (%d chars)",
                len(embedding),
                len(text),
            )
            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e, exc_info=True)
            return []

    @staticmethod
    def compute_cosine_similarity(
        emb1: list[float], emb2: list[float]
    ) -> float:
        """Compute cosine similarity between two embedding vectors.

        Returns 0.0 if either vector is empty or zero-norm.
        """
        if not emb1 or not emb2:
            return 0.0

        dot = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = sum(a * a for a in emb1) ** 0.5
        norm2 = sum(b * b for b in emb2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)
