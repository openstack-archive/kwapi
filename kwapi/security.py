# -*- coding: utf-8 -*-

"""Computes the signature of a metering message."""

import hashlib
import hmac

def recursive_keypairs(d):
    """Generator that produces sequence of keypairs for nested dictionaries."""
    for name, value in sorted(d.iteritems()):
        if isinstance(value, dict):
            for subname, subvalue in recursive_keypairs(value):
                yield ('%s:%s' % (name, subname), subvalue)
        else:
            yield name, value

def compute_signature(message, secret):
    """Returns the signature for a message dictionary."""
    digest_maker = hmac.new(secret, '', hashlib.sha256)
    for name, value in recursive_keypairs(message):
        if name == 'message_signature':
            continue
        digest_maker.update(name)
        digest_maker.update(unicode(value).encode('utf-8'))
    return digest_maker.hexdigest()

def append_signature(message, secret):
    """Sets the message signature key."""
    message['message_signature'] = compute_signature(message, secret)

def verify_signature(message, secret):
    """Checks the signature in the message against the value computed from the rest of the contents."""
    old_sig = message.get('message_signature')
    new_sig = compute_signature(message, secret)
    return new_sig == old_sig
