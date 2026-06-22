"""Tests for DOAJService with mocked HTTP responses.

Uses ``respx`` to mock ``httpx.AsyncClient`` calls to the DOAJ API
so no external network access is required.

NOTE: DOAJService strips hyphens from ISSN before making the API call,
so mocked URLs use the cleaned (unhyphenated) ISSN.
"""

import httpx
import pytest
import respx

from app.services.doaj_service import DOAJService


def _clean_issn(issn: str) -> str:
    """Match the service's internal ISSN cleaning."""
    return issn.strip().replace("-", "")


class TestDOAJService:
    """Tests for DOAJService.verify_journal."""

    def setup_method(self):
        self.service = DOAJService()
        self.base_url = "https://doaj.org/api/v3"

    # ------------------------------------------------------------------
    # Journal found in DOAJ
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_journal_found(self):
        """ISSN listed in DOAJ should return in_doaj=True."""
        issn = "1932-6203"
        clean = _clean_issn(issn)
        with respx.mock:
            route = respx.get(f"{self.base_url}/search/articles/issn:{clean}")
            route.mock(
                return_value=httpx.Response(
                    200,
                    json={"total": 5, "results": []},
                )
            )

            result = await self.service.verify_journal(issn)
            assert result["in_doaj"] is True
            assert result["total_results"] == 5

    # ------------------------------------------------------------------
    # Journal not found in DOAJ
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_journal_not_found(self):
        """ISSN not in DOAJ should return in_doaj=False."""
        issn = "0000-0000"
        clean = _clean_issn(issn)
        with respx.mock:
            route = respx.get(f"{self.base_url}/search/articles/issn:{clean}")
            route.mock(
                return_value=httpx.Response(
                    200,
                    json={"total": 0, "results": []},
                )
            )

            result = await self.service.verify_journal(issn)
            assert result["in_doaj"] is False
            assert result["total_results"] == 0

    # ------------------------------------------------------------------
    # API returns non-200 (server error)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_journal_api_error(self):
        """DOAJ API 500 error should return safe defaults, not raise."""
        issn = "1234-5678"
        clean = _clean_issn(issn)
        with respx.mock:
            route = respx.get(f"{self.base_url}/search/articles/issn:{clean}")
            route.mock(return_value=httpx.Response(500))

            result = await self.service.verify_journal(issn)
            assert result["in_doaj"] is False
            assert result["total_results"] == 0
            assert "error" in result

    # ------------------------------------------------------------------
    # API unauthorized
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_journal_unauthorized(self):
        """DOAJ API 401 should return safe defaults."""
        issn = "1234-5678"
        clean = _clean_issn(issn)
        with respx.mock:
            route = respx.get(f"{self.base_url}/search/articles/issn:{clean}")
            route.mock(return_value=httpx.Response(401))

            result = await self.service.verify_journal(issn)
            assert result["in_doaj"] is False
            assert result["total_results"] == 0

    # ------------------------------------------------------------------
    # API timeout
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_journal_timeout(self):
        """DOAJ API timeout should return safe defaults without raising."""
        issn = "1234-5678"
        clean = _clean_issn(issn)
        with respx.mock:
            route = respx.get(f"{self.base_url}/search/articles/issn:{clean}")
            route.mock(side_effect=httpx.TimeoutException("timeout"))

            result = await self.service.verify_journal(issn)
            assert result["in_doaj"] is False
            assert result["total_results"] == 0

    # ------------------------------------------------------------------
    # Empty ISSN
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_empty_issn(self):
        """Empty ISSN string should return safe defaults immediately."""
        result = await self.service.verify_journal("")
        assert result["in_doaj"] is False
        assert result["total_results"] == 0

    @pytest.mark.asyncio
    async def test_verify_none_issn(self):
        """None ISSN should return safe defaults immediately."""
        result = await self.service.verify_journal(None)  # type: ignore[arg-type]
        assert result["in_doaj"] is False
        assert result["total_results"] == 0

    # ------------------------------------------------------------------
    # ISSN with hyphen
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_verify_issn_with_hyphen(self):
        """ISSN with hyphen is stripped before the API call."""
        issn = "1932-6203"
        clean = _clean_issn(issn)
        with respx.mock:
            route = respx.get(f"{self.base_url}/search/articles/issn:{clean}")
            route.mock(
                return_value=httpx.Response(
                    200,
                    json={"total": 3, "results": []},
                )
            )

            result = await self.service.verify_journal(issn)
            assert result["in_doaj"] is True
            assert result["total_results"] == 3
