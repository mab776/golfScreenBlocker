import os
import sys
import traceback
from pathlib import Path
from io import TextIOWrapper
from datetime import datetime, timedelta
from typing import Any, Optional, TextIO, Tuple, Type, Union

LOG_FOLDER = Path('logs')
KEEP_LOGS_FOR_DAYS = 30

if not LOG_FOLDER.exists():
    os.makedirs(LOG_FOLDER)


def touchFile(path: Union[str, Path]) -> None:
    '''
    Create an empty file if it doesn't exist.
    '''
    path = Path(path)
    if not path.exists():
        path.touch()


def purge_old_logs() -> None:
    '''
    Delete log files older than KEEP_LOGS_FOR_DAYS based on the date extracted from the file name.
    Expected file name format: YYYY-MM-DD.log
    '''
    cutoff_date = datetime.now() - timedelta(days=KEEP_LOGS_FOR_DAYS)
    for logfile in LOG_FOLDER.glob("*.log"):
        try:
            file_date = datetime.strptime(logfile.stem, "%Y-%m-%d")
            if file_date < cutoff_date:
                logfile.unlink()
        except Exception as e:
            sys.stderr.write(f"Failed to parse or delete {logfile}: {e}\n")


class Logger(object):
    # singleton, this class cannot exist twice
    __shared_state: dict = {}

    def __init__(self, moduleName: str, doFileLogging: bool = True):
        # singleton
        self.__dict__ = self.__shared_state

        self.doFileLogging: bool = doFileLogging
        self.formatFile: str = "%Y-%m-%d.log"
        self.now: datetime = datetime.now()
        self.fileName: str = self.now.strftime(self.formatFile)
        self.file: Path = LOG_FOLDER / self.fileName
        self.moduleName: str = moduleName
        # save then override terminal
        self.terminal: TextIO = sys.__stdout__
        sys.stdout = self

        self.log: Optional[TextIOWrapper] = None
        if self.doFileLogging:
            # Purge logs older than 30 days before creating/opening today's log file.
            purge_old_logs()
            touchFile(self.file)
            self.log = open(self.file, "a")

        # Set the global exception handler
        sys.excepthook = self.globalExceptionHandler

        bootLogo: str = f"*      {self.moduleName} BOOT      *"

        print()
        print()
        print("*" * len(bootLogo))
        print(bootLogo)
        print("*" * len(bootLogo))
        print()
        print()

    def write(self, *args: Any) -> None:
        if not args:
            return

        self.compareFileName()
        # If the only argument is a newline, don't print the time.
        if len(args) == 1 and args[0] == '\n':
            time: str = ''
        else:
            time: str = self.now.strftime("%H:%M:%S.%f")[:-3] + " "
        messageStr: str = ""
        for arg in args:
            messageStr += str(arg)

        # Hack for progress bars.
        index: int = messageStr[:20].find('[')
        if index >= 0 and len(messageStr) > index+2 and messageStr[index+1] in {".", ">", "="}:
            messageStr = '\r' + messageStr[1:]

        if messageStr:
            if messageStr[0] == '\r':
                messageStrTime: str = messageStr[:1] + time + messageStr[1:]
            else:
                messageStrTime: str = time + messageStr
        else:
            messageStrTime: str = messageStr

        # avoid printing progress bar over several lines
        if self.log is not None and messageStr and messageStr[-1] != '\r' and messageStr[0] != '\r' and self.doFileLogging:
            self.log.write(messageStrTime)

        self.terminal.write(messageStrTime)

    def fillFileName(self) -> None:
        self.now = datetime.now()
        self.fileName = self.now.strftime(self.formatFile)

    def compareFileName(self) -> None:
        oldName: str = self.fileName
        self.fillFileName()
        if oldName != self.fileName:
            self.flush()
            if self.log is not None:
                self.log.close()
            self.file = LOG_FOLDER / self.fileName
            if self.doFileLogging:
                # Purge logs older than 30 days before creating/opening today's log file.
                purge_old_logs()
                touchFile(self.file)
                self.log = open(self.file, "a")

    def flush(self) -> None:
        if self.log is not None:
            self.log.flush()
        self.terminal.flush()

    def globalExceptionHandler(self, exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        # Print the exception type, value, and traceback.
        traces: list[str] = traceback.format_tb(exc_traceback)
        traceTuple: Tuple[str, ...] = ()
        for trace in traces:
            traceTuple += (trace + '\r\n',)
        exception: str = '{}: {}'.format(type(exc_type).__name__, exc_type)
        self.write("EXCEPTION: ", exception, '\r\n', exc_value, '\r\n', *traceTuple, '\r\n')
        self.flush()
