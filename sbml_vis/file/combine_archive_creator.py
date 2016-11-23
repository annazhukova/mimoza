import mimetypes
import os
from zipfile import ZipFile, ZIP_DEFLATED

__author__ = 'anna'

MANIFEST = "http://identifiers.org/combine.specifications/omex-manifest"

extension2format = {
    ".xml": "http://identifiers.org/combine.specifications/sbml",
    ".sbml": "http://identifiers.org/combine.specifications/sbml",
    ".sbgn": "http://identifiers.org/combine.specifications/sbgn"
}


def archive(path, zip_file):
    location2format = {}
    with ZipFile(zip_file, 'w') as zip_f:
        for r, dirs, files in os.walk(path):
            for f in files:
                _, extension = os.path.splitext(f)
                f_format = extension2format[extension] if (extension in extension2format) else mimetypes.guess_type(f)[
                    0]
                if f_format:
                    file_path = os.path.join(r, f)
                    relative_file_path = os.path.relpath(file_path, path)
                    zip_f.write(file_path, relative_file_path, compress_type=ZIP_DEFLATED)
                    location2format[relative_file_path] = f_format

    manifest_file = os.path.join(path, "manifest.xml")
    with open(manifest_file, 'w+') as manifest:
        manifest.write('<?xml version="1.0" encoding="utf-8"?>\n')
        manifest.write('<omexManifest xmlns="http://identifiers.org/combine.specifications/omex-manifest">\n')
        manifest.write(
            '<content location="./manifest.xml" format="http://identifiers.org/combine.specifications/omex-manifest"/>\n')
        for location, f_format in location2format.items():
            manifest.write('<content location="%s" format="%s"/>\n' % (os.path.join(".", location), f_format))
        manifest.write('</omexManifest>')

    with ZipFile(zip_file, 'a') as zip_f:
        zip_f.write(manifest_file, os.path.relpath(manifest_file, path), compress_type=ZIP_DEFLATED)



