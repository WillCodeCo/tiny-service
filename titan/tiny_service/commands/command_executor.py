from titan.tiny_service.commands.command import Command

class CommandExecutorException(Exception):
    pass

class CommandExecutor:
    def execute_command(self, command: Command):
        raise NotImplementedError


class AsyncCommandExecutor(CommandExecutor):
    async def execute_command(self, command: Command):
        raise NotImplementedError