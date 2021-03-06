# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import logging

from .config import (
    DsnConnection,
    Schema,
    Field,
    Index
)
from .query import Query
from . import decorators
from .model import Orm
from .interface import (
    get_interface,
    set_interface,
    get_interfaces,
    configure,
    configure_environ
)
from .exception import InterfaceError, Error, UniqueError
from . import utils


__version__ = '2.0.1'


# get rid of "No handler found" warnings (cribbed from requests)
logging.getLogger(__name__).addHandler(logging.NullHandler())

