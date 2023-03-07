#!/usr/bin/env python
import subprocess
import platform
import re
import sys
import urllib.request, urllib.parse, urllib.error
from genericpath import isfile
from hashlib import sha256
from os import remove
from os.path import dirname, abspath, join, isdir
from subprocess import Popen
import requests

BASE_DIR = abspath(dirname(__file__))
TBB_DIR = join(BASE_DIR, 'tor-browser_en-US')
TBB_VERSION_URL = "https://gettor.torproject.org/api/latest.json"
TBB_ARCHIVE_URL = "https://archive.torproject.org/tor-package-archive/torbrowser/{0}/"
TBB_DEVS_KEY_FP = '0x4E2C6E8793298290'
CHECKSUM_FILE = "sha256sums-unsigned-build.txt"
CHECKSUM_FILE_URL = TBB_ARCHIVE_URL + CHECKSUM_FILE
CHECKSUM_FPATH = join(BASE_DIR, CHECKSUM_FILE)


class IntegrityCheckError(Exception):
    pass


class ExtractionError(Exception):
    pass


class DownloadError(Exception):
    pass


def get_latest_tor(version=None):
    """Download latest stable version and verify its signature."""
    if not version:
        version = tbb_stable_version()
    if version is None:
        raise DownloadError("Cannot find latest TBB stable version.")

    # download latest TBB
    tbb_filename = get_tbb_filename(version)
    tbb_path = join(BASE_DIR, tbb_filename)
    tbb_url = TBB_ARCHIVE_URL.format(version) + tbb_filename
    download(tbb_url, BASE_DIR)
    download(CHECKSUM_FILE_URL.format(version), BASE_DIR)

    # verify checksum
    if not is_checksum_correct(tbb_filename):
        raise IntegrityCheckError("Checksum of downloaded TBB is not correct!")

    # verify signature of downloaded TBB
    #if not is_signature_valid(tbb_path + '.asc'):
    #    raise IntegrityCheckError("Invalid signature of TBB file!")
    return tbb_path


def tbb_stable_version():
    """Return version of the latest TBB stable."""
    response = requests.get(TBB_VERSION_URL)
    return response.json()['stable']['latest_version']


def get_tbb_filename(version):
    """Assume 'en-US' locale and new filename structure."""
    arch = platform.architecture()[0][:-3]
    return 'tor-browser-linux{0}-{1}_en-US.tar.xz'.format(arch, version)


def download_with_signature(file_url, dir_path):
    download(file_url, dir_path)
    download(file_url + '.asc', dir_path)


def download(file_url, dir_path):
    """Download a file to a directory."""
    fname = file_url.split("/")[-1]  # assumes no url params and others
    fpath = join(dir_path, fname)
    try:
        urllib.request.urlretrieve(file_url, fpath)
    except URLError as url_exc:
        raise DownloadError("Error retrieving: %s to %s: %s"
                            % (file_url, fpath, url_exc))


def extract_tarfile(file_path):
    """Extract a tarfile to the same directory."""
    dir_path = dirname(file_path)
    tar_cmd = "tar -xvf %s -C %s" % (file_path, dir_path)
    status, txt = subprocess.getstatusoutput(tar_cmd)

    if status or not isdir(TBB_DIR):
        raise ExtractionError("Error extracting TBB tarball %s: (%s: %s)"
                              % (tar_cmd, status, txt))


def is_signature_valid(sig_file):
    """Verify the signature of a file."""
    if not isfile(sig_file):
        raise OSError("Signature file %s not found." % sig_file)
    ret_code = Popen(['gpg', '--verify', sig_file]).wait()
    return True if ret_code == 0 else False


def is_checksum_correct(tbb_filename):
    # get SHA256 hash
    tarball_path = join(BASE_DIR, tbb_filename)
    with open(tarball_path, 'rb') as f:
        contents = f.read()
        sha256_sum = sha256(contents).hexdigest()

    # verify checksum file signature
    #if not is_signature_valid(CHECKSUM_FPATH + '.asc'):
    #    raise IntegrityCheckError("Checksum file has not a valid signature.")

    with open(CHECKSUM_FPATH, 'r') as checksum_file:
        for line in checksum_file:
            if tbb_filename in line:
                if sha256_sum.lower() in line.split()[0].lower():
                    return True
    return False


def import_gpg_key(key_fp):
    """Import GPG key with the given fingerprint."""
    # https://www.torproject.org/docs/verifying-signatures.html.en
    cmd = ['gpg', '--keyserver',
                      'pgp.mit.edu',
                      '--recv-keys', key_fp]
    print(("Import key: %s" % ' '.join(cmd)))
    ret_code = Popen(cmd).wait()

    if ret_code != 0:
        raise DownloadError("Cannot import signing key.")


def remove_tbb_file(file_path):
    if isfile(file_path):
        remove(file_path)
    if isfile(file_path + '.asc'):
        remove(file_path + '.asc')


def tbb_setup(version=None, clean=False):
    # import TBB devs gpg key
    #try:
    #    import_gpg_key(TBB_DEVS_KEY_FP)
    #except DownloadError as dwn_err:
    #    print("[gettor] - Error on download of files: %s" % dwn_err)
    #    sys.exit(-1)

    # get the latest Tor Browser Bundle
    try:
        tarfile_path = get_latest_tor(version)
    except IntegrityCheckError as int_err:
        print(("[gettor] - Error on integrity check: %s" % int_err))
        sys.exit(-1)
    except OSError as os_exc:
        print(("[gettor] - %s" % os_exc))

    # extract tar.xz
    try:
        extract_tarfile(tarfile_path)
    except ExtractionError as ext_err:
        print(("[gettor] - Error when extracting tarball: %s" % ext_err))
        sys.exit(-1)

    # clean temp files
    if clean:
        remove_tbb_file(tarfile_path)
        remove_tbb_file(CHECKSUM_FPATH)


if __name__ == '__main__':
    version = None
    if len(sys.argv) > 1:
        version = sys.argv[1]
    tbb_setup(version=version, clean=True)
