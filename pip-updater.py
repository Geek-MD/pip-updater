#!/usr/bin/env python3

# pip-updater v0.3.2
# File: pip-updater.py
# Description: Script designed to update pip packages

import argparse
import datetime
import json
import logging
import os
import subprocess
import textwrap
from datetime import datetime
import re
from crontab import CronTab


def get_config(local_path):
    with open(f'{local_path}/pip-updater.json', 'r') as config:
        data = json.load(config)
        prog_name_short = data['prog_name_short']
        prog_name_long = data['prog_name_long']
        version = data['version']
    return prog_name_short, prog_name_long, version


def argument_parser(program_name_short, program_name_long, ver):
    description = f"{program_name_long} is a python script which updates all outdated pip packages."
    epilog = (f"By default, {program_name_long} updates all outdated pip packages without asking for confirmation.\nIf "
              f"you want to exclude some packages from updating or want to freeze a package into a specific version "
              f"without updating) it, you must populate the file named \"exceptions.txt\", adding the name of the "
              f"desired package, one package per line.\nIn order to freeze a pip package into a specific version, use "
              f"\"pkg_name==version\" format. Alternatively you can use the \"--add-file\" option to add packages to "
              f"\"exceptions.txt\" via command line.")
    parser = argparse.ArgumentParser(
        prog=f"{program_name_short}",
        description=textwrap.dedent(f"{description}"),
        epilog=f"{epilog}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {ver}",
        help="show %(prog)s version information and exit.",
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="show list of outdated packages."
    )
    group = parser.add_argument_group("additional options")
    group.add_argument(
        "-c",
        "--crontab",
        required=False,
        action="store",
        metavar="cron",
        nargs="?",
        help="[optional] used to schedule the update of packages via crontab.",
    )
    group.add_argument(
        "-i",
        "--interactive",
        required=False,
        action="store_true",
        help="[optional] used to update pip packages interactively, allowing to update or not update"
             "packages one by one.",
    )
    group.add_argument(
        "-e",
        "--exceptions",
        action="store_true",
        required=False,
        help="[optional] used to exclude the update of some packages or to freeze a package into a"
             "specific version, without updating it.",
    )
    group.add_argument(
        "-a",
        "--add-pkgs",
        required=False,
        action="store",
        metavar="file",
        nargs="*",
        help="[optional] used to add packages to exceptions.txt via command line.",
    )
    args = parser.parse_args()
    config = vars(args)
    return config


def list_outdated_packages():
    outdated_list = subprocess.run(
        "pip list --outdated",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if len(outdated_list.stdout) == 0:
        print("There aren't outdated packages.")
    else:
        print(outdated_list.stdout)
    exit(0)


def get_pip_packages(config, local_path):
    log_date = datetime.now()
    outdated_object = subprocess.run(
        "pip list --outdated --format=json", shell=True, capture_output=True, text=True
    )
    outdated_data = json.loads(outdated_object.stdout)
    if outdated_object.returncode == 0:
        if len(outdated_data) == 0:
            print("There aren't any outdated packages.")
            logging.info(f"\n{log_date} -- There aren't any outdated packages.")
        else:
            update_packages(config, outdated_data, log_date, local_path)
    else:
        logging.info(f"\n{log_date} -- Error when running the command.")
        logging.info(outdated_object.stderr)
        exit(0)


def update_packages(config, outdated_data, log_date, local_path):
    interactive = config["interactive"]
    exceptions = config["exceptions"]
    add_packages = config["add_pkgs"]
    exceptions_file = f"{local_path}/exceptions.txt"
    exceptions_data = []
    if add_packages:
        add_exceptions(add_packages, exceptions_file, log_date)
    if exceptions:
        exceptions_data = get_exceptions_packages(exceptions, exceptions_file, log_date)
    try:
        logging.info(f"\n{log_date} -- Updating packages.")
        for element in outdated_data:
            pkg_name = element.get("name")
            pkg_version = element.get("version")
            latest_version = element.get("latest_version")
            if pkg_name in exceptions_data:
                if exceptions_data[pkg_name] is None:
                    msg = f"{pkg_name} not updated - exception noted at exceptions.txt."
                    print(msg)
                    logging.info(msg)
                    continue
                else:
                    msg = f"{pkg_name} frozen at {exceptions_data[pkg_name]} - exception noted at exceptions.txt."
                    print(msg)
                    logging.info(msg)
                    update_single_package(
                        pkg_name, pkg_version, exceptions_data[pkg_name], exceptions
                    )
                    continue
            else:
                if interactive:
                    while True:
                        question = f"Update {pkg_name} from {pkg_version} to {latest_version}? (y/n): "
                        confirmation = input(question).strip().lower()
                        if confirmation == 'y' or confirmation == 'n':
                            break
                        else:
                            print('Invalid input. Please, enter "y" or "n".')
                    if confirmation != 'y':
                        msg = f"{pkg_name} not updated - cancelled by user."
                        print(msg)
                        logging.info(msg)
                        continue
                    else:
                        msg = f"Updating {pkg_name} from {pkg_version} to {latest_version}."
                        print(msg)
                        update_single_package(pkg_name, pkg_version, latest_version, False)
                        continue
                else:
                    update_single_package(pkg_name, pkg_version, latest_version, False)
                    msg = f"{pkg_name} updated to {latest_version}"
                    print(msg)
                    continue

    except json.JSONDecodeError as e:
        logging.info(f"{log_date} -- Error when decoding JSON stdout.")
        logging.info(str(e))
        exit(0)


def add_exceptions(add_packages, exceptions_file, log_date):
    file = open(exceptions_file, "r")
    exceptions_pkgs = file.read().split("\n")
    regex = "(^[A-Za-z][A-Za-z0-9_-]*$)|(^[A-Za-z][A-Za-z0-9_-]*==[0-9].[0-9]([.][a-z0-9]*)*$)"
    for element in add_packages:
        if re.match(regex, element):
            results = [element in pkg for pkg in exceptions_pkgs]
            if any(results):
                msg = f"Package '{element}' already in exceptions.txt."
                print(msg)
                logging.info(f"{log_date} -- {msg}")
                continue
            else:
                msg = f"Package '{element}' added to exceptions.txt."
                print(msg)
                logging.info(f"{log_date} -- {msg}")
                file = open(exceptions_file, "a")
                file.write('\n' + element)
                continue
        else:
            msg = f"Package '{element}' doesn't match the required format"
            print(msg)
            logging.info(f"{log_date} -- {msg}")
            continue


def get_exceptions_packages(exceptions, exceptions_file, log_date):
    regex = "(^[A-Za-z][A-Za-z0-9_-]*$)|(^[A-Za-z][A-Za-z0-9_-]*==[0-9].[0-9]([.][a-z0-9]*)*$)"
    exceptions_data = []
    if exceptions:
        try:
            with open(exceptions_file, "r") as file:
                for line in file:
                    if re.match(regex, line):
                        line = line.strip()
                        elements = line.split("==")
                        if len(elements) == 2:
                            pkg_name, version = elements
                        else:
                            pkg_name, version = elements[0], None
                        exceptions_data.append(({"name": pkg_name, "version": version}))
                    else:
                        msg = f"Package '{line}' doesn't match the required format."
                        print(msg)
                        logging.info(f"{log_date} -- {msg}")
                        continue
        except FileNotFoundError:
            msg = f"File exceptions.txt not found."
            print(msg)
            logging.info(f"{log_date} -- {msg}")
            exit(0)
        except Exception as e:
            msg = "There was an error trying to read exceptions.txt."
            print(f"{msg}: {str(e)}")
            logging.info(f'{log_date} -- {msg}')
            logging.info(str(e))
            exit(0)
    return exceptions_data


def update_single_package(pkg_name, pkg_version, latest_version, exceptions):
    if pkg_name == "pip":
        result = subprocess.run(
            "python3 -m pip install --upgrade pip",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        result = subprocess.run(
            f"pip install {pkg_name}=={latest_version}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    if result.returncode == 0:
        if exceptions:
            msg = f"Correctly installed: {pkg_name} frozen at {latest_version}."
        else:
            msg = f"Correctly installed: {pkg_name} from {pkg_version} to {latest_version}."
        print(msg)
        logging.info(msg)
    else:
        if exceptions:
            msg = f"Error when freezing {pkg_name} to {latest_version}."
        else:
            msg = f"Error when upgrading {pkg_name} from {pkg_version} to {latest_version}."
        print(msg)
        print(result.stderr)
        logging.info(msg)
        logging.info(result.stderr)


def crontab_job(config, local_path):
    log_date = datetime.now()
    crontab = config["crontab"]
    exceptions = config["exceptions"]
    regex = ('^(?:(?:\*(?:\/(?:[1-5][0-9]|[0-9])(?:,(?:[1-5][0-9]|[0-9]))*)?)|^(?:[1-5][0-9]|[0-9])(?:,(?:[1-5][0-9]|['
             '0-9]))|^(?:[1-5][0-9]|[0-9])(?:-(?:[1-5][0-9]|[0-9]))(?:\/(?:[1-5][0-9]|[0-9])(?:,(?:[1-5][0-9]|['
             '0-9]))*)?|^(?:[1-5][0-9]|[0-9])) (?:(?:\*(?:\/(?:[2][0-3]|[1][0-9]|[0-9])(?:,(?:[2][0-3]|[1][0-9]|['
             '0-9]))*)?)|(?:[2][0-3]|[1][0-9]|[0-9])(?:,(?:[2][0-3]|[1][0-9]|[0-9]))|(?:[2][0-3]|[1][0-9]|[0-9])(?:-('
             '?:[2][0-3]|[1][0-9]|[0-9]))(?:\/(?:[2][0-3]|[1][0-9]|[0-9])(?:,(?:[2][0-3]|[1][0-9]|[0-9]))*)?|(?:[2]['
             '0-3]|[1][0-9]|[0-9])) (?:(?:\*(?:\/(?:[3][0-1]|[1-2][0-9]|[1-9])(?:,(?:[3][0-1]|[1-2][1-9]|['
             '0-9]))*)?)|(?:[3][0-1]|[1-2][0-9]|[1-9])(?:,(?:[3][0-1]|[1-2][0-9]|[1-9]))|(?:[3][0-1]|[1-2][0-9]|['
             '1-9])(?:-(?:[3][0-1]|[1-2][0-9]|[1-9]))(?:\/(?:[3][0-1]|[1-2][0-9]|[1-9])(?:,(?:[3][0-1]|[1-2][0-9]|['
             '1-9]))*)?|(?:[3][0-1]|[1-2][0-9]|[1-9])) (?:(?:\*(?:\/(?:[1][0-2]|[1-9])(?:,(?:[1][0-2]|[1-9]))*)?)|('
             '?:[1][0-2]|[1-9])(?:,(?:[1][0-2]|[1-9]))|(?:[1][0-2]|[1-9])(?:-(?:[1][0-2]|[1-9]))(?:\/(?:[1][0-2]|['
             '1-9])(?:,(?:[1][0-2]|[1-9]))*)?|(?:[1][0-2]|[1-9])) (?:(?:\*(?:\/(?:[0-6])(?:,(?:[0-6]))*)?)|(?:[0-6])('
             '?:,(?:[0-6]))|(?:[0-6])(?:-(?:[0-6]))(?:\/(?:[0-6])(?:,(?:[0-6]))*)?|(?:[0-6]))$')
    if re.match(regex, crontab):
        cronjob = CronTab(user=True)
        comment = "pip-updater"
        comment_found = any(job.comment == comment for job in cronjob)
        if not comment_found:
            command = f"python3 {local_path}/pip-updater.py"
            if exceptions:
                command += ' -e'
            job = cronjob.new(command=command, comment="pip-updater")
            job.setall(crontab)
            job.enable()
        cronjob.write()
        exit(0)
    else:
        msg = "Crontab format is not correct."
        print(msg)
        logging.info(f'{log_date} -- {msg}')
        exit(0)


def main():
    local_path = os.path.dirname(__file__)
    prog_name_short, prog_name_long, version = get_config(local_path)
    config = argument_parser(prog_name_short, prog_name_long, version)

    log_file = f"{local_path}/{prog_name_short}.log"

    log_format = '%(message)s'
    logging.basicConfig(
        filename=log_file, encoding='utf-8', format=log_format, level=logging.INFO
    )

    if config["crontab"]:
        crontab_job(config, local_path)
    elif config["list"]:
        list_outdated_packages()
    else:
        get_pip_packages(config, local_path)


if __name__ == "__main__":
    main()
