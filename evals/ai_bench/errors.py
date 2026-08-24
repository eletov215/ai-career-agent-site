class BenchmarkError(RuntimeError):
    """Base error for benchmark configuration or execution failures."""


class ConfigurationError(BenchmarkError):
    """Raised when benchmark configuration is invalid."""


class DatasetError(BenchmarkError):
    """Raised when the benchmark dataset violates its contract."""


class ProviderError(BenchmarkError):
    """Raised when a provider adapter cannot return a usable response."""
