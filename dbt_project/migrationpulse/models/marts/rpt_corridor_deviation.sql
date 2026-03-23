with base as (
    select * from {{ ref('fct_species_movements') }}
),

weekly_agg as (
    select
        individual_id,
        species,
        date_trunc('week', timestamp) as week_start,
        count(*) as fix_count,
        round(avg(latitude), 6) as avg_latitude,
        round(avg(longitude), 6) as avg_longitude,
        round(min(latitude), 6) as min_latitude,
        round(max(latitude), 6) as max_latitude,
        round(min(longitude), 6) as min_longitude,
        round(max(longitude), 6) as max_longitude,
        round(avg(speed_deg_per_hour), 6) as avg_speed_deg_per_hour,
        round(max(speed_deg_per_hour), 6) as max_speed_deg_per_hour
    from base
    where speed_deg_per_hour is not null
    group by 1, 2, 3
)

select * from weekly_agg
order by individual_id, week_start