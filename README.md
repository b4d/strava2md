# Strava2.md

Strava activity to hugo-compatibile markdown converter.

Parser takes an activity id, pulls all data via Strava API and generates a markdown file containing:
  - Nice header image (also useful for sharing on social media) with basic data and route overlay.
  - Stats.
  - Leaflet map with elevation profile.
  - Description of activity.
  - Photos.

## Invocation:

See help:

```bash
python stravaapi.py
```

## Converting maps and charts to png

- requires chrome and selenium
- TODO FIXME whateverify: make it better

```
cp Rides/relevant.md tmp/index.html
python3 page2png.py
```

## required hugo mods:

Ensure file `layouts/shortcodes/rawhtml.html` with content:
```
<!-- raw html -->
{{- .Inner -}}
```

## Examples

 - https://b4d.sablun.org/blog/rides/2025-09-20-15877521879/
