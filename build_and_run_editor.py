#!/usr/bin/env python3

import tools.bootstrap
import sys

tools.bootstrap.execute("build_and_run_editor", sys.argv[1:])
