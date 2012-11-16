# -*- coding: utf-8 -*-

"""Kwapi logging."""

import logging

def setup(file_name, file_level, console_level):
    """Setup logging with the given parameters."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    # Create file handler
    file_handler = logging.FileHandler(file_name, mode='w')
    file_handler.setLevel(file_level)
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
