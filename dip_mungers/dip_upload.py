import argparse
import configparser
import sys
import os
import getpass

from paramiko import AutoAddPolicy
from paramiko_jump import SSHJumpClient, simple_auth_handler
from scp import SCPClient, SCPException


class ConfigParsingError(Exception):
    pass


USER_DIRECTORY = os.path.expanduser("~")
CONFIG_FILE = os.path.join(USER_DIRECTORY, ".dip-mungers")

config = configparser.ConfigParser()
config.read(CONFIG_FILE)

try:
    USERNAME = config["GENERAL"]["USERNAME"]
    JUMP_SERVER_HOSTNAME = config["GENERAL"]["JUMP_SERVER_HOSTNAME"]
    JUMP_SERVER_PORT = config["GENERAL"]["JUMP_SERVER_PORT"]
    ATOM_HOSTNAME_DEV = config["ATOM"]["DEV_HOSTNAME"]
    ATOM_HOSTNAME_PROD = config["ATOM"]["PROD_HOSTNAME"]
except KeyError as err:
    error_msg = "Config file at {} missing expected field: {}".format(CONFIG_FILE, err)
    raise ConfigParsingError(error_msg)


def _make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dev",
        help="Upload DIP to development AtoM",
        action="store_true",
    )
    parser.add_argument(
        "--nginx",
        help="Use nginx AtoM user for upload (requires ssh key on jump server)",
        action="store_true"
    )
    parser.add_argument("dip_path", help="Path to local DIP")

    return parser


def dummy_sanitizer(s):
    return s


def main():
    parser = _make_parser()
    args = parser.parse_args()

    if not os.path.exists(CONFIG_FILE):
        error_msg = "DIP Mungers configuration file expected but not found at {}".format(CONFIG_FILE)
        raise FileNotFoundError(error_msg)

    hostname = ATOM_HOSTNAME_PROD
    if args.dev:
        hostname = ATOM_HOSTNAME_DEV

    server_name = hostname.split(".")[0]
    if server_name.startswith("arm-"):
        server_name = server_name[4:]

    local_dip_path = os.path.abspath(args.dip_path)

    remote_dip_path = "/home/{}/{}/".format(USERNAME, os.path.basename(local_dip_path))

    # Connect through jump server.
    with SSHJumpClient(auth_handler=simple_auth_handler) as jumper:
        jumper.set_missing_host_key_policy(AutoAddPolicy())
        jumper.connect(
            hostname=JUMP_SERVER_HOSTNAME, port=JUMP_SERVER_PORT, username=USERNAME,
        )

        password = getpass.getpass("Password (again, for second hop): ")

        # Connect to target server.
        target = SSHJumpClient(jump_session=jumper)
        target.set_missing_host_key_policy(AutoAddPolicy())
        if args.nginx:
            target.connect(
                hostname=hostname,
                username="nginx",
            )
        else:
            target.connect(
                hostname=hostname,
                look_for_keys=False,
                username=USERNAME,
                password=password,
            )

        # Copy DIP to target server.
        print("Copying DIP to server...")
        try:
            with SCPClient(target.get_transport(), sanitize=dummy_sanitizer) as scp:
                scp.put(local_dip_path, remote_dip_path, recursive=True)
        except SCPException as err:
            print("Error copying DIP to target server: {}".format(err))

        # Run AtoM DIP import.
        print("Importing DIP into AtoM...")
        import_cmd = "php /usr/share/nginx/{}/src/symfony import:dip-objects {}".format(
            server_name, remote_dip_path
        )
        if not args.nginx:
            import_cmd = "sudo {}".format(import_cmd)
        stdin, stdout, stderr = target.exec_command(import_cmd, get_pty=True)
        while True:
            received = stdout.channel.recv(1024).decode("utf-8")
            if "sudo" in received:
                stdin.write("{}\n".format(password))
                stdin.flush()
            if not received:
                break
            sys.stdout.write(received)
            sys.stdout.flush()

        print("Deleting remote copy of DIP...")
        target.exec_command("rm -rf {}".format(remote_dip_path))

        print("Done")


if __name__ == "__main__":
    main()
