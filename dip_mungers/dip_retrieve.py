import argparse
import configparser
import csv
import os
import sys
import tarfile

from amclient import AMClient


class ConfigParsingError(Exception):
    pass


DESKTOP_PATH = os.path.expanduser("~/Desktop")

# Suffix length includes leading dash separator.
DIP_UUID_SUFFIX_LENGTH = 37

# Status for stored AIPs in Storage Service.
UPLOADED = "UPLOADED"

USER_DIRECTORY = os.path.expanduser("~")
CONFIG_FILE = os.path.join(USER_DIRECTORY, ".dip-mungers")

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

try:
    USERNAME = config["GENERAL"]["USERNAME"]
    DEV_URL = config["STORAGE_SERVICE"]["DEV_URL"]
    DEV_API_KEY = config["STORAGE_SERVICE"]["DEV_API_KEY"]
    PROD_URL = config["STORAGE_SERVICE"]["PROD_URL"]
    PROD_API_KEY = config["STORAGE_SERVICE"]["PROD_API_KEY"]
except KeyError as err:
    error_msg = "Config file at {} missing expected field: {}".format(CONFIG_FILE, err)
    raise ConfigParsingError(error_msg)


def _make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dev",
        help="Download DIP from development Storage Service",
        action="store_true",
    )
    parser.add_argument("aip_uuid", help="AIP UUID")

    return parser


def write_csv(local_dip_path, dip_basename):
    """Write CSV file into DIP's objects directory.

    :param local_dip_path: Path to DIP on user's desktop (str)
    :param dip_basename: DIP basename (str)
    """
    transfer_name = dip_basename[:-DIP_UUID_SUFFIX_LENGTH]
    csv_path = local_dip_path + "/objects/" + transfer_name + ".csv"
    objects_list = os.listdir(local_dip_path + "/objects")
    with open(csv_path, "w", newline="\n") as csvfile:
        objects_writer = csv.writer(csvfile, delimiter=",")
        objects_writer.writerow(["filename", "slug"])
        for x in objects_list:
            objects_writer.writerow([x])


def fetch_dip_information(amclient, aip_uuid):
    """Fetch information about an AIP's DIP from the Storage Service.

    :param amclient: AMclient object instance
    :param aip_uuid: AIP UUID

    :returns: DIP dictionary from Storage Service
    """
    try:
        amclient.aip_uuid = aip_uuid
        dips = amclient.aip2dips()
    # amclient throws a TypeError on bad connection to Storage Service.
    except (ConnectionError, TypeError):
        print("Error: Unable to connect to Storage Service. Check URL and credentials?")
        sys.exit(1)

    uploaded_dips = [dip for dip in dips if dip["status"] == UPLOADED]

    if not uploaded_dips:
        print("Error: No DIPs found for AIP {}".format(aip_uuid))
        sys.exit(1)

    dip = uploaded_dips[0]

    if len(uploaded_dips) > 1:
        print(
            "Multiple DIPs found for AIP {}. Retrieving first one: {}".format(
                aip_uuid, dip["uuid"]
            )
        )

    return dip


def download_dip(amclient, dip_uuid, dip_basename):
    """Download and extract DIP to desktop.

    :param amclient: AMclient object instance
    :param dip_uuid: DIP UUID (str)
    :param dip_basename: DIP basename (str)

    :returns local_dip_path: Path to DIP on desktop (str)
    """
    amclient.directory = DESKTOP_PATH
    amclient.download_package(uuid=dip_uuid,)

    local_dip_path_tar = os.path.join(DESKTOP_PATH, dip_basename + ".tar")
    local_dip_path = os.path.join(DESKTOP_PATH, dip_basename)

    if not os.path.exists(local_dip_path_tar):
        print("Error: Unable to download DIP {} from Storage Service".format(dip_uuid))
        sys.exit(1)

    # Extract DIP from tarball.
    with tarfile.open(local_dip_path_tar) as dip_tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(dip_tar, DESKTOP_PATH)

    if not os.path.exists(local_dip_path):
        print("Error: Unable to extract DIP from tarball")
        sys.exit(1)

    # Delete tarball.
    try:
        os.remove(local_dip_path_tar)
    except OSError as err:
        print("Warning: Unable to delete .tar from desktop: {}".format(err))

    return local_dip_path


def main():
    parser = _make_parser()
    args = parser.parse_args()

    if not os.path.exists(CONFIG_FILE):
        error_msg = "DIP Mungers configuration file expected but not found at {}".format(CONFIG_FILE)
        raise FileNotFoundError(error_msg)

    storage_service_url = PROD_URL
    api_key = PROD_API_KEY
    if args.dev:
        storage_service_url = DEV_URL
        api_key = DEV_API_KEY

    amclient = AMClient(
        ss_url=storage_service_url, ss_user_name=USERNAME, ss_api_key=api_key,
    )

    dip = fetch_dip_information(amclient, args.aip_uuid)
    dip_basename = os.path.basename(dip["current_path"])

    print("Downloading DIP...")
    local_dip_path = download_dip(amclient, dip["uuid"], dip_basename)

    print("Writing CSV...")
    write_csv(local_dip_path, dip_basename)

    print("Done")


if __name__ == "__main__":
    main()
