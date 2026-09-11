from __future__ import annotations
from dataclasses import replace
from teldrive_lab.manifest import Manifest, ManifestEntry, ProviderReference, manifest_from_records, stable_object_id
from teldrive_lab.models import EncryptionClass, FileRecord, HashState, SourceType, VerificationState
from teldrive_lab.provider import ProviderCapability, ProviderErrorClass, ProviderHealth, ProviderState, classify_provider_error, retry_decision
from teldrive_lab.provider_resilience import plan_evacuation

def record(path="/tmp/a.bin", verified=True):
    return FileRecord(path, path.rsplit("/",1)[-1], "/tmp", 10, "application/octet-stream", ".bin", None, None, "a"*64, HashState.VERIFIED, SourceType.LOCAL, "local:test", None, None, None, None, None, EncryptionClass.RAW, VerificationState.VERIFIED if verified else VerificationState.UNVERIFIED, None, None, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")

def test_manifest_round_trip_and_stable_identity():
    entry=ManifestEntry.from_record(record(), provider_reference=ProviderReference("telegram","msg:1",True)); manifest=Manifest((entry,))
    assert Manifest.from_json(manifest.to_json()) == manifest
    assert stable_object_id(record()) == entry.object_id

def test_manifest_is_provider_independent():
    entry=ManifestEntry.from_record(record(), provider_reference=ProviderReference("telegram","msg:1"))
    assert entry.logical_path == "/tmp/a.bin" and entry.object_id and entry.source_type == "LOCAL"

def test_rate_limit_classification_and_bounded_retry():
    error=classify_provider_error("telegram","429 Too Many Requests",retry_after_seconds=12)
    assert error.classification is ProviderErrorClass.RATE_LIMITED and error.retryable and error.retry_after_seconds == 12
    decision=retry_decision(error, attempt=1, max_attempts=5, base_delay_seconds=1, max_delay_seconds=30)
    assert decision.retry and decision.delay_seconds == 12
    assert not retry_decision(classify_provider_error("x","permission denied"), attempt=1).retry

def test_evacuation_requires_no_alternate_verified_copy():
    entry=ManifestEntry.from_record(record(), provider_reference=ProviderReference("telegram","msg:1",True))
    health=ProviderHealth("telegram",ProviderState.UNAVAILABLE,frozenset({ProviderCapability.READ}))
    target=ProviderHealth("local",ProviderState.HEALTHY,frozenset({ProviderCapability.READ,ProviderCapability.WRITE}))
    plan=plan_evacuation([entry],health,target_provider=target)
    assert len(plan.items)==1 and plan.target_provider=="local" and plan.bytes_at_risk==10

def test_verified_replica_removes_evacuation_risk():
    entry=replace(ManifestEntry.from_record(record(), provider_reference=ProviderReference("telegram","msg:1",True)), provider_references=(ProviderReference("telegram","msg:1",True),ProviderReference("local","/tmp/a.bin",True)))
    assert not plan_evacuation([entry],ProviderHealth("telegram",ProviderState.DEGRADED)).items

def test_unavailable_provider_without_target_remains_report_only():
    plan=plan_evacuation([ManifestEntry.from_record(record())],ProviderHealth("telegram",ProviderState.UNAVAILABLE))
    assert plan.items and plan.target_provider is None

def test_manifest_from_records_is_sorted():
    assert [e.logical_path for e in manifest_from_records([record("/z"),record("/a")]).entries] == ["/a","/z"]
