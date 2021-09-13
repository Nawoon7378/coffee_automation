import device, worker, logging
import threading

class SampleDevice(device.BaseDevice):
    def __init__(self) -> None:
        super().__init__()
        self._sub_thread: threading.Thread = None

    def get_device_name(self) -> str:
        return "SampleDevice"
    
    def on_create(self, worker: worker.Worker, logger: logging.Logger) -> None:
        logger.info(f"{self.get_device_name()} - OnCreate")
    
    def on_dispose(self, worker: worker.Worker, logger: logging.Logger) -> None:
        logger.info(f"{self.get_device_name()} - OnDispose")
    
    def execute(self, worker: worker.Worker, logger: logging.Logger):
        logger.info(f"{self.get_device_name()} - Execute")
    
    def execute_async(self, worker: worker.Worker, logger: logging.Logger) -> None:
        if self._sub_thread is not None:
            self._sub_thread.join()
            self._sub_thread = None
        self._sub_thread = threading.Thread(target=self._async_thread)
        self._sub_thread.start()
    
    def _async_thread(self):
        if self._on_complete_callback is not None:
            self._on_complete_callback()
