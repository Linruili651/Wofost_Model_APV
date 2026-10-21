# BEGIN TARGET INPUT PROCESS LOGGING
# PCSE user settings extension: logging only; no scientific parameters changed.
import os as _process_log_os
from copy import deepcopy as _process_log_copy
from pcse.settings.default_settings import LOG_CONFIG as _process_log_defaults
LOG_CONFIG = _process_log_copy(_process_log_defaults)
_process_log_original = LOG_CONFIG['handlers']['file']['filename']
_process_log_folder = _process_log_os.path.dirname(_process_log_original)
LOG_CONFIG['handlers']['file']['filename'] = _process_log_os.path.join(
    _process_log_folder, 'pcse-process-' + str(_process_log_os.getpid()) + '.log')
# END TARGET INPUT PROCESS LOGGING
