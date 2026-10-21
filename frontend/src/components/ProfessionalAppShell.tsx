import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import "./ProfessionalAppShell.css";

type IconName =
  | "clients" | "add" | "file" | "pension" | "grants" | "employment"
  | "income" | "capital" | "sources" | "planning" | "scenario"
  | "readiness" | "fixation" | "results" | "history" | "menu" | "chevron";

const iconPaths: Record<IconName, string> = {
  clients: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75",
  add: "M12 5v14M5 12h14",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 13h8M8 17h8",
  pension: "M3 7h18M5 7v13h14V7M8 3h8M8 12h8M8 16h5",
  grants: "M12 2v20M17 5H9a4 4 0 0 0 0 8h6a4 4 0 0 1 0 8H6",
  employment: "M3 7h18v14H3zM8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18",
  income: "M3 17l6-6 4 4 8-8M15 7h6v6",
  capital: "M3 10l9-7 9 7M5 10v10h14V10M9 20v-6h6v6",
  sources: "M4 4h16v16H4zM8 8h8M8 12h8M8 16h5",
  planning: "M9 11l2 2 4-4M5 3h14v18H5z",
  scenario: "M4 20V9M10 20V4M16 20v-7M22 20v-11M2 20h22",
  readiness: "M4 13l5 5L20 6M3 3h18v18H3z",
  fixation: "M12 3a7 7 0 0 0-7 7c0 5 7 11 7 11s7-6 7-11a7 7 0 0 0-7-7ZM9 10l2 2 4-4",
  results: "M4 4h16v16H4zM8 16v-4M12 16V8M16 16v-6",
  history: "M3 12a9 9 0 1 0 3-6.7M3 3v5h5M12 7v5l4 2",
  menu: "M4 6h16M4 12h16M4 18h16",
  chevron: "M15 18l-6-6 6-6",
};

function ShellIcon({ name }: { name: IconName }) {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={iconPaths[name]} />
    </svg>
  );
}

type MenuItem = {
  label: string;
  icon: IconName;
  segment?: string;
  absolutePath?: string;
  pending?: boolean;
  end?: boolean;
};

const dataMenu: MenuItem[] = [
  { label: "פרטי הלקוח והתיק", icon: "file", segment: "", end: true },
  { label: "התיק הפנסיוני", icon: "pension", segment: "/pension-products" },
  { label: "מענקים היסטוריים", icon: "grants", segment: "/grants" },
  { label: "היסטוריית תעסוקה", icon: "employment", segment: "/employment-history" },
  { label: "מעסיק נוכחי", icon: "employment", pending: true },
  { label: "קצבאות קיימות", icon: "income", pending: true },
  { label: "הכנסות נוספות", icon: "income", pending: true },
  { label: "נכסי הון", icon: "capital", pending: true },
  { label: "מקורות מקצועיים", icon: "sources", segment: "/professional-sources" },
];

const planningMenu: MenuItem[] = [
  { label: "קלט התכנון", icon: "planning", segment: "/planning-input" },
  { label: "תרחישים והשוואה", icon: "scenario", pending: true },
  { label: "מוכנות הכנסה", icon: "readiness", segment: "/retirement-income-readiness" },
  { label: "קיבוע זכויות", icon: "fixation", segment: "/fixation/workspace" },
  { label: "תוצאות פרישה", icon: "results", pending: true },
  { label: "תוצאת קיבוע", icon: "results", segment: "/fixation/result" },
];

const generalMenu: MenuItem[] = [
  { label: "רשימת לקוחות", icon: "clients", absolutePath: "/clients", end: true },
  { label: "פתיחת לקוח חדש", icon: "add", absolutePath: "/clients/new" },
];

const toolMenu: MenuItem[] = [
  { label: "נתוני קיבוע כלליים", icon: "fixation", absolutePath: "/fixation/input" },
  { label: "היסטוריית קיבוע", icon: "history", absolutePath: "/fixation/history" },
];

function routeClientId(path: string): number | null {
  const match = path.match(/^\/clients\/(\d+)(?:\/|$)/);
  if (!match) return null;
  const id = Number(match[1]);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

function currentScreenLabel(path: string): string {
  if (path === "/clients/new") return "פתיחת לקוח חדש";
  if (path === "/clients") return "רשימת לקוחות";
  if (path.startsWith("/fixation/")) return toolMenu.find(item => item.absolutePath === path)?.label ?? "כלי קיבוע";
  const id = routeClientId(path);
  if (id === null) return "סביבת עבודה";
  const suffix = path.slice(`/clients/${id}`.length);
  const entry = [...dataMenu, ...planningMenu].find(item => !item.pending && item.segment === suffix);
  return entry?.label ?? "תיק לקוח";
}

function SidebarGroup({
  label, items, clientId, onNavigate,
}: {
  label: string;
  items: MenuItem[];
  clientId: number | null;
  onNavigate: () => void;
}) {
  return (
    <div className="professional-shell__nav-group">
      <p className="professional-shell__nav-heading">{label}</p>
      <ul className="professional-shell__nav-list">
        {items.map(item => {
          const path = item.absolutePath ?? (clientId !== null && item.segment !== undefined
            ? `/clients/${clientId}${item.segment}` : null);
          const inactiveReason = item.pending ? "טרם זמין" : "בחר תיק";
          return (
            <li key={item.label}>
              {path !== null && !item.pending ? (
                <NavLink to={path} end={item.end ?? true} onClick={onNavigate}
                  className={({ isActive }) => `professional-shell__nav-link${isActive ? " is-active" : ""}`}>
                  <ShellIcon name={item.icon} />
                  <span>{item.label}</span>
                  <ShellIcon name="chevron" />
                </NavLink>
              ) : (
                <span className="professional-shell__nav-link is-unavailable" aria-disabled="true">
                  <ShellIcon name={item.icon} />
                  <span>{item.label}</span>
                  <small>{inactiveReason}</small>
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Presentation-only shell. It never fetches or mutates case data, creates a
 * scenario, or infers professional readiness. Every live destination is a
 * route implemented by AppRoutes. Unimplemented V1 areas are clearly marked.
 */
export function ProfessionalAppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const clientId = routeClientId(location.pathname);
  const pageTitle = currentScreenLabel(location.pathname);

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  return (
    <div dir="rtl" lang="he" className="professional-shell">
      <a className="professional-shell__skip" href="#professional-main">דלג לתוכן הראשי</a>
      <header className="professional-shell__topbar">
        <div className="professional-shell__brand" dir="rtl">
          <div className="professional-shell__brand-mark" aria-hidden="true">ב</div>
          <div className="professional-shell__brand-copy" dir="rtl">
            <h1>מערכת תכנון פרישה</h1>
            <span>סביבת עבודה מקצועית · V2</span>
          </div>
        </div>
        <div className="professional-shell__top-actions">
          {clientId !== null ? (
            <Link className="professional-shell__top-context" to={`/clients/${clientId}`}>
              <ShellIcon name="file" />
              <span>תיק לקוח <bdi>#{clientId}</bdi></span>
            </Link>
          ) : <span className="professional-shell__top-context is-neutral">ניהול תיקים</span>}
          <button type="button" className="professional-shell__menu-toggle"
            aria-label={menuOpen ? "סגירת תפריט" : "פתיחת תפריט"}
            aria-controls="professional-navigation"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(current => !current)}>
            <ShellIcon name="menu" />
          </button>
        </div>
      </header>

      <div className="professional-shell__layout">
        {menuOpen && <button type="button" className="professional-shell__scrim"
          aria-label="סגירת תפריט ניווט" onClick={() => setMenuOpen(false)} />}
        <aside id="professional-navigation"
          className={`professional-shell__sidebar${menuOpen ? " is-open" : ""}`}
          aria-label="תפריט עבודה מקצועי">
          <div className="professional-shell__sidebar-head">
            {clientId !== null ? (
              <>
                <span className="professional-shell__eyebrow">תיק פעיל</span>
                <strong>לקוח <bdi>#{clientId}</bdi></strong>
                <Link to="/clients" onClick={() => setMenuOpen(false)}>החלפת לקוח</Link>
              </>
            ) : (
              <>
                <span className="professional-shell__eyebrow">סביבת העבודה</span>
                <strong>בחירת תיק לקוח</strong>
                <span className="professional-shell__sidebar-note">יש לפתוח תיק כדי לגשת למסכים המקצועיים.</span>
              </>
            )}
          </div>
          <nav aria-label="ניווט מערכת ותיק">
            <SidebarGroup label="ניהול לקוחות" items={generalMenu} clientId={clientId} onNavigate={() => setMenuOpen(false)} />
            <SidebarGroup label="נתוני לקוח ומקורות" items={dataMenu} clientId={clientId} onNavigate={() => setMenuOpen(false)} />
            <SidebarGroup label="תכנון, חלופות ותוצאות" items={planningMenu} clientId={clientId} onNavigate={() => setMenuOpen(false)} />
            <SidebarGroup label="כלי מערכת קיימים" items={toolMenu} clientId={clientId} onNavigate={() => setMenuOpen(false)} />
          </nav>
          <p className="professional-shell__sidebar-foot">הנתונים נשמרים במסכים המקוריים. הסרגל אינו יוצר תרחישים או משנה יתרות.</p>
        </aside>

        <div className="professional-shell__content">
          <div className="professional-shell__context-row">
            <nav aria-label="מיקום נוכחי" className="professional-shell__breadcrumb">
              <Link to="/clients">לקוחות</Link>
              {clientId !== null && <>
                <span aria-hidden="true">/</span>
                <Link to={`/clients/${clientId}`}>תיק <bdi>#{clientId}</bdi></Link>
              </>}
              <span aria-hidden="true">/</span>
              <span aria-current="page">{pageTitle}</span>
            </nav>
            <span className="professional-shell__context-tag">סביבת מתכנן</span>
          </div>
          <main id="professional-main" className="professional-shell__main" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
