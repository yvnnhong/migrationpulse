import boto3
import requests
import os
import pandas as pd
import io
from datetime import datetime, timezone

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
MOVEBANK_USERNAME = os.environ.get("MOVEBANK_USERNAME")
MOVEBANK_PASSWORD = os.environ.get("MOVEBANK_PASSWORD")

BRONZE_BUCKET = "migrationpulse-bronze"

SPECIES_STUDIES = {
    "bald_eagle": {
        "study_id": 430263960,
        "individuals": ["BACA01", "BACA02", "BACA03", "BAEA24-69", "BAEA24-70"],
    },
    "turkey_vulture": {
        "study_id": 16880941,
        "individuals": [
            "Argentina", "Butterball", "Disney", "Domingo", "Irma",
            "La Pampa", "Leo", "Mac", "Mark", "Mary", "Morongo",
            "Prado", "Rosalie", "Sarkis", "Schaumboch", "Steamhouse 1",
            "Steamhouse 2", "Whitey", "Young Luro"
        ],
    },
}

def fetch_individual(study_id, individual_id):
    """Fetch GPS records for one individual from Movebank API."""
    resp = requests.get(
        "https://www.movebank.org/movebank/service/direct-read",
        params={
            "entity_type": "event",
            "study_id": study_id,
            "individual_local_identifier": individual_id,
        },
        auth=(MOVEBANK_USERNAME, MOVEBANK_PASSWORD),
        timeout=60,
    )
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df["individual_local_identifier"] = individual_id
    return df

def upload_to_bronze(species_name, df):
    """Upload dataframe as JSON to S3 bronze bucket."""
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    now = datetime.now(timezone.utc)
    key = f"{species_name}/{now.strftime('%Y/%m/%d')}/raw_{now.strftime('%H%M%S')}.json"

    s3.put_object(
        Bucket=BRONZE_BUCKET,
        Key=key,
        Body=df.to_json(orient="records"),
        ContentType="application/json",
    )
    print(f"Uploaded {len(df)} records to s3://{BRONZE_BUCKET}/{key}")
    return key

def run_bronze_ingest():
    results = {}
    for species_name, config in SPECIES_STUDIES.items():
        try:
            all_dfs = []
            for individual in config["individuals"]:
                print(f"Fetching {species_name} / {individual}...")
                df = fetch_individual(config["study_id"], individual)
                all_dfs.append(df)
            combined = pd.concat(all_dfs, ignore_index=True)
            key = upload_to_bronze(species_name, combined)
            results[species_name] = {"status": "success", "s3_key": key, "records": len(combined)}
        except Exception as e:
            print(f"ERROR processing {species_name}: {e}")
            results[species_name] = {"status": "failed", "error": str(e)}
    return results

if __name__ == "__main__":
    results = run_bronze_ingest()
    print("\n=== INGEST SUMMARY ===")
    for species, result in results.items():
        print(f"{species}: {result['status']} — {result.get('records', 0)} records")