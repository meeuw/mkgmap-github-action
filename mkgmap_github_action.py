#!/usr/bin/env python
"""
Render template
"""
import datetime
import json
import re
import os.path
import textwrap
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

import http.client
import logging

logging.basicConfig(level=logging.DEBUG)
http.client.HTTPConnection.debuglevel = 1


def format_run(value):
    if isinstance(value, str):
        return value
    else:
        return ">\n" + "\n".join(f'          {s}' for s in value)


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
      - id: {{ name }}
        uses: ./.github/actions/cached-download
        with:
          filename: {{ download.filename }}
          url: {{ download.url }}
{%- endfor %}
      - uses: actions/setup-java@v3
        with:
          distribution: 'oracle'
          java-version: '17'
{%- for name, command in commands %}
      - name: {{ name }}
        run: {{ command | format_run | safe }}
{%- endfor %}
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
            self.nonversioned(f"https://www.viewfinderpanoramas.org/dem3/{dem}.zip")
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
            timeout=3,
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
        for _ in range(200):
            filename = f'bounds-{check.strftime("%Y%m%d")}.zip'
            if filename in request_get.text:
                self.downloads["bounds"] = {
                    "url": f"{thkukuk}/{filename}",
                    "filename": filename,
                }
                break
            check -= datetime.timedelta(days=1)

        check = datetime.datetime.now()
        for _ in range(30):
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
        request_get = requests.get(
            f"{self.mkgmaporguk}/download/mkgmap.html", timeout=3
        )
        matched = re.search(r'(mkgmap-r[0-9]+.zip)', request_get.text)
        assert matched is not None
        filename = matched.group(1)
        self.downloads["mkgmap"] = {
            "url": f"{self.mkgmaporguk}/download/{filename}",
            "filename": filename,
        }

    def splitter(self):
        """
        Find latest splitter
        """
        request_get = requests.get(
            f"{self.mkgmaporguk}/download/splitter.html", timeout=3
        )
        matched = re.search(r'(splitter-r[0-9]+)', request_get.text)
        assert matched is not None
        filename = f"{matched.group(1)}.zip"
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


class Commands:
    def __init__(self, regions, downloads):
        self.regions = regions
        self.downloads = downloads
        self.commands = (
            ("Extract osmosis", 'unzip -d osmosis ${{ steps.osmosis.outputs.filename }}'),
            ("Merge extracts", self.osmosis()),
            ("Extract splitter", 'unzip -d splitter ${{ steps.splitter.outputs.filename }}'),
            ("Extract cities", 'unzip ${{ steps.cities15000.outputs.filename }}'),
            ("Splitter", (
                "java",
                "-Xmx4096m",
                "-jar splitter/*/splitter.jar",
                "--output=pbf",
                "--output-dir=splitted",
                "--max-nodes=1400000",
                "--mapid=10010001",
                "--geonames-file=cities15000.txt",
                "--polygon-file=resources/benelux.poly",
                "merged.osm.pbf",
            )),
            ("Extract mkgmap", 'unzip -d mkgmap ${{ steps.mkgmap.outputs.filename }}'),
            ("Extract dem files", self.extract_dem_files()),
            ("Move DEM files", "mv map_with_dem_files/???/*.hgt map_with_dem_files/"),
            ("Rename sea.zip", 'mv ${{ steps.sea.outputs.filename }} sea.zip'),
            ("Rename bounds.zip", 'mv ${{ steps.bounds.outputs.filename }} bounds.zip'),
            ("mkgmap", (
                "java",
                "-Xms4096m",
                "-Xmx4096m",
                "-jar mkgmap/*/mkgmap.jar",
                "-c \"styles/Openfietsmap full/mkgmap.args\"",
                "-c splitted/template.args",
                "\"typ/Openfietsmap lite/20011.txt\"",
            )),
            ("Rename sea.zip", 'mv sea.zip ${{ steps.sea.outputs.filename }}'),
            ("Rename bounds.zip", 'mv bounds.zip ${{ steps.bounds.outputs.filename }}'),
        )

    def osmosis(self):
        result = []
        result.append("osmosis/osmosis*/bin/osmosis")
        for country in self.regions["countries"]:
            result.append(f'--rbf ${{{{ steps.geofabrik-{country}.outputs.filename }}}}')
        for hoehendaten in self.regions["hoehendaten"]:
            result.append(
                f'--rbf ${{{{ steps.Hoehendaten_Freizeitkarte_{hoehendaten}.outputs.filename }}}}'
            )
        for _ in range(
            len(self.regions["countries"]) + len(self.regions["hoehendaten"]) - 1
        ):
            result.append(f"--merge")
        result.append("--wb merged.osm.pbf")
        return result

    def extract_dem_files(self):
        result = []
        result.append("for Z in")
        for dem in self.regions["DEM"]:
            result.append(f"${{{{ steps.{dem}.outputs.filename }}}}")
        result.append("; do")
        result.append("unzip -d map_with_dem_files $Z ;")
        result.append("done")
        return result


def main():
    """
    Main function
    """
    env = Environment(
        loader=FileSystemLoader(""),
        autoescape=select_autoescape(),
        keep_trailing_newline=True,
    )
    env.filters["format_run"] = format_run

    with open("regions.json", encoding="utf8") as regions_file:
        regions = json.load(regions_file)

    downloads = Downloads(regions)
    commands = Commands(regions, downloads.downloads)

    template = env.from_string(GITHUB_ACTION)
    with open(".github/workflows/mkgmap.yml", "w", encoding="utf8") as workflow:
        workflow.write(template.render(downloads=downloads.downloads, commands=commands.commands))
