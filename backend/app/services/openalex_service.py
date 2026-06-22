import logging

import httpx
from typing import List, Dict

logger = logging.getLogger(__name__)


class OpenAlexService:
    BASE_URL = "https://api.openalex.org"

    async def fetch_journals_by_concept(self, keywords: List[str]) -> List[Dict]:
        """Fetch potential journals from OpenAlex based on extracted keywords."""
        if not keywords:
            return []

        # Search sources (journals) using the top keywords
        search_query = " ".join(keywords[:2])
        url = f"{self.BASE_URL}/sources?search={search_query}&per-page=10"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code != 200:
                    logger.error(f"OpenAlex Error: {response.text}")
                    return []

                data = response.json()
                journals = []

                for item in data.get("results", []):
                    if item.get("type") != "journal":
                        continue

                    journals.append(
                        {
                            "openalex_id": item.get("id"),
                            "name": item.get("display_name"),
                            "issn_print": item.get("issn_l"),
                            "publisher": item.get("host_organization_name", "Unknown"),
                            "country": item.get("country_code", "Unknown"),
                            "open_access": item.get("is_oa", False),
                            "apc_usd": item.get("apc_usd", 0) if item.get("apc_usd") else 0,
                            "homepage_url": item.get("homepage_url", ""),
                            "cited_by_count": item.get("cited_by_count", 0),
                        }
                    )

                logger.info(f"Fetched {len(journals)} journals from OpenAlex for keywords: {keywords[:2]}")
                return journals
            except Exception as e:
                logger.error(f"Failed to fetch from OpenAlex: {e}", exc_info=True)
                return []
