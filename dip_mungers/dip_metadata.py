import argparse
import configparser
import csv
import glob
import lxml
import metsrw
import os
import re

from agentarchives import atom


class ConfigParsingError(Exception):
    pass


UUID4_PREFIX_LENGTH = 33

USER_DIRECTORY = os.path.expanduser("~")
CONFIG_FILE = os.path.join(USER_DIRECTORY, ".dip-mungers")

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

if not os.path.exists(CONFIG_FILE):
    error_msg = "DIP Mungers configuration file expected but not found at {}".format(CONFIG_FILE)
    raise FileNotFoundError(error_msg)

try:
    ATOM_URL_DEV = config["ATOM"]["DEV_URL"]
    ATOM_API_KEY_DEV = config["ATOM"]["DEV_API_KEY"]
    ATOM_URL_PROD = config["ATOM"]["PROD_URL"]
    ATOM_API_KEY_PROD = config["ATOM"]["PROD_API_KEY"]
except KeyError as err:
    error_msg = "Config file at {} missing expected field: {}".format(CONFIG_FILE, err)
    raise ConfigParsingError(error_msg)


def _make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dev",
        help="Upload DIP metadata to development AtoM",
        action="store_true",
    )
    parser.add_argument("dip_path", help="Path to local DIP")

    return parser


def uuid_from_filename(filename):
    UUID_REGEX = r"[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}"
    UUID4_HEX = re.compile(UUID_REGEX, re.I)
    match = re.match(UUID4_HEX, filename)
    if match:
        return match.group(0)
    return None


def main():
    parser = _make_parser()
    args = parser.parse_args()

    atom_url = ATOM_URL_PROD
    api_token = ATOM_API_KEY_PROD
    if args.dev:
        atom_url = ATOM_URL_DEV
        api_token = ATOM_API_KEY_DEV

    local_dip_path = os.path.abspath(args.dip_path)
    dip_names = []

    # Gather DIP object metadata from CSV file.
    csvpath = glob.glob(local_dip_path + "/objects/*.csv")[0]
    with open(csvpath, "r") as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            new_row = {}
            for key, value in row.items():
                if "filename" in key:
                    new_row["filename"] = value
                if "slug" in key:
                    new_row["slug"] = value
            dip_names.append(new_row)

    # Parse METS file.
    metspath = glob.glob(local_dip_path + "/METS*.xml")[0]
    try:
        mets = metsrw.METSDocument.fromfile(metspath)
    except (AttributeError, lxml.etree.Error) as err:
        print("Unable to parse METS file {}: {}".format(metspath, err))

    client = atom.AtomClient(atom_url, api_token, 443)

    # Upload file metadata.
    for dip_name in dip_names:
        file_uuid = uuid_from_filename(dip_name["filename"])
        if not file_uuid:
            continue

        fs_entry = mets.get_file(file_uuid=file_uuid)
        if not fs_entry:
            continue

        try:
            premis_object = fs_entry.get_premis_objects()[0]
        except IndexError:
            continue

        filename = fs_entry.label
        size = ""
        file_format = ""

        try:
            size = premis_object.size
            file_format = premis_object.format_name
        except AttributeError:
            pass

        try:
            client.add_digital_object(
                dip_name["slug"],
                title=filename,
                usage="Offline",
                size=size,
                object_type=file_format,
                file_uuid=file_uuid,
            )
            print("Uploaded metadata for {}".format(filename))
        except NameError as err:
            print("Couldn't upload metadata for {}: {}".format(filename, err))


if __name__ == "__main__":
    main()
