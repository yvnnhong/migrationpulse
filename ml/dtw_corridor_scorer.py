import matplotlib
matplotlib.use('Agg')
import os
import boto3
import pandas as pd
import numpy as np
import io
import mlflow
import mlflow.sklearn
from dtaidistance import dtw
import matplotlib.pyplot as plt

def load_silver_data():
    """Load the latest silver parquet from S3"""
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name='us-east-2'
    )
    objs = sorted([
        o['Key'] for o in s3.list_objects_v2(
            Bucket='migrationpulse-silver',
            Prefix='bald_eagle/'
        )['Contents']
    ], reverse=True)
    obj = s3.get_object(Bucket='migrationpulse-silver', Key=objs[0])
    df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
    return df

def build_template(df):
    """Build median trajectory template per day of year"""
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df['day_of_year'] = df['timestamp'].dt.dayofyear
    template = df.groupby('day_of_year').agg(
        lat=('location_lat', 'median'),
        lon=('location_long', 'median')
    ).reset_index()
    return template

def score_individual(df, individual_id, template):
    """Compute DTW distance for one individual vs template"""
    ind_df = df[df['individual_id'] == individual_id].copy()
    ind_df['timestamp'] = pd.to_datetime(ind_df['timestamp'], utc=True)
    ind_df['day_of_year'] = ind_df['timestamp'].dt.dayofyear
    ind_df = ind_df.sort_values('day_of_year')

    if len(ind_df) < 10:
        return None

    ind_lats = ind_df['location_lat'].values.astype(np.double)
    template_lats = template['lat'].values.astype(np.double)

    distance = dtw.distance_fast(ind_lats, template_lats, window=30)
    return distance

def run_dtw_scoring():
    mlflow.set_experiment("migration_pulse")

    with mlflow.start_run():
        df = load_silver_data()

        # log parameters
        dtw_window = 30
        anomaly_threshold = 2.0
        mlflow.log_param("dtw_window", dtw_window)
        mlflow.log_param("anomaly_threshold_std", anomaly_threshold)

        template = build_template(df)
        individuals = df['individual_id'].unique()

        scores = {}
        for ind in individuals:
            score = score_individual(df, ind, template)
            if score is not None:
                scores[ind] = score

        distances = np.array(list(scores.values()))
        mean_dist = float(np.mean(distances))
        std_dist = float(np.std(distances))
        threshold = mean_dist + anomaly_threshold * std_dist

        anomalies = {k: v for k, v in scores.items() if v > threshold}
        anomaly_rate = len(anomalies) / len(scores) if scores else 0

        # log metrics
        mlflow.log_metric("mean_dtw_distance", mean_dist)
        mlflow.log_metric("std_dtw_distance", std_dist)
        mlflow.log_metric("anomaly_threshold", threshold)
        mlflow.log_metric("anomaly_rate", anomaly_rate)
        mlflow.log_metric("total_individuals", len(scores))
        mlflow.log_metric("anomaly_count", len(anomalies))

        # plot distance distribution
        plt.figure(figsize=(10, 5))
        plt.hist(distances, bins=20, color='steelblue', edgecolor='black')
        plt.axvline(threshold, color='red', linestyle='--', label=f'Threshold ({threshold:.2f})')
        plt.title('DTW Distance Distribution — Bald Eagle')
        plt.xlabel('DTW Distance')
        plt.ylabel('Count')
        plt.legend()
        plt.tight_layout()
        plt.savefig('dtw_distribution.png')
        mlflow.log_artifact('dtw_distribution.png')
        plt.close()

        print(f"Scored {len(scores)} individuals")
        print(f"Mean DTW distance: {mean_dist:.4f}")
        print(f"Anomaly threshold: {threshold:.4f}")
        print(f"Anomalies detected: {len(anomalies)}")
        for ind, dist in anomalies.items():
            print(f"{ind}: DTW distance = {dist:.4f}")

        return scores, anomalies

if __name__ == "__main__":
    run_dtw_scoring()