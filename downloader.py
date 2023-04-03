#!/usr/bin/python3

"""

    Written by BDeliers
    16 april 2020

    Edit edel-david on github
    03 april 2023 
    (the snapchat format changed to include location data in the html, breaking the parser)

    Under Apache 2.0 License

    This script downloads Snapchat's memories pictures and videos.

    To use it, download your Snapchat personnal data from https://accounts.snapchat.com/accounts/downloadmydata
    Then, launch this script by specifiying path to downloaded and unpacked Snapchat data folder
    The script will run and download each file in a subfolder Downloads in working directory
    (you should not include memories when downloading your data, because this script will do it)
    Example :
        ./downloader.py /home/john/Downloads/mydata~1234567891234


"""
from enum import Enum
from PIL import Image
import piexif
from fractions import Fraction

# HTML parser
from bs4 import BeautifulSoup

# HTTP requests
import requests

# To change creation time and make directory
from os import utime, mkdir

# To manage dates
from datetime import datetime
from time import mktime
from io import BytesIO

# Args
from sys import argv

class LatOrLong(Enum):
    Lat = 0
    Long = 1


def lat_str_to_exif_tup(value: str | float, lat_or_long: LatOrLong) -> tuple:
    """
    value has format "50.20302"
    """
    value = float(value)
    if lat_or_long == LatOrLong.Lat:
        loc = ["S", "N"]
    elif lat_or_long == LatOrLong.Long:
        loc = ["W", "E"]
    else:
        print("neither lat nor long")
        raise ValueError("err")
    if value < 0:

        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
    abs_value = abs(value)
    deg = int(abs_value)
    t1 = (abs_value - deg) * 60
    min = int(t1)
    sec = round((t1 - min) * 60, 5)
    deg_tub = Fraction(str(deg))
    min_frac = Fraction(str(min))
    sec_frac = Fraction(str(sec))

    return ((deg_tub.numerator,
             deg_tub.denominator),
            (min_frac.numerator,
             min_frac.denominator),
            (sec_frac.numerator,
             sec_frac.denominator)
             #loc
             )


# Open Snapchat data memories file, depending on args
try:
    file = open("{}/html/memories_history.html".format(argv[1]), "r")
    html = file.read()

except BaseException:
    print(
        "Invalid path to Snapchat data folder: {}/html/memories_history.html".format(argv[1]))
    exit()

# Creates Downloaded directory if needed
try:
    mkdir("./Downloaded")
except BaseException:
    pass

# Parse html
soup = BeautifulSoup(html, "html.parser")

# Get the picture's table
table = soup.find_all("tbody")[0]

photos = []
subDict = {}
i = 0

# For each line
for line in table.find_all("tr"):
    i = 0
    # For each cell
    for col in line.find_all("td"):
        # First cell is date of creation
        if i == 0:
            subDict["date"] = col.string
        # Second cell is type (PHOTO or VIDEO)
        elif i == 1:
            subDict["type"] = col.string
        # Third is a link to the download url
        elif i == 2:
            subDict["location"] = col.string

        elif i == 3:
            href = col.find("a").get("href")
            subDict["href"] = href[29:-3]

        i += 1

    # Store this data to the list
    photos.append(subDict)
    subDict = {}

# Remove first empty dict
photos.remove({})

images_amount = len(photos)
print("Now downloading {} files".format(images_amount))





# For each photos data
for index, photo in enumerate(photos[93:]):
    datestr=photo["date"]
    print(F"Next ! now downloading file {index} of {images_amount} ({datestr})")

    # Get the file url
    r = requests.post(
        photo["href"], headers={
            "Content-type": "application/x-www-form-urlencoded"})
    photo["download"] = r.text

    # Download the photo
    r = requests.get(photo["download"])

    # Get its creation time to timestamp
    time = datetime.strptime(photo["date"], "%Y-%m-%d %H:%M:%S %Z")
    modTime = mktime(time.timetuple())

    # Name the downloaded file
    name = "Snapchat-{}".format((photo["date"].replace(' ', '@'))[:-4])

    # Give it an extension
    if photo["type"] == "PHOTO" or photo["type"] == "Image":
        name += ".jpg"
        image = Image.open(BytesIO(r.content))

        latitude, longitude = photo["location"][21:].split(", ")
        latitude = float(latitude)
        longitude = float(longitude)
        # the exif data of snapchat images appears to be empty => create new dict instead of parse from file
        # exif_dict = piexif.load(image.info["exif"])
        exif_dict = {"GPS": {}, "Exif": {}}

        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = time.strftime(
            "%Y:%m:%d %H:%M:%S")

        exif_dict["GPS"][piexif.GPSIFD.GPSVersionID] = (2, 0, 0, 0)
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = b'N' if latitude >= 0 else b'S'
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = b'E' if longitude >= 0 else b'W'
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = lat_str_to_exif_tup(
            latitude, LatOrLong.Lat)
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = lat_str_to_exif_tup(
            longitude, LatOrLong.Long)
        exif_dict["GPS"][piexif.GPSIFD.GPSDateStamp] = time.strftime(
            "%Y:%m:%d")

        exif_bytes = piexif.dump(exif_dict)
        image.save(f"./Downloaded/{name}", exif=exif_bytes)

    elif photo["type"] == "VIDEO" or photo["type"] == "Video":
        name += ".mp4"
        open("./Downloaded/{}".format(name), "wb").write(r.content)

    else:
        print("unknown file type (not Image or Video)")
    # set location with exif data (pillow)

    # Store it to hard drive

    # Change its creation time
    utime(path="./Downloaded/{}".format(name), times=(modTime, modTime))
