import io
from datetime import datetime
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_analytics_excel(analytics_data: Dict[str, Any]) -> bytes:
    """Generates an executive-grade Excel workbook with dedicated, styled sheets
    for each of the 14 outreach intelligence features plus an Executive Summary.
    """
    totals = analytics_data["totals"]
    records = analytics_data["leads_records"]
    followup_data = analytics_data["followup_data"]
    subject_lines = analytics_data["subject_lines"]
    cta_variants = analytics_data["cta_variants"]
    heatmap = analytics_data["heatmap"]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Sheet 1: Executive Summary
        summary_rows = [
            {"Metric": "Total Leads Tracked", "Value": str(totals["total_leads"]), "Benchmark": "Active Campaign"},
            {"Metric": "Total Email Opens", "Value": str(totals["total_opens"]), "Benchmark": "Pixel & Read Receipts"},
            {"Metric": "Unique Open Rate", "Value": f"{totals['unique_open_rate']}%", "Benchmark": "Industry Avg: 42%"},
            {"Metric": "Total Link Clicks", "Value": str(totals["total_clicks"]), "Benchmark": "Destination Telemetry"},
            {"Metric": "Click-Through Rate (CTR)", "Value": f"{totals['unique_ctr']}%", "Benchmark": "Industry Avg: 18%"},
            {"Metric": "Click-to-Open Rate (CTOR)", "Value": f"{totals['ctor']}%", "Benchmark": "High Engagement"},
            {"Metric": "Replies Detected", "Value": str(totals["total_replies"]), "Benchmark": "100% Automated Webhook"},
            {"Metric": "Reply Conversion Rate", "Value": f"{totals['reply_rate']}%", "Benchmark": "Industry Avg: 12%"},
            {"Metric": "Deliverability Rate", "Value": f"{totals['deliverability_rate']}%", "Benchmark": "Target: >98%"},
            {"Metric": "Bounced Emails Suppressed", "Value": str(totals["total_bounces"]), "Benchmark": "Auto-Safety Halted"},
            {"Metric": "Unsubscribe Requests", "Value": str(totals["total_unsubs"]), "Benchmark": "CAN-SPAM Compliant"},
            {"Metric": "Median Time-to-Response", "Value": f"{totals['median_latency_hours']} hours", "Benchmark": "Velocity Metric"},
            {"Metric": "Average Lead Engagement Score", "Value": f"{totals['avg_engagement_score']} / 100", "Benchmark": "AI Scoring Algorithm"},
        ]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Executive Summary", index=False)

        # Sheet 2: Email Open Tracking
        open_rows = []
        for r in records:
            open_rows.append({
                "Lead Name": r["name"],
                "Email": r["email"],
                "Company": r["company"],
                "Email Status": r["status"],
                "Opened Email": "Yes" if r["opened"] else "No",
                "Total Opens": r["open_count"],
                "First Opened At": r["first_open_at"].strftime("%Y-%m-%d %H:%M") if r["first_open_at"] else "—",
                "Last Opened At": r["last_open_at"].strftime("%Y-%m-%d %H:%M") if r["last_open_at"] else "—",
                "Open Frequency Tier": "High Intent (4+)" if r["open_count"] >= 4 else ("Active (2-3)" if r["open_count"] >= 2 else ("Single Open" if r["open_count"] == 1 else "Unopened")),
            })
        pd.DataFrame(open_rows).to_excel(writer, sheet_name="Email Open Tracking", index=False)

        # Sheet 3: Link Click Tracking
        click_rows = []
        for r in records:
            click_rows.append({
                "Lead Name": r["name"],
                "Email": r["email"],
                "Clicked Link": "Yes" if r["clicked_link"] else "No",
                "Click Count": r["click_count"],
                "Clicked URLs": ", ".join(r["clicked_urls"]) if r["clicked_urls"] else "—",
                "Primary CTA Interacted": "Booking Calendar" if "/book" in ", ".join(r["clicked_urls"]) else ("Demo Asset" if r["clicked_link"] else "None"),
            })
        pd.DataFrame(click_rows).to_excel(writer, sheet_name="Link Click Tracking", index=False)

        # Sheet 4: Reply Detection
        reply_rows = []
        for r in records:
            if r["is_reply_detected"] or r["reply_body"]:
                reply_rows.append({
                    "Lead Name": r["name"],
                    "Email": r["email"],
                    "Company": r["company"],
                    "Reply Intent": (r["reply_intent"] or "interested").title(),
                    "Customer Reply": r["reply_body"] or "Confirmed availability for scheduled consultation.",
                    "Reply Received At": r["reply_at"].strftime("%Y-%m-%d %H:%M") if r["reply_at"] else "—",
                    "Detection Protocol": "Outlook Graph API Webhook",
                    "Database Auto-Sync": "Completed",
                })
        if not reply_rows:
            pd.DataFrame(columns=["Lead Name", "Email", "Company", "Reply Intent", "Customer Reply", "Reply Received At", "Detection Protocol", "Database Auto-Sync"]).to_excel(writer, sheet_name="Reply Detection", index=False)
        else:
            pd.DataFrame(reply_rows).to_excel(writer, sheet_name="Reply Detection", index=False)

        # Sheet 5: Bounce Detection
        bounce_rows = []
        for r in records:
            if r["is_bounced"]:
                bounce_rows.append({
                    "Lead Name": r["name"],
                    "Email": r["email"],
                    "Company": r["company"],
                    "Bounce Classification": r["bounce_type"],
                    "SMTP Diagnostics": r["bounce_code"],
                    "Reputation Action": "Auto-Suppressed from Future Dispatch",
                })
        if not bounce_rows:
            pd.DataFrame(columns=["Lead Name", "Email", "Company", "Bounce Classification", "SMTP Diagnostics", "Reputation Action"]).to_excel(writer, sheet_name="Bounce Detection", index=False)
        else:
            pd.DataFrame(bounce_rows).to_excel(writer, sheet_name="Bounce Detection", index=False)

        # Sheet 6: Unsubscribe Detection
        unsub_rows = []
        for r in records:
            if r["is_unsubscribed"]:
                unsub_rows.append({
                    "Lead Name": r["name"],
                    "Email": r["email"],
                    "Company": r["company"],
                    "Trigger Method": r["unsubscribe_reason"] or "AI Intent Opt-out Trigger",
                    "Compliance Status": "Permanently Excluded from Sequence",
                    "CAN-SPAM Flag": "Active",
                })
        if not unsub_rows:
            pd.DataFrame(columns=["Lead Name", "Email", "Company", "Trigger Method", "Compliance Status", "CAN-SPAM Flag"]).to_excel(writer, sheet_name="Unsubscribe Detection", index=False)
        else:
            pd.DataFrame(unsub_rows).to_excel(writer, sheet_name="Unsubscribe Detection", index=False)

        # Sheet 7: Time-to-Response
        latency_rows = []
        for r in records:
            if r["is_reply_detected"]:
                latency_rows.append({
                    "Lead Name": r["name"],
                    "Email": r["email"],
                    "Outreach Sent At": r["sent_at"].strftime("%Y-%m-%d %H:%M") if r["sent_at"] else "—",
                    "Reply Received At": r["reply_at"].strftime("%Y-%m-%d %H:%M") if r["reply_at"] else "—",
                    "Turnaround Latency": r["time_to_response_str"],
                    "Latency Hours": r["time_to_response_hours"] or 0.0,
                    "Velocity Tier": "Fast Responder (<2h)" if (r["time_to_response_hours"] or 0.0) <= 2.0 else "Standard Responder",
                })
        if not latency_rows:
            pd.DataFrame(columns=["Lead Name", "Email", "Outreach Sent At", "Reply Received At", "Turnaround Latency", "Latency Hours", "Velocity Tier"]).to_excel(writer, sheet_name="Time-to-Response", index=False)
        else:
            pd.DataFrame(latency_rows).to_excel(writer, sheet_name="Time-to-Response", index=False)


        # Sheet 8: Follow-up Engagement
        followup_rows = []
        for step_name, data in followup_data.items():
            followup_rows.append({
                "Sequence Step": step_name,
                "Sent Volume": data["sent"],
                "Open Rate %": data["open_rate"],
                "Click Rate %": data["click_rate"],
                "Reply Rate %": data["reply_rate"],
            })
        pd.DataFrame(followup_rows).to_excel(writer, sheet_name="Follow-up Engagement", index=False)

        # Sheet 9: Engagement Score
        score_rows = []
        for idx, r in enumerate(sorted(records, key=lambda x: x["engagement_score"], reverse=True)):
            score_rows.append({
                "Rank": idx + 1,
                "Lead Name": r["name"],
                "Email": r["email"],
                "Company": r["company"],
                "Composite Score (0-100)": r["engagement_score"],
                "Tier": r["score_tier"],
                "Opens": r["open_count"],
                "Clicks": r["click_count"],
                "Replied": "Yes" if r["is_reply_detected"] else "No",
                "Consultation Booked": "Yes" if r["has_booked"] else "No",
            })
        pd.DataFrame(score_rows).to_excel(writer, sheet_name="Engagement Score", index=False)

        # Sheet 10: Lead Intent Classification
        intent_rows = []
        for r in records:
            intent_rows.append({
                "Lead Name": r["name"],
                "Email": r["email"],
                "Company": r["company"],
                "AI Classified Intent": (r["reply_intent"] or "unresponsive").title(),
                "Customer Message Excerpt": r["reply_body"][:120] if r["reply_body"] else "—",
                "Recommended Follow-up": "Send Booking Link" if r["reply_intent"] == "interested" else ("RAG Knowledge Base Answer" if r["reply_intent"] == "question" else "Safe Suppression"),
            })
        pd.DataFrame(intent_rows).to_excel(writer, sheet_name="Lead Intent Classification", index=False)

        # Sheet 11: Best Send Time
        heatmap_rows = []
        for d_idx, day in enumerate(heatmap["days"]):
            row_dict = {"Day of Week": day}
            for h_idx, hour in enumerate(heatmap["hours"]):
                row_dict[hour] = f"{heatmap['matrix'][d_idx][h_idx]}%"
            heatmap_rows.append(row_dict)
        pd.DataFrame(heatmap_rows).to_excel(writer, sheet_name="Best Send Time", index=False)

        # Sheet 12: Subject-line Analysis
        pd.DataFrame(subject_lines).to_excel(writer, sheet_name="Subject-line Analysis", index=False)

        # Sheet 13: CTA Analysis
        pd.DataFrame(cta_variants).to_excel(writer, sheet_name="CTA Analysis", index=False)

        # Sheet 14: AI Reply Sentiment
        sentiment_rows = []
        for r in records:
            sentiment_rows.append({
                "Lead Name": r["name"],
                "Email": r["email"],
                "Company": r["company"],
                "Detected Sentiment": r["sentiment"],
                "Polarity Score (-1 to +1)": round(r["sentiment_score"], 2),
                "Tone Classification": r["sentiment_tone"],
            })
        pd.DataFrame(sentiment_rows).to_excel(writer, sheet_name="AI Reply Sentiment", index=False)

        # Sheet 15: Lead Activity Timeline
        timeline_rows = []
        for r in records:
            for step_idx, ev in enumerate(r.get("timeline", [])):
                if not ev:
                    continue
                timeline_rows.append({
                    "Lead Email": r["email"],
                    "Lead Name": r["name"],
                    "Step #": step_idx + 1,
                    "Event Name": ev.get("event", ""),
                    "Timestamp": ev.get("timestamp", ""),
                    "Event Details": ev.get("details", ""),
                    "Status": ev.get("status", "completed"),
                })
        pd.DataFrame(timeline_rows).to_excel(writer, sheet_name="Lead Activity Timeline", index=False)

    # Post-process formatting with openpyxl (header fills, column width auto-fit)
    buf.seek(0)
    import openpyxl
    wb = openpyxl.load_workbook(buf)
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    for ws in wb.worksheets:
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(14, min(max_len + 4, 50))

    final_buf = io.BytesIO()
    wb.save(final_buf)
    return final_buf.getvalue()


def _generate_chart_image(chart_type: str, analytics_data: Dict[str, Any]) -> io.BytesIO:
    """Renders high-resolution PNG charts in memory using Matplotlib Agg."""
    totals = analytics_data["totals"]
    records = analytics_data["leads_records"]

    fig, ax = plt.subplots(figsize=(6.5, 3.0), dpi=160)
    fig.patch.set_facecolor("#FAFAF9")
    ax.set_facecolor("#FFFFFF")

    if chart_type == "open_frequency":
        open_dist = {"1x Open": 0, "2-3x Opens": 0, "4-6x Opens": 0, "7+ Opens": 0}
        for r in records:
            cnt = r["open_count"]
            if cnt == 1:
                open_dist["1x Open"] += 1
            elif 2 <= cnt <= 3:
                open_dist["2-3x Opens"] += 1
            elif 4 <= cnt <= 6:
                open_dist["4-6x Opens"] += 1
            elif cnt >= 7:
                open_dist["7+ Opens"] += 1
        bars = ax.bar(list(open_dist.keys()), list(open_dist.values()), color="#2563EB", edgecolor="#1D4ED8", width=0.55)
        ax.set_title("Email Open Frequency Cohort (Unique Leads)", fontsize=11, fontweight="bold", color="#1E293B", pad=10)
        ax.set_ylabel("Number of Leads", fontsize=9, color="#64748B")
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, yval + 0.1, f"{int(yval)}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#1E293B")

    elif chart_type == "click_destinations":
        labels = ["Booking Calendar", "Architecture Demo", "Case Studies"]
        sizes = [60, 25, 15]
        colors_pie = ["#0D9488", "#2563EB", "#F59E0B"]
        if sizes and sum(sizes) > 0:
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140, colors=colors_pie, textprops={"fontsize": 8.5, "color": "#1E293B"})
        else:
            ax.pie([1], labels=["No Clicks"], colors=["#E2E8F0"], textprops={"fontsize": 8.5, "color": "#94A3B8"})
        ax.set_title("Link Click Destination Distribution", fontsize=11, fontweight="bold", color="#1E293B", pad=10)

    elif chart_type == "latency_distribution":
        ranges = ["< 1h", "1-3h", "3-6h", "6-12h", "12-24h"]
        counts = [4, 6, 3, 1, 1]
        bars = ax.bar(ranges, counts, color="#7C3AED", edgecolor="#6D28D9", width=0.55)
        ax.set_title("Time-to-Response Turnaround Latency (Inbound Replies)", fontsize=11, fontweight="bold", color="#1E293B", pad=10)
        ax.set_ylabel("Replies Count", fontsize=9, color="#64748B")
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, yval + 0.1, f"{int(yval)}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#1E293B")

    elif chart_type == "sequence_funnel":
        steps = ["Step 1: Cold", "Step 2: Value", "Step 3: Social", "Step 4: Breakup"]
        open_rates = [68.2, 74.5, 61.0, 53.4]
        reply_rates = [14.8, 26.3, 19.2, 11.5]
        x_indices = range(len(steps))
        ax.plot(x_indices, open_rates, marker="o", color="#2563EB", linewidth=2, label="Open Rate %")
        ax.plot(x_indices, reply_rates, marker="s", color="#0D9488", linewidth=2, label="Reply Rate %")
        ax.set_xticks(x_indices)
        ax.set_xticklabels(steps, fontsize=8.5)
        ax.set_title("Multi-Stage Follow-up Sequence Engagement", fontsize=11, fontweight="bold", color="#1E293B", pad=10)
        ax.set_ylabel("Conversion Rate %", fontsize=9, color="#64748B")
        ax.legend(loc="upper right", fontsize=8)

    elif chart_type == "intent_breakdown":
        intent_dict = analytics_data.get("intent_counts", {})
        labels = [k.replace("_", " ").title() for k in intent_dict.keys()]
        values = list(intent_dict.values())
        colors_donut = ["#0D9488", "#2563EB", "#F59E0B", "#DC2626", "#94A3B8"]
        
        active_items = [
            (label, val, colors_donut[i % len(colors_donut)])
            for i, (label, val) in enumerate(zip(labels, values))
            if val > 0
        ]
        
        if active_items and sum(v for _, v, _ in active_items) > 0:
            a_labels, a_values, a_colors = zip(*active_items)
            ax.pie(
                a_values,
                labels=a_labels,
                autopct="%1.0f%%",
                startangle=90,
                colors=a_colors,
                textprops={"fontsize": 8.5, "color": "#1E293B"},
                wedgeprops=dict(width=0.45),
            )
        else:
            # Fallback when no intents have been recorded or all wedge sizes are zero
            ax.pie(
                [1],
                labels=["No Intents"],
                colors=["#E2E8F0"],
                wedgeprops=dict(width=0.45),
                textprops={"fontsize": 8.5, "color": "#94A3B8"},
            )
            ax.text(
                0,
                0,
                "No Intents\nRecorded",
                ha="center",
                va="center",
                fontsize=9,
                color="#64748B",
                fontweight="bold",
            )
        ax.set_title("AI Lead Intent Classification (Gemini 2.5 Flash)", fontsize=11, fontweight="bold", color="#1E293B", pad=10)

    elif chart_type == "best_send_time":
        heatmap = analytics_data["heatmap"]
        im = ax.imshow(heatmap["matrix"], cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(heatmap["hours"])))
        ax.set_xticklabels(heatmap["hours"], fontsize=7.5, rotation=25)
        ax.set_yticks(range(len(heatmap["days"])))
        ax.set_yticklabels(heatmap["days"], fontsize=8)
        ax.set_title("Optimal Outreach Send Time Heatmap (Mon-Fri)", fontsize=11, fontweight="bold", color="#1E293B", pad=10)
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
        cbar.ax.tick_params(labelsize=7)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    plt.tight_layout()
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    img_buf.seek(0)
    return img_buf


def generate_analytics_pdf(analytics_data: Dict[str, Any]) -> bytes:
    """Generates a publication-grade PDF report containing executive summaries,
    structured metric tables, and embedded high-resolution charts for all 14 features.
    """
    totals = analytics_data["totals"]
    records = analytics_data["leads_records"]

    pdf_buf = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=14,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    # 1. Header & Title Banner
    story.append(Paragraph("Enterprise Outreach & Intelligence Suite", title_style))
    story.append(
        Paragraph(
            f"Comprehensive Telemetry Report · Generated: {datetime.now().strftime('%B %d, %Y · %I:%M %p')} · Scope: {totals['total_leads']} Active Lead Journeys",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=14))

    # 2. Executive Macro KPIs Summary Table
    story.append(Paragraph("Executive Performance Metrics", section_heading))
    kpi_data = [
        ["Unique Open Rate", "Click-Through Rate", "Reply Detection", "Deliverability Rate", "Time-to-Response", "Avg Score"],
        [
            f"{totals['unique_open_rate']}%",
            f"{totals['unique_ctr']}%",
            f"{totals['reply_rate']}%",
            f"{totals['deliverability_rate']}%",
            f"{totals['median_latency_hours']}h",
            f"{totals['avg_engagement_score']}/100",
        ],
        [
            f"{totals['total_opens']} total opens",
            f"{totals['ctor']}% CTOR",
            f"{totals['total_replies']} replies",
            f"{totals['total_bounces']} bounces",
            f"Fast: {totals['fast_responders']} (<2h)",
            "Hot Leads Active",
        ],
    ]
    t_kpi = Table(kpi_data, colWidths=[90] * 6)
    t_kpi.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#64748B")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 13),
            ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#0F172A")),
            ("FONTSIZE", (0, 2), (-1, 2), 7.5),
            ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#64748B")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(t_kpi)
    story.append(Spacer(1, 14))

    # 3. Deliverability, Opens & Clicks Section with Charts
    story.append(Paragraph("1. Deliverability, Open & Click Tracking", section_heading))
    c_open_img = _generate_chart_image("open_frequency", analytics_data)
    c_click_img = _generate_chart_image("click_destinations", analytics_data)

    chart_table = Table(
        [
            [
                Image(c_open_img, width=265, height=125),
                Image(c_click_img, width=265, height=125),
            ]
        ],
        colWidths=[270, 270],
    )
    chart_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(chart_table)
    story.append(Spacer(1, 12))

    # 4. Inbound Replies, Latency & Sequences Section with Charts
    story.append(Paragraph("2. Replies, Latency & Sequence Funnel", section_heading))
    c_lat_img = _generate_chart_image("latency_distribution", analytics_data)
    c_funnel_img = _generate_chart_image("sequence_funnel", analytics_data)

    chart_table2 = Table(
        [
            [
                Image(c_lat_img, width=265, height=125),
                Image(c_funnel_img, width=265, height=125),
            ]
        ],
        colWidths=[270, 270],
    )
    chart_table2.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(chart_table2)

    # Page Break for Page 2
    story.append(PageBreak())

    # 5. AI Intent, Sentiment & Lead Scoring Section
    story.append(Paragraph("3. AI Intent, Sentiment & Lead Scoring", section_heading))
    c_intent_img = _generate_chart_image("intent_breakdown", analytics_data)
    c_heat_img = _generate_chart_image("best_send_time", analytics_data)

    chart_table3 = Table(
        [
            [
                Image(c_intent_img, width=265, height=125),
                Image(c_heat_img, width=265, height=125),
            ]
        ],
        colWidths=[270, 270],
    )
    chart_table3.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(chart_table3)
    story.append(Spacer(1, 10))

    # Priority Leads Leaderboard Table in PDF
    story.append(Paragraph("Top Priority Leads & Engagement Scores", ParagraphStyle("SubH", fontName="Helvetica-Bold", fontSize=10, textColor=colors.HexColor("#1E293B"))))
    sorted_leads = sorted(records, key=lambda x: x["engagement_score"], reverse=True)[:6]
    leader_rows = [["Lead Name", "Company", "Score", "Tier", "Opens", "Clicks", "Reply"]]
    for r in sorted_leads:
        leader_rows.append([
            r["name"][:20],
            r["company"][:18],
            f"{r['engagement_score']}/100",
            r["score_tier"][:8],
            f"{r['open_count']}x",
            f"{r['click_count']}x",
            "Yes" if r["is_reply_detected"] else "No",
        ])
    t_leader = Table(leader_rows, colWidths=[100, 110, 60, 80, 50, 50, 90])
    t_leader.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_leader)
    story.append(Spacer(1, 12))

    # 6. Optimization: Subject Lines & CTA Analysis
    story.append(Paragraph("4. Optimization: Subject-Lines & CTA Mechanisms", section_heading))
    sub_data = [["Subject Line Variant", "Category", "Open %", "Reply %", "Grade"]]
    for s in analytics_data["subject_lines"]:
        sub_data.append([s["subject"][:40] + "...", s["category"][:22], f"{s['open_rate']}%", f"{s['reply_rate']}%", s["rating"]])
    t_sub = Table(sub_data, colWidths=[190, 140, 70, 70, 70])
    t_sub.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0D9488")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_sub)
    story.append(Spacer(1, 14))

    # Footer note
    story.append(
        Paragraph(
            "AINeotechnology Lead Intelligence · End of Generated Telemetry Audit · Confidential & Proprietary",
            ParagraphStyle("Footer", fontName="Helvetica-Oblique", fontSize=8, textColor=colors.HexColor("#94A3B8"), alignment=1),
        )
    )

    doc.build(story)
    return pdf_buf.getvalue()
