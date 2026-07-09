# Cross-source agreement

Sources measure different failure modes over different subsets; sparse
overlap is expected. Segment-level correlations are attenuated by geocode/
snap noise (points near segment boundaries land on neighbors) and small n —
read the road level as the primary signal.

## Segment level

| pair | n overlap | spearman |
|---|---|---|
| crashes_total vs wl_events | 22 | 0.037 |
| crashes_total vs cv_damage_per_frame | 13 | -0.087 |
| wl_events vs cv_damage_per_frame | 36 | -0.110 |

## Road level (canonical roads >= 3 km, named)

| pair | n roads | spearman |
|---|---|---|
| crashes_per_km vs wl_per_km | 64 | 0.293 |
| crashes_per_km vs cv_damage_per_frame | 28 | 0.288 |
| wl_per_km vs cv_damage_per_frame | 28 | -0.255 |
