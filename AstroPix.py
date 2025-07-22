"""
SPDX-FileCopyrightText: 2024 DESY and the Constellation authors
SPDX-License-Identifier: EUPL-1.2

Provides the class for the AstroPix example satellite
"""

# import random
# import time
# from typing import Any

# from constellation.core.cmdp import MetricsType
# from constellation.core.commandmanager import cscp_requestable
from constellation.core.configuration import Configuration

# from constellation.core.cscp import CSCPMessage
# from constellation.core.fsm import SatelliteState
# from constellation.core.monitoring import schedule_metric
from constellation.core.satellite import Satellite
from astropix import astropixRun
from core.nexysio import Nexysio
import binascii


class AstroPix(Satellite):
    """Satellite for controlling an AstroPix chip"""

    def do_initializing(self, config: Configuration):
        self.outfile_suffix = config.setdefault("outfile_suffix", "")
        self.outdir = config.setdefault("outdir", "../AstroPix")
        self.chip_config = config["chip_config"]
        self.chip_version = config["chip_version"]
        self.inject = config["inject"]
        # astro = astropixRun(chipversion=self.chip_version, inject=None, offline=True) 
        # astro.asic_init(yaml=args.yaml, analog_col = args.analog)
        self.nexys = Nexysio()
        self.handle = self.nexys.autoopen()

        register = 0x09
        self.log.status(f"Reading register {register}")
        answer = self.nexys.read_register(register)
        self.log.status(f"Read {answer.hex()}")
        for value in [0x55, 0x65]:
            self.log.status(f"Writing {value} = {hex(value)} to register {register}")
            data = self.nexys.write_register(register, value, True)
            self.log.status(f"Wrote {binascii.hexlify(data)}")
            for i in range(5):
                self.log.status(f"Reading register {register}for the {i} time")
                answer = self.nexys.read_register(register)
                self.log.status(f"Read {answer.hex()}")


    def do_launching(self):
        self.log.status("Launched")
        
    def do_landing(self):
        self.handle.close()

    def do_starting(self, run_identifier: str):
        pass

    def do_stopping(self):
        pass

    def do_run(self, payload: any) -> str:
        pass
