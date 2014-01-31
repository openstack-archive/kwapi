# -*- coding: utf-8 -*-

"""Kwapi logging."""

import logging

getLogger = logging.getLogger


def setup(file_name):
    """Setup logging with the given parameters."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # Create file handler
    file_handler = logging.FileHandler(file_name, mode='w')
    file_handler.setLevel(logging.INFO)
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
