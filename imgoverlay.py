from PIL import Image, ImageFont, ImageDraw

fin='./Rides/12355992457/photo_0.jpg'


# (x,y)
# -----> X koordinata (width)
# |
# |
# V Y koordinata (height)


img = Image.open(fin)
w = img.width
h = img.height
draw = ImageDraw.Draw(img)
maxsize=h/12
fontTitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(maxsize))
fontSubject = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(maxsize/2-1))
fontData = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(2/3.0*maxsize-1))
draw.text((20, 20), "GH://b4d/strava2md", (255,255,255), font=fontSubject)
draw.text((20, 2/3.0*h), "Titula Fure", (255,255,255), font=fontTitle)
draw.text((20, 7/8.0*h-15), "Ride", (255,255,255), font=fontSubject)
draw.text((20, 7/8.0*h+15), "30.7 km", (255,255,255), font=fontData)
draw.text((w/3.0, 7/8.0*h-15), "Gain", (255,255,255), font=fontSubject)
draw.text((w/3.0, 7/8.0*h+15), "1935 m", (255,255,255), font=fontData)
draw.text((2*w/3.0, 7/8.0*h-15), "Time", (255,255,255), font=fontSubject)
draw.text((2*w/3, 7/8.0*h+15), "2h 7min", (255,255,255), font=fontData)
img.save(fin.replace('0.jpg','0o.jpg'))