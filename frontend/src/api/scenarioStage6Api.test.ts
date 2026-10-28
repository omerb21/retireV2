import { afterEach, expect, it, vi } from "vitest";
import {
  listScenarioPensionElections, saveScenarioPensionElections,
  readFactorAdmissionCursor, submitProfessionalFactorAdmission,
  readScenarioAllocationEvidence, validScenarioAllocationEvidence,
} from "./scenarioStage6Api";

const network=vi.hoisted(() => ({ fetch:vi.fn(), url:vi.fn((x:string)=>"/api"+x) }));
vi.mock("./apiBase",() => ({ apiFetch:network.fetch, buildApiUrl:network.url }));
afterEach(() => { vi.clearAllMocks(); });

it("removes read-only authority evidence from a round-trip write payload",async () => {
  network.fetch.mockResolvedValueOnce({
    ok:true,json:async()=>({elections:[{
      decision_id:"d",pension_start_date:"2027-09-30",target_year:2027,
      survivors_option:"spouse",spouse_age_diff:0,
      coefficient_selection:"manual_review_required",
      company_name:"Company",option_name:"Plan",
      authority_state:"NOT_EVALUATED",untrusted_extra:"never-echo",
    }]}),
  }).mockResolvedValueOnce({ok:true,json:async()=>({scenario_version:3})});
  const elections=await listScenarioPensionElections(1,"scenario");
  expect(Object.keys(elections[0])).not.toContain("authority_state");
  expect(Object.keys(elections[0])).not.toContain("untrusted_extra");
  await saveScenarioPensionElections(1,"scenario",2,elections);
  const [,request]=network.fetch.mock.calls[1] as [string, RequestInit];
  const payload=JSON.parse(request.body as string);
  expect(payload.expected_scenario_version).toBe(2);
  expect(payload.elections[0]).toHaveProperty("decision_id","d");
  expect(payload.elections[0]).not.toHaveProperty("authority_state");
  expect(payload.elections[0]).not.toHaveProperty("untrusted_extra");
});

it("factor receipt uses server CAS cursor and never posts actor or source hashes",async () => {
  network.fetch.mockResolvedValueOnce({
    ok:true,json:async()=>({
      scenario_version:4,latest_admission_revision:2,authority_state:"NOT_EVALUATED",
    }),
  }).mockResolvedValueOnce({
    ok:true,json:async()=>({
      admission_revision:3,professional_admission_fingerprint:"a".repeat(64),
      execution_allowed:false,
    }),
  });
  const cursor=await readFactorAdmissionCursor(2,"sc","decision");
  await submitProfessionalFactorAdmission(2,"sc","decision",{
    expected_scenario_version:cursor.scenario_version,
    expected_admission_revision:cursor.latest_admission_revision,
    factor_value:"200",
    factor_evidence_type:"PLANNER_ASSUMPTION",
    factor_evidence_reference:"Professional estimate",
  });
  const [url,options]=network.fetch.mock.calls[1] as [string,RequestInit];
  expect(url).toContain("/pension-decisions/decision/factor-admissions");
  const payload=JSON.parse(options.body as string);
  expect(payload.expected_admission_revision).toBe(2);
  expect(payload).not.toHaveProperty("actor_id");
  expect(payload).not.toHaveProperty("manifest_fingerprint");
  expect(payload).not.toHaveProperty("source_id");
});


it("allocation evidence uses GET only and remains outside financial write pipeline", async () => {
  const envelope = {
    manifest_fingerprint:"a".repeat(64),
    candidate_evidence_state:"STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
    candidate_blockers:[],
    overall_status:"STRUCTURAL_ONLY",
    allocation_evidence:{
      schema_version:"SCENARIO_ALLOCATION_EVIDENCE_V1",
      client_id:7,scenario_id:"sc",scenario_version:2,
      manifest_fingerprint:"a".repeat(64),
      evidence_fingerprint:"b".repeat(64),
      overall_status:"STRUCTURAL_ONLY",blocker_codes:[],
      sources:[],financial_result:null,execution_allowed:false,
    },
    financial_result:null,execution_allowed:false,
  };
  network.fetch.mockResolvedValueOnce({ok:true,json:async()=>envelope});
  expect(await readScenarioAllocationEvidence(7,"sc")).toEqual(envelope);
  const [url,options]=network.fetch.mock.calls[0] as [string,RequestInit];
  expect(url).toBe("/api/clients/7/scenario-drafts/sc/allocation-evidence");
  expect(options).toEqual({});
});

it("allocation evidence uses encoded scenario identity and never includes body", async () => {
  network.fetch.mockResolvedValueOnce({ok:true,json:async()=>({})});
  await readScenarioAllocationEvidence(7,"id/with space");
  const [url,options]=network.fetch.mock.calls[0] as [string,RequestInit];
  expect(url).toContain("id%2Fwith%20space/allocation-evidence");
  expect(options.body).toBeUndefined();
  expect(options.method).toBeUndefined();
});

const validEvidence = () => ({
  manifest_fingerprint:"a".repeat(64),
  candidate_evidence_state:"STRUCTURALLY_CONSISTENT_NOT_ADMITTED",
  candidate_blockers:[],
  overall_status:"STRUCTURAL_ONLY" as const,
  allocation_evidence:{
    schema_version:"SCENARIO_ALLOCATION_EVIDENCE_V1" as const,
    client_id:7,scenario_id:"sc",scenario_version:2,
    manifest_fingerprint:"a".repeat(64),
    evidence_fingerprint:"b".repeat(64),
    overall_status:"STRUCTURAL_ONLY" as const,blocker_codes:[],
    sources:[{
      product_id:"p",component_id:"c",component_code:"a",
      balance:"100.00",allocated:"50.00",unallocated:"50.00",
      status:"STRUCTURAL_ONLY" as const,blocker_codes:[],decision_ids:["d"],
    }],
    financial_result:null,execution_allowed:false as const,
  },
  financial_result:null,execution_allowed:false as const,
});

it("accepts only informational evidence with exact scenario context", () => {
  const value = validEvidence();
  expect(validScenarioAllocationEvidence(value,7,"sc",2)).toBe(true);
  expect(validScenarioAllocationEvidence(value,8,"sc",2)).toBe(false);
  expect(validScenarioAllocationEvidence(value,7,"other",2)).toBe(false);
  expect(validScenarioAllocationEvidence(value,7,"sc",3)).toBe(false);
});

it("rejects stale or forged structural evidence rows before display", () => {
  const base = validEvidence();
  const forged = (value: unknown) => validScenarioAllocationEvidence(
    value as ReturnType<typeof validEvidence>,7,"sc",2);
  expect(forged({...base,execution_allowed:true})).toBe(false);
  expect(forged({...base,manifest_fingerprint:"f".repeat(64)})).toBe(false);
  expect(forged({...base,allocation_evidence:{...base.allocation_evidence,financial_result:{amount:100}}})).toBe(false);
  expect(forged({...base,allocation_evidence:{...base.allocation_evidence,evidence_fingerprint:"bad"}})).toBe(false);
  expect(forged({...base,allocation_evidence:{...base.allocation_evidence,sources:[
    {...base.allocation_evidence.sources[0],unallocated:"-1.00"},
  ]}})).toBe(false);
  expect(forged({...base,allocation_evidence:{...base.allocation_evidence,sources:[
    {...base.allocation_evidence.sources[0],status:"BLOCKED"},
  ]}})).toBe(false);
  expect(forged({...base,overall_status:"STRUCTURAL_ONLY",candidate_blockers:["SOURCE_STALE"]})).toBe(false);
});


it("fails closed on mismatched aggregate statuses and fabricated available amounts", () => {
  const base=validEvidence();
  const check=(v:unknown)=>validScenarioAllocationEvidence(
    v as ReturnType<typeof validEvidence>,7,"sc",2);
  expect(check({...base,overall_status:"STRUCTURAL_ONLY",
    allocation_evidence:{...base.allocation_evidence,overall_status:"BLOCKED"}})).toBe(false);
  expect(check({...base,allocation_evidence:{...base.allocation_evidence,sources:[
    {...base.allocation_evidence.sources[0],unallocated:null},
  ]}})).toBe(false);
  expect(check({...base,allocation_evidence:{...base.allocation_evidence,sources:[
    {...base.allocation_evidence.sources[0],allocated:"1e3"},
  ]}})).toBe(false);
  expect(check({...base,allocation_evidence:{...base.allocation_evidence,sources:[
    {...base.allocation_evidence.sources[0],balance:"-100.00"},
  ]}})).toBe(false);
});

it("accepts explicitly blocked source without inventing an unallocated balance", () => {
  const value=validEvidence();
  const blocked={
    ...value,overall_status:"BLOCKED" as const,
    allocation_evidence:{
      ...value.allocation_evidence,
      overall_status:"BLOCKED" as const,
      blocker_codes:["SOURCE_MISSING"],
      sources:[{
        ...value.allocation_evidence.sources[0],
        status:"BLOCKED" as const,blocker_codes:["SOURCE_MISSING"],
        balance:null,unallocated:null,
      }],
    },
  };
  expect(validScenarioAllocationEvidence(blocked,7,"sc",2)).toBe(true);
});


it("never displays structurally admitted status for a blocked candidate", () => {
  const valid=validEvidence();
  const changed={
    ...valid,candidate_evidence_state:"BLOCKED",
    overall_status:"STRUCTURAL_ONLY" as const,
  };
  expect(validScenarioAllocationEvidence(changed,7,"sc",2)).toBe(false);
});

it("never displays unknown candidate classification as trusted structural evidence", () => {
  const valid=validEvidence();
  const changed={
    ...valid,candidate_evidence_state:"READY_FOR_FINANCIAL_EXECUTION",
    overall_status:"STRUCTURAL_ONLY" as const,
  };
  expect(validScenarioAllocationEvidence(changed,7,"sc",2)).toBe(false);
});
