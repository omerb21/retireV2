import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { configureAuthenticatedApi } from "../api/apiBase";
import { login, logout, restoreSession, type AuthenticatedSession } from "../api/authApi";

export function AuthenticationGate({children, enforce = import.meta.env.MODE !== "test"}: {children: ReactNode; enforce?: boolean}) {
  const [session, setSession] = useState<AuthenticatedSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [logoutUncertain, setLogoutUncertain] = useState(false);

  useEffect(() => {
    if (!enforce) { setChecking(false); return; }
    const controller = new AbortController();
    restoreSession(controller.signal).then(value => {
      setSession(value); configureAuthenticatedApi(value.csrf_token, () => setSession(null));
    }).catch(() => { setSession(null); configureAuthenticatedApi(null); }).finally(() => setChecking(false));
    return () => controller.abort();
  }, [enforce]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage("");
    try {
      const value = await login(username, password);
      setPassword(""); setSession(value);
      configureAuthenticatedApi(value.csrf_token, () => setSession(null));
    } catch {
      setPassword(""); setMessage("ההתחברות נכשלה. יש לבדוק את הפרטים ולנסות שוב.");
    }
  }

  async function signOut() {
    const prior = session; setLogoutUncertain(true); setMessage("");
    if (!prior) return;
    try {
      const status = await logout(prior.csrf_token);
      if (status === 204 || status === 401) {
        setSession(null); configureAuthenticatedApi(null); setLogoutUncertain(false); return;
      }
      setMessage("ההתנתקות לא אושרה. המידע מוסתר עד לבדיקה או ניסיון חוזר.");
    } catch {
      setMessage("ההתנתקות לא אושרה. המידע מוסתר עד לבדיקה או ניסיון חוזר.");
    }
  }

  async function checkAfterFailedLogout() {
    setMessage("");
    try {
      const value = await restoreSession();
      setSession(value); configureAuthenticatedApi(value.csrf_token, () => setSession(null));
      setLogoutUncertain(false);
    } catch {
      setSession(null); configureAuthenticatedApi(null); setLogoutUncertain(false);
    }
  }

  if (!enforce) return <>{children}</>;
  if (checking) return <main dir="rtl"><p>בודק חיבור מאובטח…</p></main>;
  if (!session) return <main dir="rtl"><h1>כניסה למערכת תכנון הפרישה</h1>
    <form onSubmit={submit}><label>שם משתמש<input autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} /></label>
      <label>סיסמה<input type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} /></label>
      <button type="submit">כניסה</button></form>{message && <p role="alert">{message}</p>}</main>;
  if (logoutUncertain) return <main dir="rtl"><h1>אימות מצב ההתנתקות</h1>
    {message && <p role="alert">{message}</p>}
    <button type="button" onClick={() => void signOut()}>ניסיון התנתקות נוסף</button>
    <button type="button" onClick={() => void checkAfterFailedLogout()}>בדיקת מצב החיבור</button>
  </main>;
  return <><div dir="rtl"><button type="button" onClick={() => void signOut()}>התנתקות</button></div>{children}</>;
}
