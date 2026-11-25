"""Hebrew RTL print-ready PDF for a read-only M12 draft snapshot."""
from io import BytesIO
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, CondPageBreak

_FONT = "M12DejaVu"
_FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

_LABELS = {
    "not_currently_working": "אינו עובד כעת", "salaried_employee": "שכיר",
    "self_employed": "עצמאי", "salaried_and_self_employed": "שכיר ועצמאי",
    "pension_fund": "קרן פנסיה", "provident_fund": "קופת גמל",
    "insurance_policy": "פוליסת ביטוח", "bank deposit": "פיקדון בנקאי",
    "investment account": "חשבון השקעות", "real estate": "מקרקעין",
    "private asset": "נכס פרטי", "monthly": "חודשי", "quarterly": "רבעוני",
    "annual": "שנתי", "gross": "ברוטו", "net": "נטו",
    "verified": "אומת", "unverified": "טרם אומת", "partially verified": "אומת חלקית",
    "collected - not yet reviewed": "נאסף וטרם נבדק", "missing": "חסר",
    "open": "פתוח", "resolved": "נפתר", "needs_revalidation": "נדרשת בדיקה מחדש",
    "draft": "טיוטה", "pension": "קצבה", "capital_asset": "הון",
}

def _he(value):
    if value is None or value == "":
        return "לא נמסר"
    return _LABELS.get(str(value), str(value))

def _money(value):
    """Format existing source amounts without converting absence to zero."""
    if value is None or value == "":
        return "לא נמסר"
    try:
        n = Decimal(str(value))
        return f"{n:,.2f} ₪" if n.is_finite() else "נתון לא תקין"
    except (InvalidOperation, ValueError):
        return "נתון לא תקין"

def _p(value, font_size=9, keep_next=False):
    text = "לא נמסר" if value is None or value == "" else str(value)
    return Paragraph(escape(get_display(text)), ParagraphStyle(
        "rtl", fontName=_FONT, fontSize=font_size, leading=font_size*1.65,
        alignment=TA_RIGHT, textColor=colors.HexColor("#273849"), spaceAfter=3,
        keepWithNext=keep_next))

def render_pdf(doc: dict) -> bytes:
    if _FONT not in pdfmetrics.getRegisteredFontNames():
        if not _FONT_PATH.is_file(): raise RuntimeError("M12_FONT_NOT_AVAILABLE")
        pdfmetrics.registerFont(TTFont(_FONT, str(_FONT_PATH)))
    stream = BytesIO()
    layout = SimpleDocTemplate(stream, pagesize=A4, rightMargin=36, leftMargin=36,
                               topMargin=37, bottomMargin=37, title="טיוטת תכנון פרישה")
    story = []
    def section(label):
        story.append(CondPageBreak(95))
        story.append(Spacer(1, 6))
        story.append(_p(label, 12))
    def table(headers, rows):
        if not rows: rows = [["אין נתונים"] + [""]*(len(headers)-1)]
        body = [[_p(value, 8) for value in reversed(headers)]]
        body += [[_p(value, 8) for value in reversed(row)] for row in rows]
        item = Table(body, colWidths=[(A4[0]-72)/len(headers)]*len(headers),
                     hAlign="RIGHT", repeatRows=1, splitByRow=1)
        item.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e5edf4")),
            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#bdc7d0")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story.append(item)
    story += [_p("טיוטת תכנון פרישה",19),
              _p("מסמך עבודה בלבד. אין לראות בו תכנון סופי או אישור תקינות חישובים."),
              _p("מועד הפקה UTC: "+doc["generated_at"][:19].replace("T"," "))]
    client=doc["client"]
    retirement = ("תאריך "+client["planned_retirement_date"] if client["planned_retirement_date"]
                  else "גיל "+str(client["planned_retirement_age"])
                  if client["planned_retirement_age"] is not None else "לא נמסר")
    section("פרטי הלקוח")
    table(["שם","מצב תעסוקה","פרישה מתוכננת"],
          [[client["name"],_he(client.get("employment_status")),retirement]])
    section("מוצרים פנסיוניים - נתוני מקור")
    table(["מוצר","גוף מנהל","סוג","יתרה מדווחת ₪","מועד נתונים","אימות"],
          [[p["name"],p["provider"],_he(p["type"]),_money(p["reported_total"]),p["statement_date"],_he(p["verification"])]
           for p in doc["pension_products"]])
    section("נכסי הון")
    table(["נכס","סוג","שווי ידוע ₪","מועד נתונים","אימות"],
          [[a["name"],_he(a["category"]),_money(a["value"]),a["value_date"],_he(a["verification"])]
           for a in doc["capital_assets"]])
    section("הכנסות והוצאות מדווחות (ללא תחזית)")
    table(["סוג","תיאור","סכום ₪","תדירות","אימות"],
          [[kind,x["name"],_money(x["amount"]),_he(x["frequency"]),_he(x["verification"])]
           for kind,items in (("הכנסה",doc["incomes"]),("הוצאה",doc["expenses"])) for x in items])
    section("חלופה מועדפת")
    preferred=doc["preferred"]
    if preferred:
        story.append(_p(preferred["name"]+(" - נדרשת בדיקה מחדש" if preferred["outdated"] else "")))
        story.append(_p("נימוק מקצועי: "+(preferred["rationale"] or "לא נרשם")))
    else: story.append(_p("לא נבחרה חלופה מועדפת."))
    section("חלופות והחלטות")
    for scenario in doc["scenarios"]:
        story.append(_p(scenario["name"]+(" (מועדפת)" if scenario["preferred"] else "")
                        +(" - מחייבת אימות" if scenario["status"]=="needs_revalidation" else "")))
        table(["רכיב","החלטה","סכום שהוזן ₪","מצב"],
              [[d["component"],_he(d["action"]),
                _money(d["declared_amount"]),_he(d["validation_state"])] for d in scenario["decisions"]])
    if not doc["scenarios"]: story.append(_p("אין חלופות פעילות."))
    section("הנחות המתכנן")
    for a in doc["assumptions"]: story.append(_p(a["title"]+": "+a["value"]))
    if not doc["assumptions"]: story.append(_p("לא תועדו הנחות."))
    section("מידע חסר")
    for m in doc["missing_information"]: story.append(_p(m["label"]+" - "+_he(m["status"])))
    if not doc["missing_information"]: story.append(_p("לא נרשם מידע חסר; אין בכך אישור לשלמות התיק."))
    section("אזהרות")
    for warning in doc["warnings"]: story.append(_p("• "+warning))
    story.append(_p("לא חושבו בדוח קצבאות, מס, פטורים, תזרים או תשואות.",8))
    layout.build(story)
    pdf=stream.getvalue()
    if not pdf.startswith(b"%PDF") or len(pdf)<600: raise RuntimeError("M12_PDF_INVALID")
    return pdf
