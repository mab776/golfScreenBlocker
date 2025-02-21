from io import TextIOWrapper
import os
from pathlib import Path
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Optional, TextIO, Tuple, Type, Union

# logger object to write console into console and file
# it will also create a new file for every day

LOG_FOLDER = Path('logs')

if not LOG_FOLDER.exists():
    os.makedirs(LOG_FOLDER)


def touchFile(path: Union[str, Path]) -> None:
    '''
    create an empty file if it doesn't exist,
    also create the parent folder if it doesn't exist
    '''
    path = Path(path)
    if not path.exists():
        path.touch()


class Logger(object):
    # singleton, this class cannot exist twice
    __shared_state: dict = {}

    def __init__(self, doFileLogging: bool = True):
        # singleton
        self.__dict__ = self.__shared_state

        self.doFileLogging: bool = doFileLogging
        self.formatFile: str = "%Y-%m-%d.log"
        self.now: datetime = datetime.now(tz=timezone.utc)
        self.fileName: str = self.now.strftime(self.formatFile)
        self.file: Path = LOG_FOLDER / self.fileName
        # save then override terminal
        self.terminal: TextIO = sys.stdout
        sys.stdout = self

        self.log: Optional[TextIOWrapper] = None
        if self.doFileLogging:
            touchFile(self.file)
            self.log = open(self.file, "a")

        # Set the global exception handler
        sys.excepthook = self.globalExceptionHandler

        print()
        print()
        print("*****************************************")
        print("*          SCREEN BLOCKER BOOT          *")
        print("*****************************************")
        print()
        print()

    def write(self, *args: Any) -> None:
        if not args:
            return

        self.compareFileName()
        if len(args) == 1 and args[0] == '\n':
            time: str = ''
        else:
            time: str = self.now.strftime("%H:%M:%S.%f")[:-3] + " "
        messageStr: str = ""
        for arg in args:
            messageStr += str(arg)

        # hack for progress bars
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
        self.now = datetime.now(tz=timezone.utc)
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
                touchFile(self.file)
                self.log = open(self.file, "a")

    def flush(self) -> None:
        if self.log is not None:
            self.log.flush()
        self.terminal.flush()

    def globalExceptionHandler(self, exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Any) -> None:
        # Print the exception type, value, and traceback
        traces: list[str] = traceback.format_tb(exc_traceback)
        traceTuple: Tuple[str, ...] = ()
        for trace in traces:
            traceTuple += (trace + '\r\n',)
        exception: str = '{}: {}'.format(type(exc_type).__name__, exc_type)
        self.write("EXCEPTION: ", exception, '\r\n', exc_value, '\r\n', *traceTuple, '\r\n')
        self.flush()
