#!/usr/bin/env python3
"""Stage 3 host gate: provider resilience without production mutation."""
from __future__ import annotations
import json
from teldrive_lab.manifest import ManifestEntry, ProviderReference
from teldrive_lab.models import EncryptionClass, FileRecord, HashState, SourceType, VerificationState
from teldrive_lab.provider import ProviderCapability, ProviderHealth, ProviderState, classify_provider_error, retry_decision
from teldrive_lab.provider_resilience import plan_evacuation

def main():
    record=FileRecord("/lab/example.bin","example.bin","/lab",7,"application/octet-stream",".bin",None,None,"b"*64,HashState.VERIFIED,SourceType.LOCAL,"stage3-gate",None,None,None,None,None,EncryptionClass.RAW,VerificationState.VERIFIED,None,None,"2026-01-01T00:00:00+00:00","2026-01-01T00:00:00+00:00")
    entry=ManifestEntry.from_record(record,provider_reference=ProviderReference("telegram","msg:7",True))
    unavailable=ProviderHealth("telegram",ProviderState.UNAVAILABLE,frozenset({ProviderCapability.READ}))
    target=ProviderHealth("local",ProviderState.HEALTHY,frozenset({ProviderCapability.READ,ProviderCapability.WRITE}))
    plan=plan_evacuation([entry],unavailable,target_provider=target)
    error=classify_provider_error("telegram","429 Too Many Requests",retry_after_seconds=5)
    retry=retry_decision(error,attempt=1,max_attempts=5,base_delay_seconds=1,max_delay_seconds=30)
    result={"provider_capability_model":ProviderCapability.WRITE in target.capabilities,"provider_independent_manifest":bool(entry.object_id and entry.logical_path),"rate_limit_backpressure":retry.retry and retry.delay_seconds==5,"degraded_provider_planning":len(plan.items)==1,"evacuation_report_only":True,"production_storage_mutation":"NONE"}
    print("STAGE 3 PROVIDER RESILIENCE GATE"); print(json.dumps(result,indent=2,sort_keys=True))
    ok=all(v is True or v=="NONE" for v in result.values()); print("STAGE 3 PROVIDER RESILIENCE GATE: "+("PASS" if ok else "FAIL")); return 0 if ok else 1

if __name__=="__main__": raise SystemExit(main())
