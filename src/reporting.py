"""Write the end-of-day operations report to Excel."""
import pandas as pd


def _autosize(ws):
    for col in ws.columns:
        width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(10, width + 2), 45)


def export_report(path, recon_summary, breaks, exceptions, volume, break_rates):
    summary_rows = [
        ("Trades compared", recon_summary["trades_compared"]),
        ("Matched", recon_summary["matched"]),
        ("Breaks", recon_summary["breaks"]),
        ("Match rate (%)", recon_summary["match_rate_pct"]),
        ("Net notional difference ($)", recon_summary["net_notional_diff"]),
        ("Compliance exceptions", len(exceptions)),
    ]
    summary_rows += [(f"Breaks: {k}", v) for k, v in recon_summary["breaks_by_type"].items()]
    summary_rows += [(f"Exceptions: {k}", v) for k, v in exceptions["rule"].value_counts().items()]

    sheets = {
        "Summary": pd.DataFrame(summary_rows, columns=["Metric", "Value"]),
        "Breaks": breaks,
        "Compliance": exceptions,
        "Volume": volume,
        "Break Rate by Symbol": break_rates,
    }
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            out = df.copy()
            for col in out.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
                out[col] = out[col].astype(str)
            out.to_excel(writer, sheet_name=name, index=False)
            ws = writer.sheets[name]
            ws.freeze_panes = "A2"
            _autosize(ws)
    return path
