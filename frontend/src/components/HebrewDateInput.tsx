import { useEffect, useState } from "react";
import { formatIsoDate, parseHebrewDate } from "../utils/dateFormat";

type Props = {
  id?: string;
  value: string;
  onChange: (isoValue: string) => void;
  required?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
};

export function HebrewDateInput({ id, value, onChange, required, disabled, ariaLabel }: Props) {
  const [display, setDisplay] = useState(() => formatIsoDate(value));
  const [invalid, setInvalid] = useState(false);
  useEffect(() => { setDisplay(formatIsoDate(value)); setInvalid(false); }, [value]);
  return <span>
    <input id={id} value={display} inputMode="numeric" dir="ltr" placeholder="DD/MM/YYYY"
      aria-label={ariaLabel} aria-invalid={invalid} required={required} disabled={disabled}
      onChange={(event) => {
        const next = event.target.value; setDisplay(next);
        if (!next.trim()) {
          event.currentTarget.setCustomValidity("");
          setInvalid(false); onChange(""); return;
        }
        const iso = parseHebrewDate(next);
        event.currentTarget.setCustomValidity(iso === null
          ? "תאריך לא תקין. יש להזין בתבנית DD/MM/YYYY." : "");
        setInvalid(iso === null);
        if (iso !== null) onChange(iso);
      }} />
    {invalid ? <span role="alert">תאריך לא תקין. יש להזין בתבנית DD/MM/YYYY.</span> : null}
  </span>;
}
