import logging, threading, time, sys, os
from logging.handlers import RotatingFileHandler
from datetime import datetime as dt

class Worker:
    def __create_log_path(self, filename):
        return os.path.join(os.path.dirname(__file__), filename)
    
    def __init__(self,
                thread_interval=0.001,
                log_filename="worker.log",
                log_size=(1 * 1024 * 1024), # 1MB
                log_level=logging.DEBUG,
                log_backup_count=10):
        self._is_running = False
        self._stop_requested = False
        self._interval = thread_interval
        self._log_path = self.__create_log_path(log_filename)
        self._log_max_size = log_size
        self._log_backup_count = log_backup_count
        self._logging_level = log_level
        self._main_thread = threading.Thread(target=self._run)
        self._co_routine_thread = threading.Thread(target=self._co_routine)
        self._co_routine_callbacks = []
        self._callback_pre_run = None
        self._callback_main_loop = None
        self._callback_post_run = None
    
    def _BeforeRunCheck_(func):
        def decorated(self, *args, **kwargs):
            if self._is_running:
                raise RuntimeError("This method must be called before start command thread!")
            func(self, *args, **kwargs)
        return decorated
    
    def add_co_routine(self, callback):
        if callback not in self._co_routine_callbacks:
            self._co_routine_callbacks.append(callback)
    
    def remove_co_routine(self, callback):
        idx = -1
        for i, cb in self._co_routine_callbacks:
            if cb is callback:
                idx = i
                break
        if idx != -1:
            del self._co_routine_callbacks[idx]

    @_BeforeRunCheck_
    def set_prerun_callback(self, callback):
        # params: worker, logger
        self._callback_pre_run = callback
        
    def get_prerun_callback(self):
        return self._callback_pre_run

    @_BeforeRunCheck_
    def set_main_loop_callback(self, callback):
        # params: worker, delta_time, logger
        self._callback_main_loop = callback
        
    def get_main_loop_callback(self):
        return self._callback_main_loop
    
    @_BeforeRunCheck_
    def set_postrun_callback(self, callback):
        # params: worker, logger
        self._callback_post_run = callback
        
    def get_postrun_callback(self):
        return self._callback_post_run
    
    def set_callbacks(self, prerun, main_loop, postrun):
        if prerun is not None:
            self.set_prerun_callback(prerun)
        if main_loop is not None:
            self.set_main_loop_callback(main_loop)
        if postrun is not None:
            self.set_postrun_callback(postrun)
    
    @_BeforeRunCheck_
    def set_max_log_size(self, size: int):
        self._log_max_size = size
    
    def get_max_log_size(self) -> int:
        return self._log_max_size

    @_BeforeRunCheck_
    def set_log_path(self, path: str):
        self._log_path = path
    
    def get_log_path(self) -> str:
        return self._log_path

    @_BeforeRunCheck_
    def set_logging_level(self, level: int):
        self._logging_level = level
    
    @_BeforeRunCheck_
    def set_log_backup_file_count(self, cnt: int):
        self._log_backup_count = cnt
    
    def get_log_backup_file_count(self) -> int:
        return self._log_backup_count
    
    def set_thread_interval(self, interval: float):
        if interval > 1:
            raise RuntimeError(f"Not supporting interval larger than 1. Requested: {interval}, Current: {self._interval}.")
        self._interval = interval
    
    def get_thread_interval(self) -> float:
        return self._interval
    
    def create_logger(self, name="Worker"):
        logger = logging.getLogger(name)
        file_handler = RotatingFileHandler(self._log_path, self._log_max_size, self._log_backup_count)
        formatter = logging.Formatter('[%(levelname)s | %(filename)s:%(lineno)s]\t%(asctime)s\t> %(message)s')
        stream_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.setLevel(self._logging_level)
        return logger, file_handler, stream_handler
    
    def dispose_logger(self, logger: logging.Logger, file_handler: RotatingFileHandler, stream_handler: logging.StreamHandler):
        logger.removeHandler(file_handler)
        logger.removeHandler(stream_handler)
        del logger, file_handler, stream_handler
    
    def _co_routine(self, is_root=True, logger=None):
        is_own_logger = False
        if logger is None:
            logger, file_handler, stream_handler = self.create_logger(name="Co-Routine")
            is_own_logger = True

        if not is_root:
            try:
                for cb in self._co_routine_callbacks:
                    cb(self, logger)
            except:
                logger.exception("Got exception on worker co-routine process.")
        else:
            while not self._stop_requested:
                threading.Thread(target=self._co_routine, args=(False, logger)).start()
                time.sleep(0.02)
        
            if is_own_logger:
                self.dispose_logger(logger, file_handler, stream_handler)
    
    def _run(self):
        self._is_running = True
        logger, file_handler, stream_handler = self.create_logger()

        def __dispose(self, logger, file_handler, stream_handler):
            self.dispose_logger(logger, file_handler, stream_handler)
            self._is_running = False

        try:
            if self._callback_pre_run is not None:
                if self._callback_pre_run(self, logger) is False:
                    self._stop_requested = True
                    __dispose(self, logger, file_handler, stream_handler)
                    return
        except Exception as err:
            logger.exception("Got exception on worker pre-process.")
            self._stop_requested = True

        prev_time = dt.now()
        while not self._stop_requested:
            try:
                cur_time = dt.now()
                if self._callback_main_loop is not None:
                    result = self._callback_main_loop(self, (cur_time - prev_time), logger)
                    if result is False:
                        self._stop_requested = True
                prev_time = cur_time
                time.sleep(self._interval)
            except:
                logger.exception("Got exception on worker main process.")
                self._stop_requested = True
                
        try:
            if self._callback_post_run is not None:
                self._callback_post_run(self, logger)
        except Exception as err:
            logger.exception("Got exception on worker post-process.")

        __dispose(self, logger, file_handler, stream_handler)
    
    def start(self):
        self._stop_requested = False
        self._main_thread.start()
        self._co_routine_thread.start()
    
    def stop(self, timeout=None):
        self._stop_requested = True
        self._main_thread.join(timeout)
        self._co_routine_thread.join(timeout)
    
    def is_running(self) -> bool:
        return self._is_running
    
    def is_stopping(self) -> bool:
        return self._stop_requested
