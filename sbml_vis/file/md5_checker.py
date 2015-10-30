import hashlib

__author__ = 'anna'


def check_md5(file_name):
    with open(file_name) as file_to_check:
        # read contents of the file
        data = file_to_check.read()
        # pipe contents of the file through
        return hashlib.md5(data).hexdigest()