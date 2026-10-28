import { afterEach, expect, it, vi } from "vitest";
import {
  listScenarioPensionElections, saveScenarioPensionElections,
  readFactorAdmissionCursor, submitProfessionalFactorAdmission,
} from "./scenarioStage6Api";

const network=vi.hoisted(() => ({ fetch:vi.fn(), url:vi.fn((x:string)=>"/api"+x) }));
vi.mock("./apiBase",() => ({ apiFetch:network.fetch, buildApiUrl:network.url }));
afterEach(() => { vi.resetAllMocks(); });

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
