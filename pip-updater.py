#!/usr/bin/env python3

# pip-updater v0.2.0
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


def get_config(local_path):
    config = open(f'{local_path}/pip-updater.json', 'r')
    data = json.loads(config.read())
    prog_name_short = data['prog_name_short']
    prog_name_long = data['prog_name_long']
    version = data['version']
    return prog_name_short, prog_name_long, version


def argument_parser(program_name_short, program_name_long, ver):
    description = f'{program_name_long} is a python script which updates all outdated pip packages.'
    epilog = (f"""By default, {program_name_long} updates all outdated pip packages without asking confirmation.
If you want to exclude some packages from updating or want to freeze a package into a specific version without updating
it, you must populate the file named "exceptions.txt", adding the name of the desired package, one package per line.
In order to freeze a pip package into a specific version, use "pkg_name==version" format.""")
    parser = argparse.ArgumentParser(prog=f"{program_name_short}",
                                     description=textwrap.dedent(f"{description}"),
                                     epilog=f"{epilog}",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     usage='python3 %(prog)s.py [-h] [-v] [-l] [-i] [-e]')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {ver}',
                        help='show %(prog)s version information and exit')
    parser.add_argument('-l', '--list', action='store_true', help='show list of outdated packages.')
    group = parser.add_argument_group('additional options')
    group.add_argument('-i', '--interactive', required=False, action='store_true',
                       help='[optional] used to update pip packages interactively, allowing to update or not update'
                            'packages one by one.')
    group.add_argument('-e', '--exceptions', action='store_true', required=False,
                       help='[optional] used to exclude the update of some packages or to freeze a package into a'
                            'specific version, without updating it.')
    args = parser.parse_args()
    config = vars(args)
    list_packages = config['list']
    interactive = config['interactive']
    exceptions = config['exceptions']
    return list_packages, interactive, exceptions


def list_outdated_packages():
    outdated_list = subprocess.run('pip list --outdated', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
    if len(outdated_list.stdout) == 0:
        print('There aren\'t outdated packages.')
    else:
        print(outdated_list.stdout)
    exit(0)


def get_packages():
    log_date = datetime.now()
    outdated_object = subprocess.run('pip list --outdated --format=json', shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True)
    return log_date, outdated_object


def get_pip_packages(interactive, exceptions, local_path):
    log_date, outdated_object = get_packages()
    outdated_data = json.loads(outdated_object.stdout)
    if outdated_object.returncode == 0:
        if len(outdated_data) == 0:
            print('There aren\'t outdated packages.')
            logging.info(f'\n{log_date} -- There aren\'t outdated packages.')
        else:
            update_packages(outdated_data, interactive, exceptions, log_date, local_path)
    else:
        logging.info(f'\n{log_date} -- Error when running the command.')
        logging.info(outdated_object.stderr)
        exit(0)


def update_packages(outdated_data, interactive, exceptions, log_date, local_path):
    exceptions_file = f'{local_path}/exceptions.txt'
    exceptions_data = []
    if exceptions:
        exceptions_data = get_exceptions_packages(exceptions, exceptions_file, log_date)
    try:
        logging.info(f'\n{log_date} -- Updating packages')
        for index, element in enumerate(outdated_data):
            exceptions_names = []
            exceptions_versions = []
            pkg_name = element.get("name")
            pkg_version = element.get("version")
            latest_version = element.get("latest_version")
            if exceptions:
                for data in exceptions_data:
                    exceptions_names.append(data.get("name"))
                    exceptions_versions.append(data.get("version"))
            if pkg_name in exceptions_names:
                element_index = exceptions_names.index(element.get("name"))
                if exceptions_versions[element_index] is None:
                    msg = f'{pkg_name} not updated - exception noted at exceptions.txt'
                    print(msg)
                    logging.info(msg)
                    continue
                else:
                    msg = (f'{pkg_name} freezed at {exceptions_versions[element_index]} - exception noted at '
                           f'exceptions.txt')
                    print(msg)
                    logging.info(msg)
                    update_single_package(pkg_name, pkg_version, exceptions_versions[element_index], exceptions)
                    continue
            else:
                if interactive:
                    while True:
                        question = f'Update {pkg_name} from {pkg_version} to {latest_version}? (y/n): '
                        confirmation = input(question).strip().lower()
                        if confirmation == 'y' or confirmation == 'n':
                            break
                        else:
                            print(f'Invalid input. Please, enter "y" or "n"')
                    if confirmation != 'y':
                        msg = f'{pkg_name} not updated - cancelled by user'
                        print(msg)
                        logging.info(msg)
                        continue
                    else:
                        msg = f'Updating {pkg_name} from {pkg_version} to {latest_version}'
                        print(msg)
                        update_single_package(pkg_name, pkg_version, latest_version, False)
                        continue
                else:
                    update_single_package(pkg_name, pkg_version, latest_version, False)
                    msg = f'{pkg_name} updated to {latest_version}'
                    print(msg)
                    continue

    except json.JSONDecodeError as e:
        logging.info(f'{log_date} -- Error when decoding JSON stdout.')
        logging.info(str(e))
        exit(0)


def get_exceptions_packages(exceptions, exceptions_file, log_date):
    exceptions_data = []
    if exceptions:
        try:
            with open(exceptions_file, "r") as file:
                for line in file:
                    line = line.strip()
                    elements = line.split("==")
                    if len(elements) == 2:
                        pkg_name, version = elements
                    else:
                        pkg_name, version = elements[0], None
                    exceptions_data.append(({"name": pkg_name, "version": version}))

        except FileNotFoundError:
            msg = f'File exceptions.txt not found.'
            print(msg)
            logging.info(f"{log_date} -- {msg}")
            exit(0)
        except Exception as e:
            msg = 'There was an error trying to read exceptions.txt'
            print(f'{msg}: {str(e)}')
            logging.info(f'{log_date} -- {msg}')
            logging.info(str(e))
            exit(0)
    return exceptions_data


def update_single_package(pkg_name, pkg_version, latest_version, exceptions):
    if pkg_name == 'pip':
        result = subprocess.run('python3 -m pip install --upgrade pip', shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
    else:
        result = subprocess.run(f'pip install {pkg_name}=={latest_version}', shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        if exceptions:
            msg = f'Correctly installed: {pkg_name} freezed at {latest_version}'
        else:
            msg = f'Correctly installed: {pkg_name} from {pkg_version} to {latest_version}'
        print(msg)
        logging.info(msg)
    else:
        if exceptions:
            msg = f'Error when freezing {pkg_name} to {latest_version}'
        else:
            msg = f'Error when upgrading {pkg_name} from {pkg_version} to {latest_version}'
        print(msg)
        print(result.stderr)
        logging.info(msg)
        logging.info(result.stderr)


def main():
    local_path = os.path.dirname(__file__)
    prog_name_short, prog_name_long, version = get_config(local_path)
    list_packages, interactive, exceptions = argument_parser(prog_name_short, prog_name_long, version)

    log_file = f'{local_path}/{prog_name_short}.log'

    log_format = '%(message)s'
    logging.basicConfig(filename=log_file, encoding='utf-8', format=log_format, level=logging.INFO)

    if list_packages:
        list_outdated_packages()
    else:
        get_pip_packages(interactive, exceptions, local_path)


if __name__ == '__main__':
    main()
