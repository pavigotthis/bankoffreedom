"""Server-only provider contract. No prompts or credentials are sent to clients."""

from typing import Protocol


class ProviderUnavailable(RuntimeError):
    pass


class MappingProvider(Protocol):
    def generate(self, step: int, input_snapshot: dict, approved_spec: dict) -> dict: ...


class UnconfiguredProvider:
    def generate(self, step, input_snapshot, approved_spec):
        raise ProviderUnavailable(
            "No AI provider or private mapping specification has been approved/configured. Use validated operator-authored step output for synthetic development only."
        )
