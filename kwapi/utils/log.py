# -*- coding: utf-8 -*-

"""Kwapi logging."""

import logging as log

def setup(file_name):
    """Setup logging with the given parameters."""
    # Create logger
    logger = log.getLogger()
    logger.setLevel(log.INFO)
    # Create file handler
    file_handler = log.FileHandler(file_name, mode='w')
    file_handler.setLevel(log.INFO)
    # Create console handler
    console_handler = log.StreamHandler()
    console_handler.setLevel(log.INFO)
    # Create formatter and add it to the handlers
    formatter = log.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
