from config.config import LOG_FILE_PATH, LOG_PATH, DEBUG_MODE
from tools.messenger import Messenger
import os
from datetime import datetime as dt
import traceback
from tools.timers import Timer
import subprocess

def log_print(func):
    """
    Decorator to log the starting and ending of the function before and after the function call.
    Also logs the elapsed time of the function call.
    """
    def wrapper(*args, **kwargs):
        # worst code ever (too lazy)
        if args:
            # Check if the first argument is an instance of the class that owns the method
            func_class_name = func.__qualname__.split('.')[0]
            has_self = args[0].__class__.__name__ == func_class_name
            if has_self and hasattr(args[0], 'log'):
                log = args[0].log
            elif has_self:
                log = Logger(args[0].__class__.__name__)
            else:
                log = Logger(func.__name__)
        else:
            log = Logger(func.__name__)

        log.info(f'Starting {func.__name__}')
        timer = Timer(start=True)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # this finally block ensures logging happens even if an exception is raised.
            # exceptions are not suppressed and will propagate to the caller.
            elapsed_time = timer.elapsed()
            log.info(f'Finished {func.__name__}, took {elapsed_time:.2f} seconds')
    return wrapper

def _truncate_log_file(self):
    try:
        line_count = int(subprocess.check_output(['wc', '-l', LOG_FILE_PATH]).decode().strip().split()[0])
    except Exception:
        line_count = None
    if line_count is not None and line_count >= 10000:
        # If the log file has more than 10,000 lines, delete the oldest 1,000 lines
        trunc_count = 1000 if line_count < 20000 else line_count - 9000
        with open(LOG_FILE_PATH, 'r') as f:
            lines = f.readlines()
        with open(LOG_FILE_PATH, 'w') as f:
            f.writelines(lines[-trunc_count:])
        with open(LOG_FILE_PATH, 'a') as f:
            f.write(self.msgr.format_message(status = 2, time=None, message='Log file truncated to last 1000 lines.', log=True))

def _write_to_log(func):
    '''
    Decorator to write to log
    '''
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.write_counter >= 1000:
            _truncate_log_file(self)
            self.write_counter = 1

        output = func(*args, **kwargs)
        try: 
            with open(LOG_FILE_PATH, 'a') as f:
                f.write(f'{output}\n')
                self.write_counter += 1
            if DEBUG_MODE:
                print(output)
        except FileNotFoundError:
            os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
            with open(LOG_FILE_PATH, 'w') as f:
                f.write(f'{output}\n')
                self.write_counter += 1
        except Exception as e:
            # Debug: print any other exceptions that might be occurring
            print(f"[LOGGER ERROR] Failed to write to log: {e}")
            if DEBUG_MODE:
                print(f"[LOGGER DEBUG] Output was: {output}")
        return output
    return wrapper

class Logger:
    def __init__(self, name, path=None):

        self.msgr = Messenger(name=name)
        self.file_path = LOG_FILE_PATH if not path else path
        self.path = LOG_PATH
        self.write_counter = 0

    @_write_to_log
    def debug(self, msg, time=None):
        return self.msgr.format_message(status = 1, time=time, message=msg, log=True)

    @_write_to_log
    def debug_plain(self, msg):
        """
        Log message without any formatting. Only for debugging. 
        """
        return f'[DEBUG]{msg}'

    @_write_to_log
    def info(self, msg, time=None):
        return self.msgr.format_message(status = 0, time=time, message=msg, log=True)

    @_write_to_log
    def critical(self, msg, time=None):
        return self.msgr.format_message(status = 4, time=time, message=msg, log=True)

    @_write_to_log
    def warning(self, msg, time=None):
        return self.msgr.format_message(status = 2, time=time, message=msg, log=True)
    
    @_write_to_log
    def error(self, msg, time=None):
        return self.msgr.format_message(status = 3, time=time, message=msg, log=True)

    def traceback(self, tb: traceback):
        """
        Saves the traceback of the exception to an own file inside the log folder.
        """
        if DEBUG_MODE:
            print(tb)
        file_header = f'/traceback_{dt.now().strftime("%d%m%Y-%H%M%S")}.log'
        with open(str(self.path) + file_header, 'a') as f:
            f.write(tb)

    def view_log(self, lines_index):
        cursor = 0
        content =  ''
        with open(self.file_path, 'r') as f:
            lines = f.readlines() # FIXME: debug
            cursor = lines.__len__() - lines_index
        with open(self.file_path, 'r') as f:
            for count, line in enumerate(f):
                if count > cursor:
                    content += line
            return content
