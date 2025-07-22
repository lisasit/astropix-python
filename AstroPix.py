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
import numpy as np
import time
import os
import binascii
import pandas as pd
import json

class AstroPix(Satellite):
    """Satellite for controlling an AstroPix chip"""

    def do_initializing(self, config: Configuration):
        self.outfile_suffix = config.setdefault("outfile_suffix", "")
        self.outdir = config.setdefault("outdir", "../AstroPix")
        # Ensures output directory exists
        if os.path.exists(self.outdir) == False:
            os.mkdir(self.outdir)
        self.chip_config = config["chip_config"]
        self.chip_version = config["chip_version"]
        self.inject_row = config.setdefault("inject_row", None)
        self.inject_col = config.setdefault("inject_col", None)
        self.inject = (self.inject_row, self.inject_col) if self.inject_row is not None and self.inject_col is not None else None
        self.injection_voltage = config.setdefault("injection_voltage", None)
        self.analog = config.setdefault("analog", 0)
        self.threshold = config.setdefault("threshold", None)
        self.injection_onchip = config.setdefault("injection_onchip", True)
        self.newfilter = config.setdefault("newfilter", False)
        self.warmup = config.setdefault("warmup", True)
        if hasattr(self, 'astro'):
            self.astro.close_connection()
        self.astro = astropixRun(chipversion=self.chip_version, inject=self.inject)
        self.log.debug(f'Configuration:\n {json.dumps(config.get_dict(), indent=1)}')

    def do_launching(self) -> str:
        self.astro.asic_init(yaml=self.chip_config, analog_col = self.analog)
        self.astro.init_voltages(vthreshold=self.threshold)
        #If injection, ensure injection pixel is enabled and initialize
        if self.inject is not None:
            self.log.debug(f'Enabling pixel {self.inject}')
            self.astro.enable_pixel(self.inject[1], self.inject[0])
            self.astro.init_injection(inj_voltage=self.injection_voltage, onchip=self.injection_onchip)
        self.astro.enable_spi()
        self.astro.asic_configure()
        if self.chip_version == 4:
            self.astro.update_asic_tdac_row(0)
        self.finalize_config()
        self.astro.dump_fpga()
        return f"AstroPix is configured"

    def do_reconfigure(self, partial_config: Configuration) -> str:
        call_asic_init = False
        if "outfile_suffix" in partial_config:
            self.outfile_suffix = partial_config["outfile_suffix"]
            self.log.info(f"New suffix for the output files: {self.outfile_suffix}")

        if "outdir" in partial_config:
            self.outdir = partial_config["outdir"]
            if os.path.exists(self.outdir) == False:
                os.mkdir(self.outdir)
            self.log.info(f"New directory for the output files: {self.outdir}")

        if "chip_config" in partial_config:
            self.chip_config = partial_config["chip_config"]
            call_asic_init = True
            self.log.info(f"New config for the chip: {self.chip_config}")

        if "analog" in partial_config:
            self.analog = partial_config["analog"]
            call_asic_init = True
            self.log.info(f"New analog output column: {self.analog}")

        if "chip_version" in partial_config:
            raise ValueError("Reconfiguring chip version is not possible")

        if "inject_row" in partial_config or inject_col in partial_config:
            if "inject_row" in partial_config:
                self.inject_row = partial_config["inject_row"]
            if "inject_col" in partial_config:
                self.inject_col = partial_config["inject_col"]
            new_inject = (self.inject_row, self.inject_col) if self.inject_row is not None and self.inject_col is not None else None
            if new_inject == self.inject:
                self.log.warning(f"Injection pixel not changed from {self.inject}, check if the config is correct")
            else:
                self.log.info(f"Injection pixel changed from {self.inject} to {new_inject}")
                self.inject = new_inject
                self.astro.injection_row = self.inject_row
                self.astro.injection_col = self.inject_col
                call_asic_init = True

        if "injection_voltage" in partial_config:
            self.injection_voltage = partial_config["injection_voltage"]
            call_asic_init = True
            self.log.info(f"New injection_voltage: {self.injection_voltage} {self.injection_voltage < 5 : 'V' else 'mV'}")

        if "threshold" in partial_config:
            self.threshold = partial_config["threshold"]
            self.astro.init_voltages(vthreshold=self.threshold)
            self.log.info(f"New threshold: {self.threshold} {self.threshold < 5 : 'V' else 'mV'}")

        if "injection_onchip" in partial_config:
            raise ValueError("Reconfiguring the source of injection (on chip/through the injection board) is not possible")

        if call_asic_init:
            self.log.info("Reinitializing the chip")
            self.astro.asic_init(yaml=self.chip_config, analog_col = self.analog)
            if self.inject is not None:
                self.astro.enable_pixel(self.inject[1], self.inject[0])
                self.astro.init_injection(inj_voltage=self.injection_voltage, onchip=self.injection_onchip)
            self.astro.enable_spi()
            self.astro.asic_configure()
            if self.chip_version == 4:
                self.astro.update_asic_tdac_row(0)
        self.finalize_config()
        self.astro.dump_fpga()
        return "AstroPix is reinitialized"

    def do_landing(self) -> str:
        return "No way to control anything from here, consider AstroPix landed"

    def do_starting(self, run_identifier: str):
        if self.inject is not None:
            self.astro.start_injection()
            return f"Injections into pixel {self.inject} started"
        return f"Chip ready for taking data"

    def do_stopping(self):
        return "Nothing is done, AstroPix is unstoppable"

    def do_run(self, payload: any) -> str:
        i = 0
        while not self._state_thread_evt.is_set():
            readout = self.astro.get_readout()
            if readout: #if there is data contained in the readout stream
                # Writes the hex version to hits
                self.bitfile.write(f"{i}\t{str(binascii.hexlify(readout))}\n")
                self.bitfile.flush() #make it simulate streaming
                i += 1
        return "Finished data acquisition"

    def finalize_config(self):
        # Save final configuration to output file
        time_config=time.strftime("%Y%m%d-%H%M%S")
        ymlpathout = self.outdir +"/"+self.chip_config+"_"+time_config+".yml"
        try:
            self.astro.write_conf_to_yaml(ymlpathout)
        except FileNotFoundError:
            ypath = self.chip_config.split('/')
            ymlpathout = self.outdir + "/" + ypath[1] + "_" + time_config + ".yml"
            self.astro.write_conf_to_yaml(ymlpathout)
        self.log.info(f'Configuration saved to file {ymlpathout}')

        # Prepare text files/logs
        fname = "" if not self.outfile_suffix else self.outfile_suffix + "_"
        bitpath = self.outdir + '/' + fname + time_config + '.log'
        # textfiles are always saved so we open it up
        if hasattr(self, 'bitfile'):
            self.bitfile.close()
        self.bitfile = open(bitpath, 'w')
        # Writes all the config information to the file
        self.bitfile.write(self.astro.get_log_header())
        self.bitfile.write(self.config.get_json())
        self.bitfile.write("\n")
        self.log.info(f'Bitfile with data: {bitpath}')
