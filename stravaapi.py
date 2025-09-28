#!/usr/bin/env python3
"""

    - Pull all activities
    - If suffer score > something
    - Pull activity and generate YYYY-MM-DD-{ID}.md
    - Put that file in the blog/Rides/ folder

TODO:
    - photos at coordinates as popups
"""

import requests
from datetime import timedelta, datetime
import time
import polyline
import numpy as np
import os
import argparse, sys
from config import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_CBACK_URL 
from config import HOME_COORDINATES, HOME_OFFSET, FONT_PATH, FONT_PATH_BOLD

import math
from PIL import Image, ImageFont, ImageDraw
import io

# OAuth workflow
import webbrowser, threading, re
from http.server import BaseHTTPRequestHandler, HTTPServer

# Strava root API
STRAVA_API_ROOT = "https://www.strava.com/api/v3"
VERBOSE=False

# These badbois get populated with oauth flow:
oauthcode = "" 
access_token = ""
headers = ""


# Used to make home locations private
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def trim_by_radius_multi(poly_line, centers, radius_m=HOME_OFFSET):
    """
    poly_line: list of [lat, lon, alt]
    centers: list of (lat, lon) tuples (e.g., HOME_COORDINATES)
    Removes start points until outside radius of ALL centers,
    and removes end points until outside radius of ALL centers.
    """
    if not poly_line:
        return poly_line

    def near_any(lat, lon):
        return any(haversine_m(lat, lon, cx, cy) <= radius_m for cx, cy in centers)

    # Trim from start
    start_idx = 0
    while start_idx < len(poly_line) and near_any(poly_line[start_idx][0], poly_line[start_idx][1]):
        start_idx += 1

    # Trim from end
    end_idx = len(poly_line) - 1
    while end_idx >= start_idx and near_any(poly_line[end_idx][0], poly_line[end_idx][1]):
        end_idx -= 1

    return poly_line[start_idx:end_idx+1]


def _align_polyline(activity_id):
    # Pull distance-aligned streams
    h = getStream(activity_id, 'altitude,distance')  # altitude vs its distance axis
    g = getStream(activity_id, 'latlng,distance')    # latlng    vs its distance axis

    alts = (h.get('altitude', {}) or {}).get('data', []) or []
    d_h  = (h.get('distance', {}) or {}).get('data', []) or []

    latlng = (g.get('latlng', {}) or {}).get('data', []) or []
    d_g    = (g.get('distance', {}) or {}).get('data', []) or []

    # Guardrails
    if len(latlng) < 2 or len(alts) < 2 or len(d_g) < 2 or len(d_h) < 2:
        return []  # not enough data to plot

    # Both distance arrays should be increasing; drop any non‑monotonic glitches
    def _monotonic(x, y):
        out_x, out_y = [x[0]], [y[0]]
        for i in range(1, len(x)):
            if x[i] > out_x[-1]:
                out_x.append(x[i]); out_y.append(y[i])
        return np.array(out_x), np.array(out_y)

    d_h, alts = _monotonic(np.array(d_h, dtype=float), np.array(alts, dtype=float))
    d_g       = np.array(d_g, dtype=float)

    # Resample altitude to latlng distances
    alt_on_g = np.interp(d_g, d_h, alts, left=alts[0], right=alts[-1])

    # Light smoothing to kill micro spikes (boxcar)
    if len(alt_on_g) >= 5:
        k = 5
        kernel = np.ones(k) / k
        alt_on_g = np.convolve(alt_on_g, kernel, mode='same')

    # Build [lat, lon, alt] with rounded altitude
    poly_line = [[lat, lon, int(round(alt))] for (lat, lon), alt in zip(latlng, alt_on_g)]

    # Apply your privacy trimming
    poly_line = trim_by_radius_multi(poly_line, centers=HOME_COORDINATES, radius_m=HOME_OFFSET)

    # Ensure at least 2 points after trimming
    return poly_line if len(poly_line) >= 2 else []

# Return array of activity IDs where suffer_score (relative effort) is over 200
def get_sufferfest_activities(access_token, suffer_threshold=200, per_page=100, max_pages=10):
    url = f"{STRAVA_API_ROOT}/athlete/activities"

    result_ids = []

    for page in range(1, max_pages + 1):
        params = {
            "page": page,
            "per_page": per_page
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
            break

        activities = response.json()

        if not activities:
            break  # No more data

        for activity in activities:
            score = activity.get("suffer_score")
            if score is not None and score > suffer_threshold:
                result_ids.append(activity["id"])

    return result_ids

# Return array of activity IDs that are defined as MountainBikeRide
def get_mtb_ride_ids(access_token, per_page=100, max_pages=10):
    url = f"{STRAVA_API_ROOT}/athlete/activities"

    mtb_ids = []

    for page in range(1, max_pages + 1):
        params = {
            "page": page,
            "per_page": per_page
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"⚠️ Failed to fetch page {page}: {response.status_code} {activity_id}")
            break

        activities = response.json()

        if not activities:
            break  # No more activities

        for activity in activities:
            # Match type and sub-type
            if activity.get("sport_type") == "MountainBikeRide":
                mtb_ids.append(activity["id"])

    return mtb_ids

def getStream(activity_id, keys, series_type='distance', resolution='high'):
    stream_url = f"{STRAVA_API_ROOT}/activities/{activity_id}/streams"
    stream_params = {
        "keys": keys,                 # e.g., "latlng,distance" or "altitude,distance"
        "key_by_type": "true",
        "series_type": series_type,   # enforce distance-based alignment
        "resolution": resolution      # high/medium/low
    }
    r = requests.get(stream_url, headers=headers, params=stream_params)
    if r.status_code != 200:
        print(f"⚠️ Stream fetch failed: {r.status_code} {activity_id}")
        return {}
    return r.json()

# Create MD links to all the photos on the activity
def list_photos(activity_id):
    photo_url = f"{STRAVA_API_ROOT}/activities/{activity_id}/photos?size=5000"
    response = requests.get(photo_url, headers=headers)

    if response.status_code == 200:
        photos = response.json()
        output = []
        if not os.path.exists(f'./Rides/{activity_id}/'):
            os.makedirs(f'./Rides/{activity_id}/')

        for i, photo in enumerate(photos, 1):
            url = photo.get("urls", {}).get("5000")
            if url:
                img_data = requests.get(url).content
                with open(f'./Rides/{activity_id}/photo_{i}.jpg', 'wb') as handler:
                    handler.write(img_data)
                output.append(f"![Ride Image {i}](./{activity_id}/photo_{i}.jpg)")

        return "\n".join(output)
    else:
        return f"⚠️ Error: {response.status_code} - {response.text}"


def fetch_activites(_since, _max_pages=10, _type='Ride'):
    url = f"{STRAVA_API_ROOT}/athlete/activities"
    result_ids = []
    _per_page = 20

    for page in range(1, _max_pages + 1):
        params = {
            "page": page,
            "per_page": _per_page,
            "after": _since
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"⚠️ Failed to fetch page {page}: {response.status_code}")
            break

        activities = response.json()

        if not activities:
            break  # No more data

        for activity in activities:
            if activity['type'] == _type:
                result_ids.append(activity["id"])

    return result_ids

def fetch_activity_data(activity_id):
    url = f"{STRAVA_API_ROOT}/activities/{activity_id}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"⚠️ Failed to fetch activity {activity_id} Error: {response.status_code} - {response.text}")
        return activity_id, -1, -1, -1
    
    data = response.json()
    activity_summary = {
        "id": activity_id,
        "name": data.get("name"),
        "distance_km": round(data.get("distance", 0) / 1000, 2),
        "moving_time": str(timedelta(seconds=data.get("moving_time", 0))),
        "elapsed_time": str(timedelta(seconds=data.get("elapsed_time", 0))),
        "elevation_gain_m": data.get("total_elevation_gain", 0),
        "start_date_time": data.get("start_date"),
        "start_date": data.get("start_date")[:10] if data.get("start_date") else None,
        "location_country": data.get("location_country"),
        "description_parsed": (data.get("description") or "").replace('\r\n', '\n').strip(),
        "image": (((data.get("photos") or {}).get("primary") or {}).get("urls") or {}).get("600"),
    }

    poly_line = _align_polyline(activity_id)

    photos = list_photos(activity_id)
    return activity_summary, poly_line, photos

def wrap_title(draw, text, font, max_width):
    """Wrap title into one or two lines based on available width."""
    if draw.textlength(text, font=font) <= max_width:
        return [text]  # fits in one line

    # Try splitting by spaces
    words = text.split()
    line1, line2 = "", ""
    for word in words:
        test_line = (line1 + " " + word).strip()
        if draw.textlength(test_line, font=font) <= max_width:
            line1 = test_line
        else:
            # Move rest of words to line2
            line2 = " ".join(words[words.index(word):])
            break
    return [line1, line2] if line2 else [line1]

def draw_polyline_on_image(
    draw,
    poly_line,
    w, h,
    margin=40,
    color=(253,151,32,255),
    width=4,
    scale=0.4,                 # fraction of drawable area (0<scale<=1)
    anchor="topmiddle",         # "topright" | "topleft" | "bottomright" | "bottomleft"
    supersample=3,             # AA factor
    outline_color=(0,0,0,180), # soft outline for contrast
    outline_extra=2            # extra px around the main width for outline
):
    """Render a route with correct aspect by projecting lat/lon to Web-Mercator
    and fitting it into a smaller box anchored inside the image.
    """
    if not poly_line:
        return

    # --- Project lat/lon to Web-Mercator (meters) ---
    R = 6378137.0
    def mercator(lat, lon):
        # clamp latitude for numerical stability
        lat = max(min(lat, 85.05112878), -85.05112878)
        x = math.radians(lon) * R
        y = math.log(math.tan(math.pi/4.0 + math.radians(lat)/2.0)) * R
        return x, y

    mx, my = zip(*(mercator(p[0], p[1]) for p in poly_line))
    min_x, max_x = min(mx), max(mx)
    min_y, max_y = min(my), max(my)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)

    # --- Target plot box on final image ---
    plot_w = int((w - 2*margin) * scale)
    plot_h = int((h - 2*margin) * scale)

    if anchor == "topright":
        base_x, base_y = w - margin - plot_w, margin
    elif anchor == "topleft":
        base_x, base_y = margin, margin
    elif anchor == "topmiddle":
        base_x = (w - plot_w) / 2
        base_y = margin
    elif anchor == "bottomright":
        base_x, base_y = w - margin - plot_w, h - margin - plot_h
    elif anchor == "bottommiddle":
        base_x = (w - plot_w) / 2
        base_y = h - margin - plot_h
    else:  # "bottomleft"
        base_x, base_y = margin, h - margin - plot_h

    # --- Supersampled overlay for crisp anti-aliased result ---
    ss = max(1, int(supersample))
    big_w, big_h = plot_w * ss, plot_h * ss
    overlay = Image.new("RGBA", (big_w, big_h), (0,0,0,0))
    odraw = ImageDraw.Draw(overlay)

    # Preserve aspect ratio with a single uniform scale; center within box
    sx = (big_w - 1) / span_x
    sy = (big_h - 1) / span_y
    s  = min(sx, sy)
    off_x = (big_w - span_x * s) / 2.0
    off_y = (big_h - span_y * s) / 2.0

    def to_px(xm, ym):
        x = off_x + (xm - min_x) * s
        y = off_y + (max_y - ym) * s  # flip vertical
        return (x, y)

    path = [to_px(x, y) for x, y in zip(mx, my)]

    # Optional soft outline for visibility on busy photos
    if outline_extra > 0:
        odraw.line(path, fill=outline_color, width=width*ss + 2*outline_extra, joint="curve")

    odraw.line(path, fill=color, width=max(1, width*ss), joint="curve")

    # Downsample with LANCZOS and paste into the base image
    overlay_small = overlay.resize((plot_w, plot_h), Image.LANCZOS)

    # Try to obtain the underlying image from the draw object (works in modern Pillow)
    base_img = getattr(draw, "_image", None)
    if base_img is None:
        # Fallback for some Pillow versions
        base_img = getattr(draw, "im", None)
        if base_img is None:
            raise RuntimeError("Could not access base image from draw; pass the PIL Image to paste the overlay.")

    base_img.paste(overlay_small, (int(base_x), int(base_y)), overlay_small)

def overlayify_image(_image, _title, _date, _distance, _elevation, _moving, poly_line=None):

    margin = 40  # global margin from edge

    # Work in RGBA so we can blend an icon with transparency
    img = Image.open(io.BytesIO(_image)).convert("RGBA")
    w, h = img.size
    draw = ImageDraw.Draw(img)

    # Font sizes
    maxsize = min(w, h) / 12
    fontTitle   = ImageFont.truetype(FONT_PATH_BOLD, int(2/3.0*maxsize - 1))
    fontSubject = ImageFont.truetype(FONT_PATH, int(maxsize/2 - 5))
    fontData    = ImageFont.truetype(FONT_PATH_BOLD, int(2/3.0*maxsize - 1))

    # Darken the image
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 100))  # alpha = 120 (~50% dark)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)


    # Text (use 4-tuple RGBA color)
    # draw.text((20, 20), "GH://b4d/strava2md", (255, 255, 255, 255), font=fontSubject)
    # draw.text((w - 150, 20), _date, (255, 255, 255, 255), font=fontSubject)

    # --- Bottom stats reference ---
    stats_y_top = int(7/8.0 * h - 15)   # where you draw "Distance"

    # --- Title wrapping ---
    max_width = w - margin*2
    wrapped = wrap_title(draw, _title, fontTitle, max_width)

    # Height of title block (all lines)
    line_height = int(maxsize * 1.2)
    title_block_height = len(wrapped) * line_height

    # Place title so its bottom is 20px above stats
    y_start = stats_y_top - title_block_height - 20

    # --- Icon above title ---
    icon = Image.open("assets/icon-mtb.png").convert("RGBA")
    icon = icon.resize((int(2/3.0*maxsize - 1), int(2/3.0*maxsize - 1)))
    icon_x = margin
    icon_y = y_start - icon.height - 10
    img.paste(icon, (icon_x, icon_y), icon)

    # --- Draw wrapped title ---
    for i, line in enumerate(wrapped):
        draw.text((margin, y_start + i*line_height), line,
                  (255,255,255,255), font=fontTitle)

    # --- Polyline on image (only if provided & non-empty) ---
    if poly_line:
        draw_polyline_on_image(draw, poly_line, w, h, margin=40, scale=0.6)

    # --- Bottom stats ---
    bottom_y_label = int(7/8.0 * h - 15)
    bottom_y_value = int(7/8.0 * h + 15)

    inner_w = w - 2*margin
    col_w = inner_w / 3.0

    x_left   = margin                   # left column anchor
    x_center = margin + inner_w/2       # middle column anchor
    x_right  = w - margin               # right column anchor

    # Distance (value left, label centered above it)
    val_dist = f"{_distance} km"
    val_w = draw.textlength(val_dist, font=fontData)
    label = "Distance"
    label_w = draw.textlength(label, font=fontSubject)
    draw.text((x_left, bottom_y_value), val_dist, (255,255,255,255), font=fontData)
    draw.text((x_left + val_w/2 - label_w/2, bottom_y_label), label, (255,255,255,255), font=fontSubject)

    # Elev Gain (value centered, label centered above)
    val_elev = f"{_elevation}".rstrip("0").rstrip(".") + " m"
    val_w = draw.textlength(val_elev, font=fontData)
    label = "Elev Gain"
    label_w = draw.textlength(label, font=fontSubject)
    draw.text((x_center - val_w/2, bottom_y_value), val_elev, (255,255,255,255), font=fontData)
    draw.text((x_center - label_w/2, bottom_y_label), label, (255,255,255,255), font=fontSubject)

    # Time (value right, label centered above it)
    val_time = f"{_moving}"
    val_w = draw.textlength(val_time, font=fontData)
    label = "Time"
    label_w = draw.textlength(label, font=fontSubject)
    draw.text((x_right - val_w, bottom_y_value), val_time, (255,255,255,255), font=fontData)
    draw.text((x_right - val_w/2 - label_w/2, bottom_y_label), label, (255,255,255,255), font=fontSubject)


    # Flatten to RGB for JPEG (preserves icon edges by compositing with a solid bg)
    out_rgb = Image.new("RGB", img.size, (0, 0, 0))  # background color if any transparency remains
    out_rgb.paste(img, mask=img.split()[-1])

    _out = io.BytesIO()
    out_rgb.save(_out, format='JPEG', quality=95,subsampling=0)
    return _out.getvalue()


def generate_markdown(_summary, _photos, _polyline, _ftemplate='post_template.md', _leaftemplate='leaflet_template.html'):
    with open(_ftemplate,'r') as t:
        post_template=t.read()
        t.close()

    with open(_leaftemplate,'r') as t:
        leaflet_template=t.read()
        t.close()

    if not os.path.exists(f'./Rides/{_summary["id"]}/'):
        os.makedirs(f'./Rides/{_summary["id"]}/')

    _rideImg = '> No photos taken, too busy hammering my pedals'
    if _summary['image']:
        img_data = requests.get(_summary['image']).content
        with open(f'./Rides/{_summary["id"]}/photo_0.jpg', 'wb') as handler:
            handler.write(img_data)

        img_overlayed = overlayify_image(img_data, _summary['name'], _summary['start_date'], _summary['distance_km'], _summary['elevation_gain_m'], _summary['moving_time'],poly_line=_polyline,)
        with open(f'./Rides/{_summary["id"]}/photo_0o.jpg', 'wb') as handler:
            handler.write(img_overlayed)

        _rideImg = f"\n![Ride Image](./{_summary['id']}/photo_0o.jpg)"

    _leaflet = leaflet_template % {'POLYLINE':str(_polyline) }

    _photos = _photos if len(_photos) > 1 else '> As said, none taken, too busy riding'
    generated_markdown = post_template % {
                        'ID':_summary['id'],
                        'TITLE':_summary['name'],
                        'DATE':_summary['start_date'],
                        'ISDRAFT':'false',
                        'CATS':'["MTB"]',
                        'TAGS':'["rides", "mtb", "cycling", "bike"]',
                        'RIDEIMG': _rideImg,
                        'DISTANCE': _summary['distance_km'],
                        'ELE_GAIN': _summary['elevation_gain_m'],
                        'TIME_MOV':_summary['moving_time'],
                        'TIME_ELA': _summary['elapsed_time'],
                        'MAP': _leaflet,
                        'DESCR': _summary['description_parsed'],
                        'PHOTOS':_photos,
    }
    return generated_markdown

def save_markdown(_content, _fname):
    with open(_fname, "w", encoding="utf-8") as f:
        f.write(_content)
    print(f"✅ Created: {_fname}")

class WebRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        global oauthcode
        oauthcode = re.findall("code=(.*)&", self.path)[0]
        self.wfile.write(bytes("<html><body><script>window.close();</script></body></html>", "utf-8"))
    def log_message(self, fmt, *args):
        print(f"✅ Got a callback on WebServer")
        pass

def strava_oauth2(_cid, _secret, _cbackurl):
    _tkn = ''
    _url = f"https://www.strava.com/oauth/authorize?client_id={_cid}&response_type=code&redirect_uri={_cbackurl}&approval_prompt=force&scope=activity:read_all"
    # spin up oAuth2 httpd listerner
    server = HTTPServer((_cbackurl.split("/")[-3:-1][1].split(":")[0], int(_cbackurl.split("/")[-3:-1][1].split(":")[1])), WebRequestHandler)
    # redirect user to the page:
    webbrowser.open_new(_url)
    # listen for callback
    server.handle_request()
    _url2 = f"https://www.strava.com/oauth/token?client_id={_cid}&client_secret={_secret}&code={oauthcode}&grant_type=authorization_code"
    x = requests.post(_url2)
    _tkn = x.json()['access_token']
    return _tkn

def main(args):
    if not args.ids and not args.since:
        print(f"⚠️ Failed fetching data: either activity ID(s) or --since flag is required.")
        exit(1)

    # FIXME: Ride works, check for Walk, Hike, etc.!
    activity_types = ['Ride','Walk','Hike']
    type = str(args.type).title()
    if type not in activity_types:
        print(f"⚠️ Failed fetching data: type {args.type} is not allowed. Permitted values: {str(activity_types)}.")
        exit(1)

    # authorisation workflow
    authdelta = 21600 # 6 * 3600
    try:
        authstat = os.stat('.auth')
        authdelta = authstat.st_mtime
    except FileNotFoundError:
        open('.auth', 'a').close()

    if (time.time() - authdelta) < 21600:
        with open('.auth','r') as f:
            line = f.readline()
            f.close()
        if len(line)>0:
            access_token = line
            print(f"✅ Auth token retrieved sucessfully")
        else:
            print(f"⚠️ Failed retrieving auth token")
    else:
        access_token = strava_oauth2(_cid=OAUTH_CLIENT_ID, _secret=OAUTH_CLIENT_SECRET, _cbackurl=OAUTH_CBACK_URL)
        with open('.auth','w') as f: 
            f.write(access_token)
            f.close()
        print(f"✅ Auth token stored sucessfully")

    global headers
    headers = {"Authorization": f"Bearer {access_token}"}
    print(f"✅ Log in successful")

    # Ensure subfolder
    os.makedirs("Rides", exist_ok=True)

    if args.since:
        timestamp=time.mktime(datetime.strptime(args.since, "%Y-%m-%d").timetuple())
        activities_list = fetch_activites(_since=timestamp, _type=type)

    if args.ids:
        activities_list = args.ids.split(',')

    l = len(activities_list)
    if l < 1:
        print(f"⚠️ Failed fetching data: Require more than 1 activity to fetch any data.")

    for activity_id in activities_list:
        if args.verbose: print (f"ID: {activity_id}")
        summary, poly_line, photos = fetch_activity_data(activity_id)
        # 'summary' variable will equal to activity_id (type: string) if fetch failed
        # else it will be type of dict
        # Hack/workaround untill we create custom exceptions that allow us to handle this
        if isinstance(summary, str):
            print(f"⚠️ Skipping activity ID {activity_id} due to fetching issues")
            continue

        # save activity if longer than DescrLimit parameter.
        if len(summary['description_parsed']) >= args.descrlimit:
            markdown_post = generate_markdown(_summary = summary,
                                            _polyline = poly_line,
                                            _photos = photos)
            filename = f"Rides/{summary['start_date']}-{summary['id']}.md"
            save_markdown(_content=markdown_post, _fname=filename)

        else:
            print(f"⏭️ Skipping {activity_id} — description too short.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Strava2.MD", description="Pull Strava activity information into nice hugo-compatibile .md file."
    )
    parser.add_argument(
        "-i",
        "--ids",
        action="store",
        type=str,
        help="Comma-separated list of activity IDs (no spaces, example: 1,2,3,4,5). Overrides -s if both used at same time.",
    )
    parser.add_argument(
        "-s",
        "--since",
        action="store",
        type=str,
        help="Fetch after (including) that date, if your API budget alows. (example: 2025-01-01). Gets overriden by -i if both used at same time."
    )
    parser.add_argument(
        "-t",
        "--type",
        action="store",
        default="Ride",
        type=str,
        help="Fetch type of activities (default: 'Ride'). Used with -s."
    )
    parser.add_argument(
        "--descrlimit",
        action="store",
        default=200,
        type=int,
        help="Minimal length of description to create a .md file. Defaults to 200."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")

    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
    if args.verbose:
        VERBOSE=True
    main(args)
