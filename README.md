# Strava2.md

Strava activity to hugo-compatibile markdown converter

## Invocation:

See help:

```bash
python stravaapi.py
```

## required hugo mods:

Ensure file `layouts/shortcodes/rawhtml.html` with content:
```
<!-- raw html -->
{{- .Inner -}}
```