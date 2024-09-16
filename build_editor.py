#!/usr/bin/env python3

import tools.bootstrap
import sys

tools.bootstrap.execute("build_editor", sys.argv[1:])
