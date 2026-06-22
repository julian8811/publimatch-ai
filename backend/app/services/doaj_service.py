"""DOAJ (Directory of Open Access Journals) verification service.

Provides async lookups against the DOAJ API v3 to verify whether a
journal is indexed in DOAJ. The result feeds the risk assessment
pipeline and the ``indexed_doaj`` flag on journal records.
"""

import logging

import httpx

logger = logging.getLogger(__name__)


class DOAJService:
    """Verify journal status in the Directory of Open Access Journals.

    Uses the DOAJ public API v3 (no API key required for basic search).
    On any failure (timeout, non-200, parse error) returns conservative
    defaults so the caller can continue without crashing.
    """

    BASE_URL = "https://doaj.org/api/v3"

    async def verify_journal(self, issn: str) -> dict:
        """Check if a journal identified by ISSN is indexed in DOAJ.

        Args:
            issn: The ISSN string (print or online), with or without hyphen.
                  E.g. ``"1932-6203"``.

        Returns:
            dict with keys:
                ``in_doaj`` (bool) — whether the journal was found.
                ``total_results`` (int) — number of matching articles.
                ``error`` (str, optional) — present only on API failure.
        """
        if not issn or not issn.strip():
            return {"in_doaj": False, "total_results": 0}

        clean_issn = issn.strip().replace("-", "")
        url = f"{self.BASE_URL}/search/articles/issn:{clean_issn}"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, timeout=10.0)

                if resp.status_code == 401:
                    logger.warning(
                        "DOAJ API returned 401 for ISSN %s (API key may be "
                        "required for v3). Falling back to safe defaults.",
                        clean_issn,
                    )
                    return {"in_doaj": False, "total_results": 0}

                if resp.status_code != 200:
                    logger.error(
                        "DOAJ returned %d for ISSN %s",
                        resp.status_code,
                        clean_issn,
                    )
                    return {
                        "in_doaj": False,
                        "total_results": 0,
                        "error": f"DOAJ returned {resp.status_code}",
                    }

                data = resp.json()
                total = data.get("total", 0)
                return {
                    "in_doaj": total > 0,
                    "total_results": total,
                }

            except httpx.TimeoutException:
                logger.warning("DOAJ API timed out for ISSN %s", clean_issn)
                return {"in_doaj": False, "total_results": 0, "error": "timeout"}

            except Exception as e:
                logger.error(
                    "DOAJ API error for ISSN %s: %s", clean_issn, e, exc_info=True
                )
                return {"in_doaj": False, "total_results": 0, "error": str(e)}
