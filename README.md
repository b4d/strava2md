# Strava2.md

Strava activity to hugo-compatibile markdown converter

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