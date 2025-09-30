# Strava2.md

![Logo](assets/logo-250.png)

Strava activity to hugo-compatibile markdown converter.

Using Activity ID, uses Strava API to fetch data, download activity images, and generate a markdown file containing:
  - Nice header image with activity stats (also useful for sharing on social media) with basic data and route overlay.
  - Short activity stats
  - Leaflet.JS map with elevation profile.
  - Activity description
  - Photos

## Invocation:

See help:

```bash
python stravaapi.py
```

## Required hugo mods:

Ensure file `layouts/shortcodes/rawhtml.html` with content:
```
<!-- raw html -->
{{- .Inner -}}
```

## Code development and testing

Unless well-broken, debugging a .md is non-trivial, especially when not many editors/viewers support rendering raw HTML content.
To circumvent that, [md-to-html](https://github.com/AumitLeon/markdown_html_converter)-based converter is in `utils` folder.

A short Makefile has also been added to simplify the situation.

Usage (**warning: this will clear your Activities folder every time!**):

```
export ACTIVITY_ID=.....
make env # creates python venv with requriements
make test # wipes the Activities folder and fetches the activity
```


## Examples

 - https://b4d.sablun.org/blog/activities/2025-09-20-15877521879/


## Disclaimer

The testing suite that is a part of this project uses the [mistune library](https://github.com/lepture/mistune) for parsing markdown into html. Disclamer below:

> Copyright (c) 2014, Hsiaoming Yang
>
> All rights reserved.
>
> Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
>
> * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
>
> * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
>
> * Neither the name of the creator nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
>
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

