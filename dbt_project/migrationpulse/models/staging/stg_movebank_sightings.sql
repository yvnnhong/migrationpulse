{% set aws_key = env_var('AWS_ACCESS_KEY_ID') %}
{% set aws_secret = env_var('AWS_SECRET_ACCESS_KEY') %}

{{ config(pre_hook="
    CREATE OR REPLACE SECRET delta_s3_secret (
        TYPE S3,
        KEY_ID '" ~ aws_key ~ "',
        SECRET '" ~ aws_secret ~ "',
        REGION 'us-east-2'
    )
") }}

with bald_eagle as (
    select individual_id, timestamp, location_lat, location_long, species, ingest_date
    from delta_scan('s3://migrationpulse-silver/bald_eagle')
),
turkey_vulture as (
    select individual_id, timestamp, location_lat, location_long, species, ingest_date
    from delta_scan('s3://migrationpulse-silver/turkey_vulture')
),
delmarva_waterfowl as (
    select individual_id, timestamp, location_lat, location_long, species, ingest_date
    from delta_scan('s3://migrationpulse-silver/delmarva_waterfowl')
),
source as (
    select * from bald_eagle
    union all
    select * from turkey_vulture
    union all
    select * from delmarva_waterfowl
),
renamed as (
    select
        individual_id,
        timestamp,
        location_long as longitude,
        location_lat as latitude,
        species,
        ingest_date
    from source
    where latitude is not null
      and longitude is not null
)

select * from renamed