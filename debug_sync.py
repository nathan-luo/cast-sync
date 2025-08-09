#!/usr/bin/env python3

import traceback
import sys
sys.path.insert(0, ".")

try:
    from cast.cli import app
    from typer.testing import CliRunner
    
    runner = CliRunner()
    result = runner.invoke(app, ["sync", "vault2", "vault1", "--apply"])
    
    if result.exit_code != 0:
        print("Exit code:", result.exit_code)
        print("Output:", result.output)
        if result.exception:
            print("Exception traceback:")
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
except Exception as e:
    traceback.print_exc()
