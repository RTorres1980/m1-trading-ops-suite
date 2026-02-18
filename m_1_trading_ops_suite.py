import os
import zipfile

# Define the folder structure and sample files
repo_name = 'm1-trading-ops-suite'
file_structure = {
    'README.md': '# M1 Trading Operations Suite\n\nThis repository simulates trading operations for M1 Finance.\n',
    'requirements.txt': 'pandas\nnumpy\nsqlalchemy\nopenpyxl\nstreamlit\nmatplotlib\njupyter\npytest\n',
    '.gitignore': '__pycache__/\n*.pyc\n.env\noutput/\n.ipynb_checkpoints/\n',
    'LICENSE': 'MIT License\n',
    'data/internal_trades.csv': 'TradeID,Account,Symbol,Quantity,Price\n1,ACC1,AAPL,100,150.0\n',
    'data/broker_trades.csv': 'TradeID,Account,Symbol,Quantity,Price\n1,ACC1,AAPL,100,150.0\n',
    'data/sample_positions.csv': 'Account,Symbol,Quantity\nACC1,AAPL,100\n',
    'sql/schema.sql': 'CREATE TABLE trades (TradeID INT PRIMARY KEY, Account VARCHAR(50), Symbol VARCHAR(10), Quantity INT, Price DECIMAL(10,2), TradeDate DATE);\n',
    'sql/queries/daily_reconciliation.sql': '-- Sample SQL query for reconciliation\nSELECT * FROM trades;\n',
    'sql/queries/compliance_checks.sql': '-- Sample compliance check\nSELECT * FROM trades WHERE Quantity <= 0;\n',
    'src/__init__.py': '',
    'src/main.py': 'print("M1 Trading Ops Suite")\n',
    'src/ingest.py': 'import pandas as pd\ndef load_csv(file):\n    return pd.read_csv(file)\n',
    'src/reconcile.py': 'import pandas as pd\ndef reconcile_trades(internal_file, broker_file):\n    internal = pd.read_csv(internal_file)\n    broker = pd.read_csv(broker_file)\n    merged = internal.merge(broker, on=["TradeID"], how="outer", suffixes=("_internal","_broker"))\n    merged["Break"] = merged["Quantity_internal"] != merged["Quantity_broker"]\n    return merged\n',
    'src/compliance.py': 'def check_compliance(df):\n    return df[df["Quantity_internal"] <= 0]\n',
    'src/analytics.py': 'def daily_metrics(df):\n    return df.groupby("Symbol").sum()[["Quantity_internal"]]\n',
    'src/reporting.py': 'import pandas as pd\ndef export_report(df, file):\n    df.to_excel(file, index=False)\n',
    'src/db.py': 'from sqlalchemy import create_engine\nengine = create_engine("sqlite:///trades.db")\n',
    'src/utils.py': 'def helper():\n    return True\n',
    'src/dashboard.py': 'import streamlit as st\nimport pandas as pd\ndf = pd.read_csv("../data/internal_trades.csv")\nst.title("M1 Trading Ops Dashboard")\nst.dataframe(df)\n',
    'notebooks/trade_analysis_demo.ipynb': '{}',
    'notebooks/reconciliation_visualization.ipynb': '{}',
    'output/.gitkeep': '',
    'tests/test_reconcile.py': 'import pytest\nfrom src.reconcile import reconcile_trades\ndef test_reconcile():\n    df = reconcile_trades("data/internal_trades.csv","data/broker_trades.csv")\n    assert "Break" in df.columns\n',
    'tests/test_compliance.py': '',
    'tests/test_analytics.py': '',
    'Dockerfile': 'FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nEXPOSE 8501\nCMD ["streamlit","run","src/dashboard.py","--server.port=8501","--server.address=0.0.0.0"]\n'
}

# Create ZIP file
output_zip = '/mnt/data/m1_trading_ops_suite.zip'
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file_path, content in file_structure.items():
        # Ensure folder structure exists inside zip
        zipf.writestr(file_path, content)

output_zip
