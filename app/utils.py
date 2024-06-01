import os


def is_readable_dir(path):
    # Check if the given path is readable
    return os.path.isdir(path) and os.access(path, os.R_OK)
