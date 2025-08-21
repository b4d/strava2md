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
from config import OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_CBACK_URL, HOME_COORDINATES
import math

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

def trim_by_radius_multi(poly_line, centers, radius_m=200):
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

def getStream(activity_id,type):
    stream_url = f"{STRAVA_API_ROOT}/activities/{activity_id}/streams"
    stream_params = {"keys": type, "key_by_type": "true"}
    stream_response = requests.get(stream_url, headers=headers, params=stream_params)

    if stream_response.status_code == 200:
        stream_data = stream_response.json()
    else:
        print(f"⚠️ Elevation stream fetch failed: {stream_response.status_code} {activity_id}")
    return stream_data

# Create MD links to all the photos on the activity
def list_photos(activity_id):
    photo_url = f"{STRAVA_API_ROOT}/activities/{activity_id}/photos?size=5000"
    response = requests.get(photo_url, headers=headers)

    if response.status_code == 200:
        photos = response.json()
        output = []

        for i, photo in enumerate(photos, 1):
            url = photo.get("urls", {}).get("5000")
            if url:
                output.append(f"![Ride Image {i}]({url})")

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

    # Manually prepare the polyline, elevation plot and photos
    height_stream = getStream(activity_id, 'altitude,distance')
    latlng_stream = getStream(activity_id, 'latlng,distance')

    # Be defensive about stream lengths
    alts   = height_stream.get('altitude', {}).get('data', []) or []
    latlng = latlng_stream.get('latlng',   {}).get('data', []) or []

    L = min(len(alts), len(latlng))
    poly_line = []
    for i in range(L):
        lat, lon = latlng[i]
        alt = alts[i]
        poly_line.append([lat, lon, alt])

    # Apply trimming / privacy zones
    poly_line = trim_by_radius_multi(poly_line, centers=HOME_COORDINATES, radius_m=200)

    photos = list_photos(activity_id)
    return activity_summary, poly_line, photos

def generate_markdown(_summary, _photos, _polyline, _ftemplate='post_template.md', _leaftemplate='leaflet_template.html'):
    with open(_ftemplate,'r') as t:
        post_template=t.read()
        t.close()

    with open(_leaftemplate,'r') as t:
        leaflet_template=t.read()
        t.close()

    _rideImg = f"\n![Ride Image]({_summary['image']})\n" if _summary['image'] else '> No photos taken, too busy hammering my pedals'
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
