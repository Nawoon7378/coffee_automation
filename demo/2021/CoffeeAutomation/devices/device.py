import worker, logging, abc

class BaseDevice:
    def __init__(self) -> None:
        self._name = self.get_device_name()
        self._on_complete_callback = None
    
    @classmethod
    def is_singleton(cls) -> bool:
        return False
    
    def get_device_name(self) -> str:
        raise NotImplementedError()
    
    def set_on_complete_callback(self, callback):
        self._on_complete_callback = callback
    
    @abc.abstractmethod
    def on_create(self, worker: worker.Worker, logger: logging.Logger) -> None:
        raise NotImplementedError()
    
    @abc.abstractmethod
    def on_dispose(self, worker: worker.Worker, logger: logging.Logger) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def execute(self, worker: worker.Worker, logger: logging.Logger):
        raise NotImplementedError()
    
    @abc.abstractmethod
    def execute_async(self, worker: worker.Worker, logger: logging.Logger) -> None:
        raise NotImplementedError()


class BaseDeviceSingleton(BaseDevice):
    @classmethod
    def is_singleton(cls) -> bool:
        return True

    @classmethod
    def __get_instance(cls):
        return cls.__instance

    @classmethod
    def get_instance(cls):
        cls.__instance = BaseDeviceSingleton()
        cls.get_instance = cls.__get_instance
        return cls.__instance
