import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScenarioFactorAdmissionPanel } from "./ScenarioFactorAdmissionPanel";

const mock=vi.hoisted(() => ({ cursor:vi.fn(), approve:vi.fn() }));
vi.mock("../api/scenarioStage6Api", () => ({
  readFactorAdmissionCursor:mock.cursor,
  submitProfessionalFactorAdmission:mock.approve,
}));
afterEach(() => { cleanup(); vi.resetAllMocks(); });

function panel(version=3,onApproved=vi.fn()) {
  return render(<ScenarioFactorAdmissionPanel clientId={1} scenarioId="sc"
    decisionId="d" scenarioVersion={version} disabled={false}
    onApproved={onApproved}/>);
}

it("posts authenticated CAS fields only after fresh cursor read",async () => {
  mock.cursor.mockResolvedValue({
    scenario_version:3,latest_admission_revision:4,authority_state:"NOT_EVALUATED",
  });
  mock.approve.mockResolvedValue({
    admission_revision:5,professional_admission_fingerprint:"a".repeat(64),
    execution_allowed:false,
  });
  const approved=vi.fn();
  panel(3,approved);
  fireEvent.click(screen.getByRole("button",{name:"הזן ואשר מקדם מקצועי"}));
  const factor=await screen.findByLabelText(/מקדם קצבה/);
  fireEvent.change(factor,{target:{value:"200"}});
  fireEvent.change(screen.getByLabelText("אסמכתה ותנאי המסלול"),{
    target:{value:"Document ref 123"},
  });
  fireEvent.click(screen.getByRole("button",{name:"אשר את המקדם ושמור גרסת אישור"}));
  await waitFor(() => expect(mock.approve).toHaveBeenCalledTimes(1));
  expect(mock.approve).toHaveBeenCalledWith(1,"sc","d",{
    expected_scenario_version:3,
    expected_admission_revision:4,
    factor_value:"200",
    factor_evidence_type:"PLANNER_ASSUMPTION",
    factor_evidence_reference:"Document ref 123",
  });
  await waitFor(() => expect(approved).toHaveBeenCalledTimes(1));
});

it("rejects stale approval cursor without any POST",async () => {
  mock.cursor.mockResolvedValue({
    scenario_version:2,latest_admission_revision:4,authority_state:"NOT_EVALUATED",
  });
  panel(3);
  fireEvent.click(screen.getByRole("button",{name:"הזן ואשר מקדם מקצועי"}));
  await screen.findByText(/FACTOR_ADMISSION_SCENARIO_STALE/);
  expect(mock.approve).not.toHaveBeenCalled();
});

it("never sends invalid or nonpositive factor",async () => {
  mock.cursor.mockResolvedValue({
    scenario_version:3,latest_admission_revision:0,authority_state:"NOT_EVALUATED",
  });
  panel();
  fireEvent.click(screen.getByRole("button",{name:"הזן ואשר מקדם מקצועי"}));
  const factor=await screen.findByLabelText(/מקדם קצבה/);
  fireEvent.change(factor,{target:{value:"0"}});
  fireEvent.change(screen.getByLabelText("אסמכתה ותנאי המסלול"),{
    target:{value:"assumption"},
  });
  const submit=screen.getByRole("button",{name:"אשר את המקדם ושמור גרסת אישור"});
  expect((submit as HTMLButtonElement).disabled).toBe(true);
  expect(mock.approve).not.toHaveBeenCalled();
});

it("drops old cursor when scenario version changes",async () => {
  let resolve!: (x:any)=>void;
  mock.cursor.mockReturnValueOnce(new Promise(r => {resolve=r;}));
  const view=panel(3);
  fireEvent.click(screen.getByRole("button",{name:"הזן ואשר מקדם מקצועי"}));
  view.rerender(<ScenarioFactorAdmissionPanel clientId={1}
    scenarioId="sc" decisionId="d" scenarioVersion={4}
    disabled={false} onApproved={vi.fn()}/>);
  resolve({scenario_version:3,latest_admission_revision:0,authority_state:"NOT_EVALUATED"});
  await waitFor(() => expect(screen.queryByLabelText(/מקדם קצבה/)).toBeNull());
  expect(mock.approve).not.toHaveBeenCalled();
});
