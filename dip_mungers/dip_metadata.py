import argparse
import configparser
import csv
import glob
import os
import re
import xmltodict

from agentarchives import atom


class ConfigParsingError(Exception):
    pass


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
    with open(metspath, "r") as metsfile:
        mets = metsfile.read()
    metstree = xmltodict.parse(mets)

    client = atom.AtomClient(atom_url, api_token, 443)

    # Upload file metadata.
    for dip_name in dip_names:
        dip_name["filename"] = re.sub(
            r"^\S+?-\S+?-\S+?-\S+?-\S+?-", "", dip_name["filename"]
        )
        for techMD in metstree["mets:mets"]["mets:amdSec"]:
            try:
                size = ""
                object_type = ""
                file_uuid = ""
                if (
                    os.path.splitext(
                        techMD["mets:techMD"]["mets:mdWrap"]["mets:xmlData"][
                            "premis:object"
                        ]["premis:objectCharacteristics"][
                            "premis:objectCharacteristicsExtension"
                        ][
                            "rdf:RDF"
                        ][
                            "rdf:Description"
                        ][
                            "System:FileName"
                        ]
                    )[0]
                    == os.path.splitext(dip_name["filename"])[0]
                ):
                    size = techMD["mets:techMD"]["mets:mdWrap"]["mets:xmlData"][
                        "premis:object"
                    ]["premis:objectCharacteristics"][
                        "premis:objectCharacteristicsExtension"
                    ][
                        "rdf:RDF"
                    ][
                        "rdf:Description"
                    ][
                        "System:FileSize"
                    ]
                    object_type = techMD["mets:techMD"]["mets:mdWrap"]["mets:xmlData"][
                        "premis:object"
                    ]["premis:objectCharacteristics"]["premis:format"][
                        "premis:formatDesignation"
                    ][
                        "premis:formatName"
                    ]
                    file_uuid = techMD["mets:techMD"]["mets:mdWrap"]["mets:xmlData"][
                        "premis:object"
                    ]["premis:objectIdentifier"]["premis:objectIdentifierValue"]
            except:
                pass

        try:
            client.add_digital_object(
                dip_name["slug"],
                title=dip_name["filename"],
                size=size,
                object_type=object_type,
                file_uuid=file_uuid,
            )
            print("Uploaded metadata for {}".format(dip_name["filename"]))
        except NameError as err:
            print("Couldn't upload metadata for {}: {}".format(dip_name["filename"], err))


if __name__ == "__main__":
    main()
