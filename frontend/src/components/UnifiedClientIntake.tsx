import { useEffect, useState, type FormEvent } from "react";
import { getClientProfile, updateClientCase, updateClientProfile, type ClientDetailItem, type M01CaseUpdatePayload, type M01EmploymentStatus, type ClientProfileUpdatePayload } from "../api/clientsApi";

type Props = { client: ClientDetailItem; onUpdated: () => Promise<void> };

const employmentOptions: Array<[M01EmploymentStatus, string]> = [
  ["salaried_employee", "שכיר/ה"], ["self_employed", "עצמאי/ת"],
  ["salaried_and_self_employed", "שכיר/ה ועצמאי/ת"],
  ["not_currently_working", "לא עובד/ת"], ["unknown", "לא ידוע"]
];

function caseDraft(client: ClientDetailItem): M01CaseUpdatePayload {
  const entry = client.m01_case;
  return {
    display_name: entry?.display_name || client.full_name,
    id_number: entry?.id_number || client.id_number || "",
    birth_date: entry?.birth_date || client.birth_date,
    gender: entry?.gender || null,
    employment_status: entry?.employment_status || null,
    planned_retirement_age: entry?.planned_retirement_age ?? null,
    planned_retirement_date: entry?.planned_retirement_date || null
  };
}

export function UnifiedClientIntake({ client, onUpdated }: Props) {
  const [draft, setDraft] = useState(() => caseDraft(client));
  const [retirementMode, setRetirementMode] = useState<"" | "age" | "date">(() => client.m01_case?.planned_retirement_date ? "date" : client.m01_case?.planned_retirement_age != null ? "age" : "");
  const [contact, setContact] = useState<ClientProfileUpdatePayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [contactError, setContactError] = useState("");

  useEffect(() => {
    setDraft(caseDraft(client));
    setRetirementMode(client.m01_case?.planned_retirement_date ? "date" : client.m01_case?.planned_retirement_age != null ? "age" : "");
  }, [client.client_id, client.m01_case?.updated_at]);
  useEffect(() => {
    let active = true;
    setContact(null);
    setContactError("");
    void getClientProfile(client.client_id).then(response => {
      if (!active) return;
      const value = response.profile;
      setContact({
        id_number: value?.id_number || client.id_number,
        birth_date: value?.birth_date || client.birth_date,
        gender: value?.gender || client.m01_case?.gender || null,
        contact_method: value?.contact_method || null,
        contact_details: value?.contact_details || null,
        notes: value?.notes || null
      });
    }).catch(() => { if (active) setContactError("פרטי קשר אינם זמינים כרגע. ניתן לשמור את פרטי תיק הפרישה."); });
    return () => { active = false; };
  }, [client.client_id]);

  async function saveCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setMessage("");
    try {
      await updateClientCase(client.client_id, draft);
      await onUpdated();
      setMessage("פרטי תיק הפרישה נשמרו.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "שמירת פרטי התיק נכשלה");
    } finally { setBusy(false); }
  }
  async function saveContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !contact) return;
    setBusy(true);
    setMessage("");
    try {
      await updateClientProfile(client.client_id, contact);
      await onUpdated();
      setMessage("פרטי הקשר נשמרו.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "שמירת פרטי הקשר נכשלה");
    } finally { setBusy(false); }
  }

  return <section aria-label="פרטי הלקוח ותכנון פרישה">
    <h2>פרטי תיק הפרישה</h2>
    <p className="professional-workspace__sub">השלם את הפרטים הדרושים לתכנון. מידע חסר יוצג כאן, ולא כקודי מערכת.</p>
    <form onSubmit={saveCase} className="professional-workspace__intake">
      <div className="professional-workspace__edit-grid">
        <label>שם מלא<input required value={draft.display_name} onChange={e => setDraft({ ...draft, display_name: e.target.value })}/></label>
        <label>מספר זהות<input required value={draft.id_number} onChange={e => setDraft({ ...draft, id_number: e.target.value })}/></label>
        <label>תאריך לידה<input type="date" value={draft.birth_date || ""} onChange={e => setDraft({ ...draft, birth_date: e.target.value || null })}/></label>
        <label>מגדר<input value={draft.gender || ""} onChange={e => setDraft({ ...draft, gender: e.target.value || null })} placeholder="זכר / נקבה"/></label>
        <label>מצב תעסוקה<select value={draft.employment_status || ""} onChange={e => setDraft({ ...draft, employment_status: (e.target.value || null) as M01EmploymentStatus | null })}>
          <option value="">לא תועד</option>{employmentOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label>תכנון מועד הפרישה<select value={retirementMode} onChange={e => {
          const mode = e.target.value as "" | "age" | "date";
          setRetirementMode(mode);
          setDraft({ ...draft, planned_retirement_age: mode === "age" ? draft.planned_retirement_age : null, planned_retirement_date: mode === "date" ? draft.planned_retirement_date : null });
        }}>
          <option value="">טרם נקבע</option><option value="age">לפי גיל</option><option value="date">לפי תאריך</option>
        </select></label>
        {retirementMode === "age" && <label>גיל פרישה מתוכנן<input type="number" min={18} max={120} value={draft.planned_retirement_age ?? ""} onChange={e => setDraft({ ...draft, planned_retirement_age: e.target.value ? Number(e.target.value) : null })}/></label>}
        {retirementMode === "date" && <label>תאריך פרישה מתוכנן<input type="date" value={draft.planned_retirement_date ?? ""} onChange={e => setDraft({ ...draft, planned_retirement_date: e.target.value || null })}/></label>}
      </div>
      <div className="professional-workspace__actions"><button type="submit" disabled={busy}>{busy ? "שומר..." : "שמירת פרטי תיק"}</button></div>
    </form>
    <details className="professional-workspace__advanced">
      <summary>פרטי קשר והערות</summary>
      {contactError && <p role="alert">{contactError}</p>}
      {contact && <form onSubmit={saveContact}>
        <div className="professional-workspace__edit-grid">
          <label>אמצעי קשר<input value={contact.contact_method || ""} onChange={e => setContact({ ...contact, contact_method: e.target.value || null })}/></label>
          <label>פרטי קשר<input value={contact.contact_details || ""} onChange={e => setContact({ ...contact, contact_details: e.target.value || null })}/></label>
          <label>הערות<textarea value={contact.notes || ""} onChange={e => setContact({ ...contact, notes: e.target.value || null })}/></label>
        </div>
        <div className="professional-workspace__actions"><button type="submit" disabled={busy}>שמירת פרטי קשר</button></div>
      </form>}
    </details>
    {message && <p role="status">{message}</p>}
  </section>;
}
