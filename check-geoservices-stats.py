# -*- coding: utf-8 -*-
"""
Title: Check geoservices statistics
Author: Ralph Straumann
Date: 2023-05 (updated 2026-11)
Purpose: Compare the current geoservices statistics with the mean of the
    last 30 days and send an e-mail alert if the number of datasets of an
    owner dropped significantly (which usually means changed endpoints).
Notes:
- Python >= 3.10, duckdb >= 1.0, polars >= 1.0
- E-mail settings are read from MAIL_SMTP_SERVER, MAIL_USER_NAME and
  MAIL_PASSWORD. Without them no e-mail is sent.
"""

import os
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage

import duckdb
import polars as pl

import configuration as config

CLASSIFICATION = """
    CASE
        WHEN ratio = 100 THEN 'Stable'
        WHEN ratio > 100 THEN 'Improved'
        WHEN ratio > 90 THEN 'Decreased'
        WHEN ratio > 80 THEN 'Strongly decreased'
        ELSE 'Suspicious. Maybe services endpoints have changed?'
    END"""


def compute_change_stats():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE current_stats AS SELECT DATE, OWNER, DATASET_COUNT "
        "FROM read_csv_auto(?)", [config.GEOSERVICES_STATS_CH_CSV])
    current_date = con.execute(
        "SELECT MAX(DATE) FROM current_stats").fetchone()[0]
    from_date = current_date - timedelta(days=30)

    # Historic statistics: everything between 1 and 30 days old
    con.execute(
        "CREATE TABLE hist_stats AS SELECT OWNER, "
        "AVG(DATASET_COUNT) AS MEAN_DATASET_COUNT "
        "FROM read_csv_auto(?, union_by_name = true) "
        "WHERE DATE >= ? AND DATE < ? GROUP BY OWNER",
        [config.GEOSERVICES_STATS_CH_PATTERN, from_date, current_date])

    rel = con.sql(f"""
        WITH s AS (
            SELECT c.OWNER, c.DATE, c.DATASET_COUNT, h.MEAN_DATASET_COUNT,
                   ROUND(c.DATASET_COUNT / h.MEAN_DATASET_COUNT * 100, 1)
                       AS ratio
            FROM current_stats c JOIN hist_stats h ON c.OWNER = h.OWNER)
        SELECT OWNER AS "Owner",
               DATE AS "Date",
               DATASET_COUNT AS "Current dataset count",
               MEAN_DATASET_COUNT AS "Mean dataset count over last 30 days",
               ratio AS "Dataset ratio (percent)",
               ROUND(ratio - 100, 1) AS "Dataset change (percent)",
               {CLASSIFICATION} AS "Classification"
        FROM s
        UNION ALL
        -- Owners without history (new sources)
        SELECT c.OWNER, c.DATE, c.DATASET_COUNT, NULL, NULL, NULL, 'New'
        FROM current_stats c ANTI JOIN hist_stats h ON c.OWNER = h.OWNER
        """)
    # Build the DataFrame from plain rows (avoids a pyarrow dependency)
    return pl.DataFrame(rel.fetchall(), schema=rel.columns, orient="row")


def send_alert(suspicious):
    smtp_server = os.environ.get("MAIL_SMTP_SERVER")
    user_name = os.environ.get("MAIL_USER_NAME")
    password = os.environ.get("MAIL_PASSWORD")
    if not (smtp_server and user_name and password):
        print("No mail credentials configured, not sending an alert.")
        return
    owners = ", ".join(suspicious["Owner"].to_list())
    msg = EmailMessage()
    msg["Subject"] = "Significant changes in geoservices availability"
    msg["From"] = user_name
    msg["To"] = ", ".join(config.GEOSERVICES_CHANGESTATS_ALERT_RECIPIENTS)
    msg.set_content(
        "Hi\n\n"
        "Geoservice Harvester has found significant changes in geoservices "
        "availability in its last run (%s).\n"
        "This might mean that some data owners have changed the endpoints "
        "of their geoservices.\n\n"
        "Check the change statistics at https://github.com/davidoesch/"
        "geoservice_harvester_poc/blob/main/data/"
        "geoservices_changestats_CH.csv\n" % owners)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, 465, context=context) as server:
        server.login(user_name, password)
        server.send_message(msg)
    print("Alert e-mail sent")


if __name__ == "__main__":
    df = compute_change_stats()
    pl.Config.set_tbl_rows(len(df))
    print(df)
    df.write_csv(config.GEOSERVICES_CHANGESTATS_CH_CSV, separator=",",
                 quote_char='"', date_format="%d.%m.%Y")

    suspicious = df.filter(
        pl.col("Classification").str.contains("Suspicious"))
    if len(suspicious) > 0:
        print("\nFound significant changes")
        try:
            send_alert(suspicious)
        except Exception as e:
            print("Sending the alert failed: %s" % e)
