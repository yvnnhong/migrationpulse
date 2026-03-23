with base as (
    select * from {{ ref('stg_movebank_sightings') }}
),

with_velocity as (
    select
        individual_id,
        timestamp,
        latitude,
        longitude,
        species,
        ingest_date,
        lag(latitude) over (partition by individual_id order by timestamp) as prev_lat,
        lag(longitude) over (partition by individual_id order by timestamp) as prev_lon,
        lag(timestamp) over (partition by individual_id order by timestamp) as prev_timestamp
    from base
),

final as (
    select
        individual_id,
        timestamp,
        latitude,
        longitude,
        species,
        ingest_date,
        round(
            sqrt(power(latitude - prev_lat, 2) + power(longitude - prev_lon, 2)),
        6) as displacement,
        round(
            sqrt(power(latitude - prev_lat, 2) + power(longitude - prev_lon, 2)) /
            nullif(epoch(timestamp - prev_timestamp) / 3600, 0),
        6) as speed_deg_per_hour
    from with_velocity
)

select * from final