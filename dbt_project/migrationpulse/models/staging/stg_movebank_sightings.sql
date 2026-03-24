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

with source as (
    select *
    from delta_scan('s3://migrationpulse-silver/bald_eagle')
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