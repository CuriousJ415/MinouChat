"""
Web Search Service using DuckDuckGo.

Privacy-focused web search integration for personas with web_search capability.
No API key required - uses DuckDuckGo's search engine.

Features:
- Text and news search
- Automatic search intent detection
- Result formatting for LLM context
- Character capability validation
- Rate limiting awareness
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Structured representation of a search result."""
    title: str
    url: str
    snippet: str
    source: str
    retrieved_at: str
    result_type: str = "web"
    date: Optional[str] = None
    image: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "retrieved_at": self.retrieved_at,
            "type": self.result_type,
            "date": self.date,
            "image": self.image
        }


@dataclass
class SearchIntent:
    """Represents detected search intent from a message."""
    should_search: bool
    query: Optional[str]
    intent_type: Optional[str]  # explicit, current_events, none

    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_search": self.should_search,
            "query": self.query,
            "type": self.intent_type
        }


@dataclass
class WebSearchConfig:
    """Configuration for web search service."""
    max_results: int = 5
    timeout: int = 10
    default_region: str = "wt-wt"  # Worldwide
    default_safesearch: str = "moderate"
    max_snippet_length: int = 300
    max_context_chars: int = 2000

    @classmethod
    def from_env(cls) -> "WebSearchConfig":
        """Create config from environment variables."""
        return cls(
            max_results=int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5")),
            timeout=int(os.getenv("WEB_SEARCH_TIMEOUT", "10")),
            default_region=os.getenv("WEB_SEARCH_REGION", "wt-wt"),
            default_safesearch=os.getenv("WEB_SEARCH_SAFESEARCH", "moderate"),
            max_context_chars=int(os.getenv("WEB_SEARCH_MAX_CONTEXT_CHARS", "2000"))
        )


class WebSearchError(Exception):
    """Base exception for web search errors."""
    pass


class WebSearchUnavailableError(WebSearchError):
    """Raised when DuckDuckGo search is unavailable."""
    pass


class WebSearchRateLimitError(WebSearchError):
    """Raised when rate limited by DuckDuckGo."""
    pass


class WebSearchService:
    """Service for performing privacy-focused web searches using DuckDuckGo.

    This service provides:
    - Text and news search via DuckDuckGo
    - Search intent detection from user messages
    - Result formatting for LLM context injection
    - Character capability validation

    Example:
        service = WebSearchService()
        results = service.search("latest python news", max_results=5)
        context = service.format_results_for_context(results, "python news")
    """

    # Explicit search trigger phrases
    EXPLICIT_SEARCH_TRIGGERS: List[str] = [
        "search for",
        "search the web",
        "look up",
        "find information about",
        "find info on",
        "what's the latest",
        "what is the latest",
        "current news",
        "recent news",
        "search online",
        "google",
        "look online",
        "find online"
    ]

    # Current events indicator phrases
    CURRENT_EVENT_INDICATORS: List[str] = [
        "today",
        "this week",
        "recently",
        "latest",
        "current",
        "breaking",
        "just happened",
        "right now",
        "headlines",
        "news"
    ]

    # Question patterns that may benefit from search
    QUESTION_PATTERNS: List[str] = [
        "what happened",
        "what is happening",
        "who won",
        "who is winning",
        "what's going on",
        "what are the",
        "what is the",
        "any news about",
        "have you heard about",
        "tell me about"
    ]

    def __init__(self, config: Optional[WebSearchConfig] = None):
        """Initialize the web search service.

        Args:
            config: Optional configuration. Defaults to env-based config.
        """
        self.config = config or WebSearchConfig.from_env()
        self._ddgs = None
        self._ddgs_available: Optional[bool] = None
        logger.info(
            f"WebSearchService initialized with config: "
            f"max_results={self.config.max_results}, timeout={self.config.timeout}s"
        )

    def _get_ddgs(self):
        """Lazy initialization of DuckDuckGo search client.

        Tries the newer 'ddgs' package first, falls back to 'duckduckgo_search'.

        Raises:
            WebSearchUnavailableError: If no search package installed.
        """
        if self._ddgs is None:
            try:
                # Try the newer ddgs package first
                from ddgs import DDGS
                self._ddgs = DDGS(timeout=self.config.timeout)
                self._ddgs_available = True
                logger.debug("DuckDuckGo search client initialized (ddgs package)")
            except ImportError:
                try:
                    # Fall back to duckduckgo_search
                    from duckduckgo_search import DDGS
                    self._ddgs = DDGS(timeout=self.config.timeout)
                    self._ddgs_available = True
                    logger.debug("DuckDuckGo search client initialized (duckduckgo_search package)")
                except ImportError:
                    self._ddgs_available = False
                    logger.error(
                        "No DuckDuckGo search package installed. "
                        "Install with: pip install ddgs"
                    )
                    raise WebSearchUnavailableError(
                        "ddgs or duckduckgo-search package is required for web search"
                    )
        return self._ddgs

    def is_available(self) -> bool:
        """Check if web search functionality is available.

        Returns:
            True if duckduckgo-search is installed and working.
        """
        if self._ddgs_available is not None:
            return self._ddgs_available

        try:
            self._get_ddgs()
            return True
        except WebSearchUnavailableError:
            return False

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        region: Optional[str] = None,
        safesearch: Optional[str] = None,
        timelimit: Optional[str] = None
    ) -> List[SearchResult]:
        """Perform a web search using DuckDuckGo.

        Args:
            query: Search query string (required, 1-500 chars).
            max_results: Maximum number of results (1-10).
            region: Region for search results (default: worldwide).
            safesearch: Safe search level (off, moderate, strict).
            timelimit: Time limit for results (d=day, w=week, m=month, y=year).

        Returns:
            List of SearchResult objects.

        Raises:
            WebSearchUnavailableError: If search service unavailable.
            WebSearchRateLimitError: If rate limited.
            ValueError: If query is invalid.
        """
        # Validate query
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        query = query.strip()
        if len(query) > 500:
            logger.warning(f"Query too long ({len(query)} chars), truncating to 500")
            query = query[:500]

        # Apply defaults
        results_limit = min(max_results or self.config.max_results, 10)
        region = region or self.config.default_region
        safesearch = safesearch or self.config.default_safesearch

        logger.info(
            f"Performing web search: query='{query[:50]}...', "
            f"max_results={results_limit}, region={region}"
        )

        try:
            ddgs = self._get_ddgs()

            # The ddgs package uses 'query' parameter, duckduckgo_search uses 'keywords'
            try:
                # Try new ddgs API first (query parameter)
                raw_results = list(ddgs.text(
                    query=query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=results_limit
                ))
            except TypeError:
                # Fall back to old API (keywords parameter)
                raw_results = list(ddgs.text(
                    keywords=query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=results_limit
                ))

            results = [
                self._parse_text_result(item)
                for item in raw_results
            ]

            logger.info(f"Web search for '{query[:30]}...' returned {len(results)} results")
            return results

        except WebSearchUnavailableError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "limit" in error_msg or "429" in error_msg:
                logger.warning(f"Rate limited by DuckDuckGo: {e}")
                raise WebSearchRateLimitError(f"Search rate limited: {e}")

            logger.error(f"Web search failed for query '{query[:30]}...': {e}")
            return []

    def search_news(
        self,
        query: str,
        max_results: Optional[int] = None,
        region: Optional[str] = None,
        safesearch: Optional[str] = None,
        timelimit: Optional[str] = "w"  # Default to last week for news
    ) -> List[SearchResult]:
        """Perform a news search using DuckDuckGo.

        Args:
            query: Search query string.
            max_results: Maximum number of results.
            region: Region for search results.
            safesearch: Safe search level.
            timelimit: Time limit (d=day, w=week, m=month). Defaults to week.

        Returns:
            List of SearchResult objects with type="news".
        """
        if not query or not query.strip():
            return []

        query = query.strip()
        results_limit = min(max_results or self.config.max_results, 10)
        region = region or self.config.default_region
        safesearch = safesearch or self.config.default_safesearch

        logger.info(f"Performing news search: query='{query[:50]}...', timelimit={timelimit}")

        try:
            ddgs = self._get_ddgs()

            # The ddgs package uses 'query' parameter, duckduckgo_search uses 'keywords'
            try:
                # Try new ddgs API first (query parameter)
                raw_results = list(ddgs.news(
                    query=query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=results_limit
                ))
            except TypeError:
                # Fall back to old API (keywords parameter)
                raw_results = list(ddgs.news(
                    keywords=query,
                    region=region,
                    safesearch=safesearch,
                    timelimit=timelimit,
                    max_results=results_limit
                ))

            results = [
                self._parse_news_result(item)
                for item in raw_results
            ]

            logger.info(f"News search for '{query[:30]}...' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"News search failed for query '{query[:30]}...': {e}")
            return []

    def _parse_text_result(self, item: Dict[str, Any]) -> SearchResult:
        """Parse a raw text search result into SearchResult."""
        url = item.get("href", item.get("link", ""))
        return SearchResult(
            title=item.get("title", "Untitled"),
            url=url,
            snippet=item.get("body", item.get("snippet", ""))[:self.config.max_snippet_length],
            source=self._extract_domain(url),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            result_type="web"
        )

    def _parse_news_result(self, item: Dict[str, Any]) -> SearchResult:
        """Parse a raw news search result into SearchResult."""
        url = item.get("url", item.get("link", ""))
        return SearchResult(
            title=item.get("title", "Untitled"),
            url=url,
            snippet=item.get("body", item.get("excerpt", ""))[:self.config.max_snippet_length],
            source=item.get("source", self._extract_domain(url)),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            result_type="news",
            date=item.get("date", ""),
            image=item.get("image", "")
        )

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL.

        Args:
            url: Full URL string.

        Returns:
            Domain name (e.g., 'example.com') or empty string if invalid.
        """
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def format_results_for_context(
        self,
        results: List[SearchResult],
        query: str,
        max_chars: Optional[int] = None
    ) -> str:
        """Format search results for inclusion in LLM chat context.

        Args:
            results: List of search results.
            query: Original search query.
            max_chars: Maximum characters for output.

        Returns:
            Formatted string suitable for LLM context injection.
        """
        max_chars = max_chars or self.config.max_context_chars

        if not results:
            return f"[Web search for '{query}' returned no results]"

        lines = [
            f"[Web Search Results for: {query}]",
            "INSTRUCTION: Use these search results to provide a helpful, informative answer. Synthesize the key information from the sources below. Cite specific facts and mention which sources they come from."
        ]
        current_length = sum(len(line) for line in lines)

        for i, result in enumerate(results, 1):
            result_text = f"\n{i}. {result.title}"
            if result.source:
                result_text += f" ({result.source})"
            if result.snippet:
                snippet = result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet
                result_text += f"\n   {snippet}"
            if result.url:
                result_text += f"\n   Link: {result.url}"

            if current_length + len(result_text) > max_chars:
                lines.append("\n[Additional results truncated]")
                break

            lines.append(result_text)
            current_length += len(result_text)

        lines.append("\n[End Web Search Results - Please synthesize these into a helpful response]")
        return "\n".join(lines)

    def format_results_for_display(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Format search results for frontend display.

        Args:
            results: List of search results.

        Returns:
            List of dictionaries suitable for JSON response.
        """
        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet[:300] if r.snippet else "",
                "source": r.source,
                "type": r.result_type
            }
            for r in results
        ]

    def check_capability(self, character: Dict[str, Any]) -> bool:
        """Check if a character has web search capability enabled.

        Args:
            character: Character dictionary from character_manager.

        Returns:
            True if web_search is enabled in character capabilities.
        """
        capabilities = character.get("capabilities", {})
        return bool(capabilities.get("web_search", False))

    def detect_search_intent(self, message: str) -> SearchIntent:
        """Detect if a user message implies a need for web search.

        Uses pattern matching to detect:
        - Explicit search requests ("search for...", "look up...")
        - Current events questions with time indicators

        Args:
            message: User's message text.

        Returns:
            SearchIntent with should_search, query, and intent type.
        """
        if not message or not message.strip():
            return SearchIntent(should_search=False, query=None, intent_type=None)

        message_lower = message.lower().strip()

        # Check explicit search triggers
        for trigger in self.EXPLICIT_SEARCH_TRIGGERS:
            if trigger in message_lower:
                idx = message_lower.find(trigger)
                query = message[idx + len(trigger):].strip()
                # Clean up common filler words
                query = re.sub(r'^(for|about|on)\s+', '', query, flags=re.IGNORECASE).strip()

                if query:
                    logger.debug(f"Detected explicit search intent: '{query[:50]}...'")
                    return SearchIntent(
                        should_search=True,
                        query=query,
                        intent_type="explicit"
                    )

        # Check for current events pattern
        for pattern in self.QUESTION_PATTERNS:
            if pattern in message_lower:
                for indicator in self.CURRENT_EVENT_INDICATORS:
                    if indicator in message_lower:
                        logger.debug(f"Detected current events search intent")
                        return SearchIntent(
                            should_search=True,
                            query=message,
                            intent_type="current_events"
                        )

        return SearchIntent(should_search=False, query=None, intent_type=None)


# Global service instance
web_search_service = WebSearchService()
