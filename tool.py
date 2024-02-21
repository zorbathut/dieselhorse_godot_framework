#!/usr/bin/env python3

import tools.bootstrap
import sys

tools.bootstrap.execute(sys.argv[1], sys.argv[2:], shell=True)
