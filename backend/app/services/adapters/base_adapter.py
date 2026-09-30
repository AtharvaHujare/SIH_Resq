from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseAdapter(ABC):
    """Abstract Base Class defining the contract for external data ingestion adapters."""

    def __init__(self, source_id: str, name: str):
        self.source_id = source_id
        self.name = name

    @abstractmethod
    async def fetch(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """Asynchronously query external service endpoint and return raw response payload."""
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Transform raw external payload into normalized domain observation dictionaries."""
        pass

    @abstractmethod
    def validate(self, normalized_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate structure, types, boundary constraints, and reject malformed records."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verify remote endpoint connectivity, API key validity, or service availability."""
        pass
