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
on: [push]
jobs:
  mkgmap:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository code
        uses: actions/checkout@v3

      - name: Cache osmosis
        id: cache-osmosis
        uses: actions/cache@v3
        with:
          path: osmosis-0.48.3.zip
          key: osmosis-0.48.3.zip
      - name: Cache geofabrik-belgium
        id: cache-geofabrik-belgium
        uses: actions/cache@v3
        with:
          path: belgium-220706.osm.pbf
          key: belgium-220706.osm.pbf
      - name: Cache geofabrik-netherlands
        id: cache-geofabrik-netherlands
        uses: actions/cache@v3
        with:
          path: netherlands-220706.osm.pbf
          key: netherlands-220706.osm.pbf
      - name: Cache geofabrik-luxembourg
        id: cache-geofabrik-luxembourg
        uses: actions/cache@v3
        with:
          path: luxembourg-220706.osm.pbf
          key: luxembourg-220706.osm.pbf
      - name: Cache bounds
        id: cache-bounds
        uses: actions/cache@v3
        with:
          path: bounds-20220701.zip
          key: bounds-20220701.zip
      - name: Cache sea
        id: cache-sea
        uses: actions/cache@v3
        with:
          path: sea-20220707001500.zip
          key: sea-20220707001500.zip
      - name: Cache mkgmap
        id: cache-mkgmap
        uses: actions/cache@v3
        with:
          path: mkgmap-r4904.zip
          key: mkgmap-r4904.zip
      - name: Cache splitter
        id: cache-splitter
        uses: actions/cache@v3
        with:
          path: splitter-r652.zip
          key: splitter-r652.zip
      - name: Cache M31
        id: cache-M31
        uses: actions/cache@v3
        with:
          path: 300ab8-114a217-526c5f822db40.zip
          key: 300ab8-114a217-526c5f822db40.zip
      - name: Cache M32
        id: cache-M32
        uses: actions/cache@v3
        with:
          path: 300ab9-1bb1c19-526c61e487b40.zip
          key: 300ab9-1bb1c19-526c61e487b40.zip
      - name: Cache N31
        id: cache-N31
        uses: actions/cache@v3
        with:
          path: 300aef-1f5128-526ca57fcfc40.zip
          key: 300aef-1f5128-526ca57fcfc40.zip
      - name: Cache N32
        id: cache-N32
        uses: actions/cache@v3
        with:
          path: 300af0-a3ea25-526ca661d5180.zip
          key: 300af0-a3ea25-526ca661d5180.zip
      - name: Cache Hoehendaten_Freizeitkarte_NLD
        id: cache-Hoehendaten_Freizeitkarte_NLD
        uses: actions/cache@v3
        with:
          path: 17d90c-5c1046fe2b380.zip
          key: 17d90c-5c1046fe2b380.zip
      - name: Cache cities15000
        id: cache-cities15000
        uses: actions/cache@v3
        with:
          path: 2542be-5e32d0145523c.zip
          key: 2542be-5e32d0145523c.zip

      - name: Download osmosis
        if: steps.cache-osmosis.outputs.cache-hit != 'true'
        run: wget -O osmosis-0.48.3.zip https://github.com/openstreetmap/osmosis/releases/download/0.48.3/osmosis-0.48.3.zip
      - name: Download geofabrik-belgium
        if: steps.cache-geofabrik-belgium.outputs.cache-hit != 'true'
        run: wget -O belgium-220706.osm.pbf https://download.geofabrik.de/europe/belgium-220706.osm.pbf
      - name: Download geofabrik-netherlands
        if: steps.cache-geofabrik-netherlands.outputs.cache-hit != 'true'
        run: wget -O netherlands-220706.osm.pbf https://download.geofabrik.de/europe/netherlands-220706.osm.pbf
      - name: Download geofabrik-luxembourg
        if: steps.cache-geofabrik-luxembourg.outputs.cache-hit != 'true'
        run: wget -O luxembourg-220706.osm.pbf https://download.geofabrik.de/europe/luxembourg-220706.osm.pbf
      - name: Download bounds
        if: steps.cache-bounds.outputs.cache-hit != 'true'
        run: wget -O bounds-20220701.zip http://osm.thkukuk.de/data/bounds-20220701.zip
      - name: Download sea
        if: steps.cache-sea.outputs.cache-hit != 'true'
        run: wget -O sea-20220707001500.zip http://osm.thkukuk.de/data/sea-20220707001500.zip
      - name: Download mkgmap
        if: steps.cache-mkgmap.outputs.cache-hit != 'true'
        run: wget -O mkgmap-r4904.zip https://www.mkgmap.org.uk/mkgmap-r4904.zip
      - name: Download splitter
        if: steps.cache-splitter.outputs.cache-hit != 'true'
        run: wget -O splitter-r652.zip https://www.mkgmap.org.uk/splitter-r652.zip
      - name: Download M31
        if: steps.cache-M31.outputs.cache-hit != 'true'
        run: wget -O 300ab8-114a217-526c5f822db40.zip http://www.viewfinderpanoramas.org/dem3/M31.zip
      - name: Download M32
        if: steps.cache-M32.outputs.cache-hit != 'true'
        run: wget -O 300ab9-1bb1c19-526c61e487b40.zip http://www.viewfinderpanoramas.org/dem3/M32.zip
      - name: Download N31
        if: steps.cache-N31.outputs.cache-hit != 'true'
        run: wget -O 300aef-1f5128-526ca57fcfc40.zip http://www.viewfinderpanoramas.org/dem3/N31.zip
      - name: Download N32
        if: steps.cache-N32.outputs.cache-hit != 'true'
        run: wget -O 300af0-a3ea25-526ca661d5180.zip http://www.viewfinderpanoramas.org/dem3/N32.zip
      - name: Download Hoehendaten_Freizeitkarte_NLD
        if: steps.cache-Hoehendaten_Freizeitkarte_NLD.outputs.cache-hit != 'true'
        run: wget -O 17d90c-5c1046fe2b380.zip http://develop.freizeitkarte-osm.de/ele_20_100_500/Hoehendaten_Freizeitkarte_NLD.osm.pbf
      - name: Download cities15000
        if: steps.cache-cities15000.outputs.cache-hit != 'true'
        run: wget -O 2542be-5e32d0145523c.zip http://download.geonames.org/export/dump/cities15000.zip
      - name: Extract osmosis
        run: unzip -d osmosis osmosis-0.48.3.zip
      - name: Merge extracts
        run: >
          osmosis/bin/osmosis
          --rbf belgium-220706.osm.pbf
          --rbf netherlands-220706.osm.pbf
          --rbf luxembourg-220706.osm.pbf
          --rbf 17d90c-5c1046fe2b380.zip
          --merge
          --merge
          --merge
          --wb merged.osm.pbf
      - name: Extract splitter
        run: unzip -d splitter splitter-r652.zip
      - name: Extract cities
        run: unzip 2542be-5e32d0145523c.zip
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
          --polygon-file=benelux.poly
          merged.osm.pbf
      - name: Extract mkgmap
        run: unzip -d mkgmap mkgmap-r4904.zip
      - name: Extract dem files
        run: >
          for Z in
          300ab8-114a217-526c5f822db40.zip
          300ab9-1bb1c19-526c61e487b40.zip
          300aef-1f5128-526ca57fcfc40.zip
          300af0-a3ea25-526ca661d5180.zip
          ; do
          unzip -d map_with_dem_files $Z ;
          done
      - name: Move DEM files
        run: mv map_with_dem_files/???/*.hgt map_with_dem_files/
      - name: Rename sea.zip
        run: mv sea-20220707001500.zip sea.zip
      - name: Rename bounds.zip
        run: mv bounds-20220701.zip bounds.zip
      - name: mkgmap
        run: >
          java
          -Xms1024m
          -Xmx1024m
          -jar mkgmap/*/mkgmap.jar
          -c osm_bnl.args
          -c splitted/template.args
          10010.txt
      - name: Rename sea.zip
        run: mv sea.zip sea-20220707001500.zip
      - name: Rename bounds.zip
        run: mv bounds.zip bounds-20220701.zip
      - name: Upload gmapsupp.img
        uses: actions/upload-artifact@v3
        with:
          name: gmapsupp.img
          path: gmapsupp.img
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
        self.nonversioned(
            "http://develop.freizeitkarte-osm.de/ele_20_100_500/"
            f"Hoehendaten_Freizeitkarte_{regions['hoehendaten']}.osm.pbf"
        )
        self.nonversioned("http://download.geonames.org/export/dump/cities15000.zip")

    def osmosis(self):
        """
        Find latest osmosis
        """
        request_get = requests.get(
            "https://api.github.com/repos/openstreetmap/osmosis/releases/latest"
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
        request_get = requests.get(f"{thkukuk}/")

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
        request_get = requests.get(f"{self.mkgmaporguk}/download/mkgmap.html")
        matched = re.search(r"/download/(mkgmap-r[0-9]+.zip)", request_get.text)
        if matched:
            filename = matched.group(1)
            self.downloads["mkgmap"] = {
                "url": f"{self.mkgmaporguk}/{filename}",
                "filename": filename,
            }

    def splitter(self):
        """
        Find latest splitter
        """
        request_get = requests.get(f"{self.mkgmaporguk}/download/splitter.html")
        matched = re.search(r"/download/(splitter-r[0-9]+.zip)", request_get.text)
        if matched:
            filename = matched.group(1)
            self.downloads["splitter"] = {
                "url": f"{self.mkgmaporguk}/{filename}",
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
        downloads = Downloads(json.load(regions_file))

    template = env.from_string(GITHUB_ACTION)
    with open(".github/workflows/mkgmap.yml", "w", encoding="utf8") as workflow:
        workflow.write(template.render(downloads=downloads.downloads))
