"""Report-only provider evacuation planning."""
from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable
from .manifest import ManifestEntry, requires_evacuation
from .provider import ProviderCapability, ProviderHealth, ProviderState

class EvacuationPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"

@dataclass(frozen=True, slots=True)
class EvacuationItem:
    object_id: str
    logical_path: str
    source_provider: str
    size: int | None
    sha256: str | None
    priority: EvacuationPriority
    reason: str

@dataclass(frozen=True, slots=True)
class EvacuationPlan:
    unavailable_provider: str
    target_provider: str | None
    items: tuple[EvacuationItem, ...]
    blocked: tuple[str, ...] = ()
    @property
    def bytes_at_risk(self) -> int:
        return sum(item.size or 0 for item in self.items)

def plan_evacuation(entries: Iterable[ManifestEntry], provider: ProviderHealth, *, target_provider: ProviderHealth | None = None) -> EvacuationPlan:
    blocked: list[str] = []
    if provider.state not in {ProviderState.DEGRADED, ProviderState.UNAVAILABLE}:
        blocked.append("evacuation is only planned for degraded or unavailable providers")
    target_id = target_provider.provider_id if target_provider else None
    if target_provider and ProviderCapability.WRITE not in target_provider.capabilities:
        blocked.append("target provider does not advertise WRITE capability"); target_id = None
    if target_provider and ProviderCapability.READ not in target_provider.capabilities:
        blocked.append("target provider does not advertise READ capability"); target_id = None
    items = []
    for entry in entries:
        if not requires_evacuation(entry, provider.provider_id): continue
        priority = EvacuationPriority.HIGH if target_id and entry.sha256 else EvacuationPriority.CRITICAL if not target_id else EvacuationPriority.NORMAL
        items.append(EvacuationItem(entry.object_id, entry.logical_path, provider.provider_id, entry.size, entry.sha256, priority, "verified object has no alternate verified provider copy"))
    items.sort(key=lambda item: (item.priority.value, item.logical_path, item.object_id))
    return EvacuationPlan(provider.provider_id, target_id, tuple(items), tuple(sorted(set(blocked))))

def evacuation_payload(plan: EvacuationPlan) -> dict[str, object]:
    return {"unavailable_provider": plan.unavailable_provider, "target_provider": plan.target_provider, "items": [{"object_id": i.object_id, "logical_path": i.logical_path, "source_provider": i.source_provider, "size": i.size, "sha256": i.sha256, "priority": i.priority.value, "reason": i.reason} for i in plan.items], "blocked": list(plan.blocked), "bytes_at_risk": plan.bytes_at_risk, "mutation_performed": False}
