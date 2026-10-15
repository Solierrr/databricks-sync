class SyncConfigurationError(RuntimeError):
    pass


class SyncExecutionError(RuntimeError):
    def __init__(self, summary: dict):
        self.summary = summary
        super().__init__("One or more tables failed to synchronize")


class JobAlreadyRunning(RuntimeError):
    pass
