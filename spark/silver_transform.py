import boto3
import os
import json
import pandas as pd
import io
from datetime import datetime, timezone

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")

BRONZE_BUCKET = "migrationpulse-bronze"
SILVER_BUCKET = "migrationpulse-silver"

def read_latest_bronze(species_name):
    """Read the most recent bronze JSON file for a species from S3."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    # List all files for this species and get the most recent
    response = s3.list_objects_v2(Bucket=BRONZE_BUCKET, Prefix=f"{species_name}/")
    files = sorted([obj["Key"] for obj in response.get("Contents", [])], reverse=True)

    if not files:
        raise ValueError(f"No bronze files found for {species_name}")

    latest = files[0]
    print(f"Reading bronze file: {latest}")
    obj = s3.get_object(Bucket=BRONZE_BUCKET, Key=latest)
    df = pd.read_json(io.BytesIO(obj["Body"].read()))
    return df

def transform_to_silver(df, species_name):
    """Apply silver-layer cleaning and transformations."""

    # Drop the numeric individual_id — keep the human-readable one
    df = df.drop(columns=["individual_id"], errors="ignore")

    # Rename individual_local_identifier to individual_id
    df = df.rename(columns={"individual_local_identifier": "individual_id"})

    # Cast timestamp to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    # Drop rows with null coordinates or timestamps
    df = df.dropna(subset=["location_lat", "location_long", "timestamp"])

    # Drop duplicates — same individual, same timestamp
    df = df.drop_duplicates(subset=["individual_id", "timestamp"])

    # Clean ground speed — flag negatives as null
    if "ground_speed" in df.columns:
        df["ground_speed"] = pd.to_numeric(df["ground_speed"], errors="coerce")
        df.loc[df["ground_speed"] < 0, "ground_speed"] = None

    # Add metadata columns
    df["species"] = species_name
    df["ingest_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Sort by individual and timestamp
    df = df.sort_values(["individual_id", "timestamp"]).reset_index(drop=True)

    print(f"Silver transform complete: {len(df)} records")
    return df

def upload_to_silver(species_name, df):
    """Upload cleaned dataframe as Parquet to S3 silver bucket."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    now = datetime.now(timezone.utc)
    key = f"{species_name}/{now.strftime('%Y/%m/%d')}/silver_{now.strftime('%H%M%S')}.parquet"

    # Write parquet to buffer
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    s3.put_object(
        Bucket=SILVER_BUCKET,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )
    print(f"Uploaded silver parquet to s3://{SILVER_BUCKET}/{key}")
    return key

def run_silver_transform(species_list=["bald_eagle"]):
    results = {}
    for species_name in species_list:
        try:
            df_bronze = read_latest_bronze(species_name)
            df_silver = transform_to_silver(df_bronze, species_name)
            key = upload_to_silver(species_name, df_silver)
            results[species_name] = {"status": "success", "s3_key": key, "records": len(df_silver)}
        except Exception as e:
            print(f"ERROR transforming {species_name}: {e}")
            results[species_name] = {"status": "failed", "error": str(e)}
    return results

if __name__ == "__main__":
    results = run_silver_transform()
    print("\n=== SILVER TRANSFORM SUMMARY ===")
    for species, result in results.items():
        print(f"{species}: {result['status']} — {result.get('records', 0)} records")