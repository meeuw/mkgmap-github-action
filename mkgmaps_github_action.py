#!/usr/bin/env python
"""
Render template
"""
import datetime
import json
import re
import os.path
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape


GITHUB_ACTION = """name: Generate OpenStreetMap Garmin maps
on:
  push:
    branches:
      - main
jobs:
  mkgmap:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository code
        uses: actions/checkout@v3
{% for name, download in downloads.items() %}
      - name: Cache {{ name }}
        id: cache-{{ name }}
        uses: actions/cache@v3
        with:
          path: {{ download["filename"] }}
          key: {{ download["filename"] }}
{%- endfor %}
{% for name, download in downloads.items() %}
      - name: Download {{ name }}
        if: steps.cache-{{ name }}.outputs.cache-hit != 'true'
        run: wget -O {{ download.filename }} {{ download.url }}
{%- endfor %}
      - name: Extract osmosis
        run: unzip -d osmosis {{ downloads["osmosis"]["filename"] }}
      - name: Merge extracts
        run: >
          osmosis/bin/osmosis
{%- for country in regions["countries"] %}
          --rbf {{ downloads["geofabrik-" ~ country]["filename"] }}
{%- endfor %}
{%- for hoehendaten in regions["hoehendaten"] %}
          --rbf {{ downloads["Hoehendaten_Freizeitkarte_" ~ hoehendaten]["filename"] }}
{%- endfor %}
{%- for _ in range(regions["countries"]|length + regions["hoehendaten"]|length - 1) %}
          --merge
{%- endfor %}
          --wb merged.osm.pbf
      - name: Extract splitter
        run: unzip -d splitter {{ downloads["splitter"]["filename"] }}
      - name: Extract cities
        run: unzip {{ downloads["cities15000"]["filename"] }}
      - name: Splitter
        run: >
          java
          -Xmx4096m
          -jar splitter/*/splitter.jar
          --output=pbf
          --output-dir=splitted
          --max-nodes=1400000
          --mapid=10010001
          --geonames-file=cities15000.txt
          --polygon-file=resources/benelux.poly
          merged.osm.pbf
      - name: Extract mkgmap
        run: unzip -d mkgmap {{ downloads["mkgmap"]["filename"] }}
      - name: Extract dem files
        run: >
          for Z in
{%- for dem in regions["DEM"] %}
          {{ downloads[dem]["filename"] }}
{%- endfor %}
          ; do
          unzip -d map_with_dem_files $Z ;
          done
      - name: Move DEM files
        run: mv map_with_dem_files/???/*.hgt map_with_dem_files/
      - name: Rename sea.zip
        run: mv {{ downloads["sea"]["filename"] }} sea.zip
      - name: Rename bounds.zip
        run: mv {{ downloads["bounds"]["filename"] }} bounds.zip
      - name: mkgmap
        run: >
          java
          -Xms1024m
          -Xmx1024m
          -jar mkgmap/*/mkgmap.jar
          -c "styles/Openfietsmap full/mkgmap.args"
          -c splitted/template.args
          "typ/Openfietsmap lite/20011.txt"
      - name: Rename sea.zip
        run: mv sea.zip {{ downloads["sea"]["filename"] }}
      - name: Rename bounds.zip
        run: mv bounds.zip {{ downloads["bounds"]["filename"] }}
      - uses: "marvinpinto/action-automatic-releases@v1.2.1"
        with:
          repo_token: "${{ '{{ secrets.PAT }}' }}"
          automatic_release_tag: "latest"
          prerelease: false
          files: gmapsupp.img
"""


class Downloads:
    """
    Find all download urls and unique filenames
    """

    def __init__(self, regions):
        self.downloads = {}
        self.osmosis()
        self.mkgmaporguk = "https://www.mkgmap.org.uk"
        for country in regions["countries"]:
            self.geofabrik_europe(country)
        self.bounds_and_sea()
        self.mkgmap()
        self.splitter()
        for dem in regions["DEM"]:
            self.nonversioned(f"http://www.viewfinderpanoramas.org/dem3/{dem}.zip")
        for hoehendaten in regions["hoehendaten"]:
            self.nonversioned(
                "http://develop.freizeitkarte-osm.de/ele_20_100_500/"
                f"Hoehendaten_Freizeitkarte_{hoehendaten}.osm.pbf"
            )
        self.nonversioned("http://download.geonames.org/export/dump/cities15000.zip")

    def osmosis(self):
        """
        Find latest osmosis
        """
        request_get = requests.get(
            "https://api.github.com/repos/openstreetmap/osmosis/releases/latest",
            timeout=3
        )
        download_json = request_get.json()
        name = download_json["name"]
        self.downloads["osmosis"] = {
            "url": "https://github.com/openstreetmap/osmosis/releases/download/"
            f"{name}/osmosis-{name}.zip",
            "filename": f"osmosis-{name}.zip",
        }

    def geofabrik_europe(self, country):
        """
        Find latest extract
        """
        check = datetime.datetime.now()
        for _ in range(10):
            filename = f'{country}-{check.strftime("%y%m%d")}.osm.pbf'
            url = f"https://download.geofabrik.de/europe/{filename}"
            request_head = requests.head(url)
            if request_head.ok:
                self.downloads[f"geofabrik-{country}"] = {
                    "url": url,
                    "filename": filename,
                }
                break
            check -= datetime.timedelta(days=1)

    def bounds_and_sea(self):
        """
        Find latest bounds and sea zip files
        """
        thkukuk = "http://osm.thkukuk.de/data"
        request_get = requests.get(f"{thkukuk}/", timeout=3)

        check = datetime.datetime.now()
        for _ in range(10):
            filename = f'bounds-{check.strftime("%Y%m%d")}.zip'
            if filename in request_get.text:
                self.downloads["bounds"] = {
                    "url": f"{thkukuk}/{filename}",
                    "filename": filename,
                }
                break
            check -= datetime.timedelta(days=1)

        check = datetime.datetime.now()
        for _ in range(10):
            filename = f'sea-{check.strftime("%Y%m%d")}'
            matched = re.search(f"({filename}[0-9]*.zip)", request_get.text)
            if matched:
                filename = matched.group(1)
                self.downloads["sea"] = {
                    "url": f"{thkukuk}/{filename}",
                    "filename": filename,
                }
                break

            check -= datetime.timedelta(days=1)

    def mkgmap(self):
        """
        Find latest mkgmap
        """
        request_get = requests.get(f"{self.mkgmaporguk}/download/mkgmap.html", timeout=3)
        matched = re.search(r"/download/(mkgmap-r[0-9]+.zip)", request_get.text)
        if matched:
            filename = matched.group(1)
            self.downloads["mkgmap"] = {
                "url": f"{self.mkgmaporguk}/download/{filename}",
                "filename": filename,
            }

    def splitter(self):
        """
        Find latest splitter
        """
        request_get = requests.get(f"{self.mkgmaporguk}/download/splitter.html", timeout=3)
        matched = re.search(r"/download/(splitter-r[0-9]+.zip)", request_get.text)
        if matched:
            filename = matched.group(1)
            self.downloads["splitter"] = {
                "url": f"{self.mkgmaporguk}/download/{filename}",
                "filename": filename,
            }

    def nonversioned(self, url):
        """
        Make non versioned files versioned using ETag
        """
        request_head = requests.head(url)
        self.downloads[os.path.basename(url).split(".")[0]] = {
            "url": url,
            "filename": f"{request_head.headers['ETag'][1:-1]}.zip",
        }


def main():
    """
    Main function
    """
    env = Environment(
        loader=FileSystemLoader(""),
        autoescape=select_autoescape(),
        keep_trailing_newline=True,
    )

    with open("regions.json", encoding="utf8") as regions_file:
        regions = json.load(regions_file)

    downloads = Downloads(regions)

    template = env.from_string(GITHUB_ACTION)
    with open(".github/workflows/mkgmap.yml", "w", encoding="utf8") as workflow:
        workflow.write(template.render(downloads=downloads.downloads, regions=regions))
