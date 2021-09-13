import worker, time, Config
from indy_utils import indy_shm
from logging import Logger

from devices.sample_device import SampleDevice

class ProcessHandler:
    _worker = None

    def __init__(self) -> None:
        self._worker = worker.Worker(thread_interval=1)
        self._worker.set_callbacks(
            prerun=self.__prepare__,
            main_loop=self.__main__,
            postrun=self.__dispose__
        )
        self._config = Config.load_config()
        self._shm = indy_shm.IndyShmCommand(sync_mode=False, joint_dof=self._config[Config.CONFIG_KEY_ROBOT_DOF])

        self._device_list = [
            SampleDevice
        ]#logger.info(f"{self.get_device_name()} - Execute (w/ Async)")
    
    def __prepare__(self, worker: worker.Worker, deltatime, logger: Logger) -> None:
        new_list = []
        for dev_class in self._device_list:
            if dev_class.is_singleton():
                dev = dev_class.get_instance()
            else:
                dev = dev_class()
            new_list.append(dev)
            
    
    def __main__(self, worker: worker.Worker, deltatime, logger: Logger) -> bool or None:
        pass

    def __dispose__(self, worker: worker.Worker, deltatime, logger: Logger) -> None:
        pass
    
    def run(self) -> None:
        self._logger.info("Reporter started.")
        self._session.open()
        self._worker.start()
        while self._worker.is_running():
            time.sleep(0.5)
        self._session.close()
        self._logger.info("Reporter finished.")
    
    def terminate(self) -> None:
        self._logger.info("Reporter terminating was requested.")
        self._worker.stop()
        Config.save_config(self._config)
