# -*- coding: utf-8 -*-
"""
Title: Check geoservices statistics
Author: Ralph Straumann
Date: 2023-05-00
Purpose: Compare current geoservices statistics with recent ones.
Notes:
- Uses Python 3.9
- If significant changes occur 
"""

import os
import configuration as config
from datetime import timedelta
import polars as pl
import duckdb
import smtplib
import ssl

if __name__ == "__main__":

    # Get current statistics
    duckdb.sql('CREATE TABLE current_stats AS ('
               'SELECT DATE, OWNER, DATASET_COUNT FROM "%s");' %
               config.GEOSERVICES_STATS_CH_CSV)
    current_date = duckdb.sql(
        'SELECT MAX(DATE) FROM current_stats').fetchone()[0]
    from_date = current_date - timedelta(days=30)

    # Get historic statistics (everything that is at least 1 and at most
    # 30 days old)
    duckdb.sql("""CREATE TABLE hist_stats AS (
        SELECT OWNER, 
        AVG(DATASET_COUNT) AS MEAN_DATASET_COUNT 
        FROM "%s"
        WHERE DATE >= '%s' AND 
        DATE < '%s' 
        GROUP BY OWNER);""" % (
        config.GEOSERVICES_STATS_CH_PATTERN,
        from_date.strftime("%Y-%m-%d"),
        current_date.strftime("%Y-%m-%d")))

    duckdb.sql(
        """CREATE TABLE stats AS (
        SELECT current_stats.OWNER AS Owner, 
        DATE as Date, 
        DATASET_COUNT as "Current dataset count", 
        MEAN_DATASET_COUNT as "Mean dataset count over last 30 days", 
        DATASET_COUNT / MEAN_DATASET_COUNT * 100 AS "Dataset ratio (percent)",
        ROUND("Dataset ratio (percent)" - 100, 1) as "Dataset change (percent)",
        CASE
            WHEN "Dataset ratio (percent)" == 100 THEN 'Stable'
            WHEN "Dataset ratio (percent)" > 100 THEN 'Improved'
            WHEN "Dataset ratio (percent)" < 100 AND 
                "Dataset ratio (percent)" > 90 THEN 'Decreased'
            WHEN "Dataset ratio (percent)" <= 90 AND 
                "Dataset ratio (percent)" > 80 THEN 'Strongly decreased'
            WHEN "Dataset ratio (percent)" <= 80 THEN 'Suspicious. Maybe services endpoints have changed?'
        END AS Classification
        FROM current_stats 
        JOIN hist_stats 
        ON current_stats.OWNER = hist_stats.OWNER);""")

    df = duckdb.sql("""SELECT * FROM stats""").pl()
    pl.Config.set_tbl_rows(len(df))
    print(df)
    df.write_csv(config.GEOSERVICES_CHANGESTATS_CH_CSV, separator=',',
                 quote='"', date_format="%d.%m.%Y")

    df = duckdb.sql(
        """SELECT * FROM stats WHERE Classification LIKE '%Suspicious%'""").pl()

    # if len(df) > 0:
    if 1 > 0:
        # We have at least one "suspicious" entry
        try:
            smtp_server = os.environ.get('MAIL_SMTP_SERVER')
            user_name = os.environ.get('MAIL_USER_NAME')
            password = os.environ.get('MAIL_PASSWORD')
            port = 465
            # Create a secure SSL context
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(smtp_server, port, context=context) as \
                    server:
                server.login(user_name, password)
                message = """
                Subject: Significant changes in geoservices availability
                
                Hello
                
                Geoservice Harvester has found significant changes in 
                geoservices availability in its last run. 
                This might mean that some data owners have changed 
                endpoints of their geoservices. 
                Check the geoservice availability change statistics at:
                https://github.com/rastrau/geoservice_harvester_poc/blob/main/data/geoservices_changestats_CH.csv
                """

                server.sendmail(user_name,
                                config.GEOSERVICES_CHANGESTATS_ALERT_RECIPIENTS,
                                message)
        except Exception as e:
            print(str(e))
