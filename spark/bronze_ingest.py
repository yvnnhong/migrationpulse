import requests
import boto3
import json
import os
from datetime import datetime, timezone

# AWS + Movebank credentials from environment
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
MOVEBANK_USERNAME = os.environ.get("MOVEBANK_USERNAME")
MOVEBANK_PASSWORD = os.environ.get("MOVEBANK_PASSWORD")

BRONZE_BUCKET = "migrationpulse-bronze"

# Movebank study IDs for our 5 species
# These are real public study IDs from Movebank
SPECIES_STUDIES = {
    "usgs_avian_telemetry": 619097045,
    "ferruginous_hawk": 110270319,
    "northern_elephant_seal": 7006760,
}

def fetch_species_data(species_name, study_id):
    """Fetch GPS records for a species study from Movebank API."""
    print(f"Fetching data for {species_name} (study {study_id})...")

    url = "https://www.movebank.org/movebank/service/direct-read"
    params = {
        "entity_type": "event",
        "study_id": study_id,
        "attributes": "individual_local_identifier,timestamp,location_lat,location_long,ground_speed,heading,height_above_ellipsoid",
        "format": "json",
    }

    response = requests.get(
        url,
        params=params,
        auth=(MOVEBANK_USERNAME, MOVEBANK_PASSWORD),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()

def upload_to_bronze(species_name, data):
    """Upload raw JSON to S3 bronze bucket."""
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
        Body=json.dumps(data),
        ContentType="application/json",
    )
    print(f"Uploaded {species_name} data to s3://{BRONZE_BUCKET}/{key}")
    return key

def run_bronze_ingest():
    """Main function — fetch all species and land in bronze."""
    results = {}
    for species_name, study_id in SPECIES_STUDIES.items():
        try:
            data = fetch_species_data(species_name, study_id)
            key = upload_to_bronze(species_name, data)
            results[species_name] = {"status": "success", "s3_key": key}
        except Exception as e:
            print(f"ERROR fetching {species_name}: {e}")
            results[species_name] = {"status": "failed", "error": str(e)}
    return results

if __name__ == "__main__":
    results = run_bronze_ingest()
    print("\n=== INGEST SUMMARY ===")
    for species, result in results.items():
        print(f"{species}: {result['status']}")