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


class AstroPix(Satellite):
    """Satellite for controlling an AstroPix chip"""

    def do_initializing(self, config: Configuration):
        pass

    def do_launching(self):
        pass

    def do_landing(self):
        pass

    def do_starting(self, run_identifier: str):
        pass

    def do_stopping(self):
        pass

    def do_run(self, payload: any) -> str:
        pass
