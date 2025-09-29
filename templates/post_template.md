---
title: "%(TITLE)s"
date: "%(DATE)s"
draft: %(ISDRAFT)s
categories: %(CATS)s
tags: %(TAGS)s
---

%(HEADERIMG)s

## Info

- **Date:** %(DATE)s
- **Distance:** %(DISTANCE)s km
- **Elevation Gain:** %(ELE_GAIN)s m
- **Moving Time:** %(TIME_MOV)s
- **Elapsed Time:** %(TIME_ELA)s
- [%(TITLE)s on Strava](https://www.strava.com/activities/%(ID)s)

---

## Map

{{< rawhtml >}}
%(MAP)s
{{< /rawhtml >}}

---

## Description

%(DESCR)s

---

## Photos

%(PHOTOS)s

---

Data parsed automatically from [Strava](https://www.strava.com) using [Strava2.MD](https://github.com/b4d/strava2md) 
