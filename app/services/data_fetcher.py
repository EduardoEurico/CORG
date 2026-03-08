"""Service for fetching public organization data from external APIs.

Currently integrates with:
- Portal da Transparência (Brazilian federal government transparency portal)
  https://portaldatransparencia.gov.br/api-de-dados

When an API key is not configured, placeholder/demo data is returned so the
application can still run in development/testing mode.
"""

import logging
from decimal import Decimal
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DataFetcherError(Exception):
    """Raised when an external data source returns an error."""


class DataFetcher:
    """Client for fetching public data from external transparency APIs."""

    def __init__(self) -> None:
        self._base_url = settings.transparencia_base_url.rstrip("/")
        self._api_key = settings.transparencia_api_key
        self._timeout = 20.0

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["chave-api-dados"] = self._api_key
        return headers

    # ------------------------------------------------------------------
    # Portal da Transparência – Convenios (agreements / funds)
    # ------------------------------------------------------------------

    async def fetch_convenios(
        self,
        cnpj: str | None = None,
        year: int | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch convenio (agreement) records from Portal da Transparência.

        If no API key is configured, returns an empty list and logs a warning.
        """
        if not self._api_key:
            logger.warning(
                "transparencia_api_key not set – skipping external data fetch. "
                "Set TRANSPARENCIA_API_KEY in .env to enable live data."
            )
            return []

        params: dict[str, Any] = {"pagina": page, "tamanhoDaPagina": per_page}
        if cnpj:
            # Strip non-digit characters for the API
            params["cnpjProponente"] = cnpj.replace(".", "").replace("/", "").replace("-", "")
        if year:
            params["ano"] = year

        url = f"{self._base_url}/convenios"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=self._headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise DataFetcherError(
                f"Portal da Transparência returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise DataFetcherError(f"Network error fetching convenios: {exc}") from exc

    async def fetch_despesas(
        self,
        cnpj: str | None = None,
        year: int | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch spending (despesas) records from Portal da Transparência."""
        if not self._api_key:
            logger.warning(
                "transparencia_api_key not set – skipping external data fetch."
            )
            return []

        params: dict[str, Any] = {"pagina": page, "tamanhoDaPagina": per_page}
        if cnpj:
            params["cnpjOrdem"] = cnpj.replace(".", "").replace("/", "").replace("-", "")
        if year:
            params["ano"] = year

        url = f"{self._base_url}/despesas/documentos"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params, headers=self._headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise DataFetcherError(
                f"Portal da Transparência returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise DataFetcherError(f"Network error fetching despesas: {exc}") from exc

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def convenio_to_fund_data(convenio: dict[str, Any]) -> dict[str, Any]:
        """Map a Portal da Transparência convenio record to fund creation data."""
        valor_global = convenio.get("valorGlobal") or convenio.get("valorConvenio") or 0
        valor_desembolsado = convenio.get("valorDesembolsado") or 0

        return {
            "title": (
                convenio.get("objeto")
                or convenio.get("descricao")
                or f"Convenio {convenio.get('numero', 'N/A')}"
            )[:255],
            "allocated_amount": Decimal(str(valor_global)),
            "executed_amount": Decimal(str(valor_desembolsado)),
            "source": "Portal da Transparência",
            "external_id": str(convenio.get("numero") or convenio.get("id") or ""),
            "reference_year": (
                int(convenio["anoConvenio"])
                if convenio.get("anoConvenio")
                else None
            ),
        }


# Singleton instance
data_fetcher = DataFetcher()
