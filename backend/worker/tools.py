from typing import Any

from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.tracing import get_trace_id

logger = get_logger(__name__)


def get_tavily_client() -> TavilyClient | None:
    if not settings.TAVILY_API_KEY:
        return None
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def tavily_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    trace_id = get_trace_id()
    client = get_tavily_client()

    if client is None:
        logger.warning(
            "Tavily API key not configured returning stub results",
            extra={"trace_id": trace_id, "query": query},
        )
        return [
            {
                "title": f"Stub result for: {query}",
                "url": "https://example.com/stub",
                "content": f"This is a stub search result for query: {query}. Tavily API key is not configured.",
                "score": 0.5,
            }
        ]

    try:
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=False,
        )
        results = response.get("results", [])
        logger.info(
            "tavily search completed",
            extra={
                "trace_id": trace_id,
                "query": query,
                "num_results": len(results),
            },
        )
        return results
    except Exception as e:
        logger.error(
            "tavily search failed",
            extra={"trace_id": trace_id, "query": query, "error": str(e)},
        )
        raise
