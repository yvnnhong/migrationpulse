with source as (
    select *
    from read_parquet('s3://migrationpulse-silver/bald_eagle/**/*.parquet')
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