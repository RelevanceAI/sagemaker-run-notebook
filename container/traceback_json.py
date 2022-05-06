"""
Extract a structured traceback from an exception.

Copied and adapted from Rich:
https://github.com/Textualize/rich/blob/972dedff/rich/traceback.py
"""
import os
import sys
from traceback import walk_tb
from types import TracebackType
from typing import Any, List, Optional, Type, Union, Tuple, Dict

import attrs


SHOW_LOCALS = True
LOCALS_MAX_STRING = 80
MAX_FRAMES = 50

ExcInfo = Tuple[Type[BaseException], BaseException, Optional[TracebackType]]
OptExcInfo = Union[ExcInfo, Tuple[None, None, None]]


@attrs.define
class Frame:
    filename: str
    lineno: int
    name: str
    line: str = ""
    locals: Optional[Dict[str, str]] = None


@attrs.define
class SyntaxError_:  # pylint: disable=invalid-name
    offset: int
    filename: str
    line: str
    lineno: int
    msg: str


@attrs.define
class Stack:
    exc_type: str
    exc_value: str
    syntax_error: Optional[SyntaxError_] = None
    is_cause: bool = False
    frames: List[Frame] = attrs.field(factory=list)


@attrs.define
class Trace:
    stacks: List[Stack]


def safe_str(_object: Any) -> str:
    """Don't allow exceptions from __str__ to propegate."""
    try:
        return str(_object)
    except Exception as error:
        return f"<str-error {str(error)!r}>"


def to_repr(obj: Any, max_string: Optional[int] = None) -> str:
    """Get repr string for an object, but catch errors."""
    if isinstance(obj, str):
        obj_repr = obj
    else:
        try:
            obj_repr = repr(obj)
        except Exception as error:
            obj_repr = f"<repr-error {str(error)!r}>"

    if max_string is not None and len(obj_repr) > max_string:
        truncated = len(obj_repr) - max_string
        obj_repr = f"{obj_repr[:max_string]!r}+{truncated}"

    return obj_repr


def extract(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    traceback: Optional[TracebackType],
    *,
    show_locals: bool = False,
    locals_max_string: int = LOCALS_MAX_STRING,
) -> Trace:
    """
    Extract traceback information.

    Args:
        exc_type: Exception type.
        exc_value: Exception value.
        traceback: Python Traceback object.
        show_locals: Enable display of local variables. Defaults to False.
        locals_max_string: Maximum length of string before truncating, or ``None`` to
            disable.
        max_frames: Maximum number of frames in each stack

    Returns:
        Trace: A Trace instance which you can use to construct a :cls:`Traceback`.
    """

    stacks: list[Stack] = []
    is_cause = False

    while True:
        stack = Stack(
            exc_type=safe_str(exc_type.__name__),
            exc_value=safe_str(exc_value),
            is_cause=is_cause,
        )

        if isinstance(exc_value, SyntaxError):
            stack.syntax_error = SyntaxError_(
                offset=exc_value.offset or 0,
                filename=exc_value.filename or "?",
                lineno=exc_value.lineno or 0,
                line=exc_value.text or "",
                msg=exc_value.msg,
            )

        stacks.append(stack)
        append = stack.frames.append  # pylint: disable=no-member

        for frame_summary, line_no in walk_tb(traceback):
            filename = frame_summary.f_code.co_filename
            if filename and not filename.startswith("<"):
                filename = os.path.abspath(filename)
            frame = Frame(
                filename=filename or "?",
                lineno=line_no,
                name=frame_summary.f_code.co_name,
                locals={
                    key: to_repr(value, max_string=locals_max_string)
                    for key, value in frame_summary.f_locals.items()
                }
                if show_locals
                else None,
            )
            append(frame)

        cause = getattr(exc_value, "__cause__", None)
        if cause and cause.__traceback__:
            exc_type = cause.__class__
            exc_value = cause
            traceback = cause.__traceback__
            is_cause = True
            continue

        cause = exc_value.__context__
        if (
            cause
            and cause.__traceback__
            and not getattr(exc_value, "__suppress_context__", False)
        ):
            exc_type = cause.__class__
            exc_value = cause
            traceback = cause.__traceback__
            is_cause = False
            continue

        # No cover, code is reached but coverage doesn't recognize it.
        break  # pragma: no cover

    trace = Trace(stacks=stacks)
    return trace


def get_exc_info(v: Any) -> OptExcInfo:
    """
    Return an exception info tuple for the input value.

    Args:
        v: Usually an :exc:`BaseException` instance or an exception tuple
            ``(exc_cls, exc_val, traceback)``.  If it is someting ``True``-ish, use
            :func:`sys.exc_info()` to get the exception info.

    Return:
        An exception info tuple or ``(None, None, None)`` if there was no exception.
    """
    if isinstance(v, BaseException):
        return (type(v), v, v.__traceback__)

    if isinstance(v, tuple):
        return v  # type: ignore

    if v:
        return sys.exc_info()

    return (None, None, None)


def get_traceback_dicts(
    exception: Any,
    show_locals: bool = True,
    locals_max_string: int = LOCALS_MAX_STRING,
    max_frames: int = MAX_FRAMES,
) -> List[Dict[str, Any]]:
    """
    Return a list of exception stack dictionaries for *exception*.

    These dictionaries are based on :cls:`Stack` instances generated by
    :func:`extract()` and can be dumped to JSON.
    """
    if locals_max_string < 0:
        raise ValueError(f'"locals_max_string" must be >= 0: {locals_max_string}')
    if max_frames < 2:
        raise ValueError(f'"max_frames" must be >= 2: {max_frames}')

    exc_info = get_exc_info(exception)
    if exc_info == (None, None, None):
        return []

    trace = extract(
        *exc_info, show_locals=show_locals, locals_max_string=locals_max_string
    )

    for stack in trace.stacks:
        if len(stack.frames) <= max_frames:
            continue

        half = max_frames // 2  # Force int division to handle odd numbers correctly
        fake_frame = Frame(
            filename="",
            lineno=-1,
            name=f"Skipped frames: {len(stack.frames) - (2 * half)}",
        )
        stack.frames[:] = [*stack.frames[:half], fake_frame, *stack.frames[-half:]]

    stack_dicts = [attrs.asdict(stack) for stack in trace.stacks]
    return stack_dicts


#
# Demo
#
import sys

import orjson
import structlog
from structlog import wrap_logger
from structlog.processors import _json_fallback_handler as orjson_fallback_handler
from structlog.types import EventDict, WrappedLogger


def render_orjson(_logger: WrappedLogger, _name: str, event_dict: EventDict) -> str:
    """
    Modified version of :class:`structlog.processors.JSONRenderer` that works around
    the issues in https://github.com/hynek/structlog/issues/360
    """
    exc_info = event_dict.pop("exc_info", None)
    if exc_info:
        event_dict["exception"] = get_traceback_dicts(exc_info)
    return orjson.dumps(event_dict, default=orjson_fallback_handler).decode()


# def configure_traceback_json_logger(filename:str):
#     def mydumps(dic, **kw):
#         import json
#         # mod = {}
#         # if 'event' in dic:
#         #     mod["event"] = dic["event"]
#         # for k in dic:
#         #     if k!="event":
#         #         mod[k] = dic[k]
#         return json.dumps(dic,**kw)

#     import logging

#     if filename:
#         args={
#             'filename': filename
#         }
#     # logging.basicConfig(format="%(message)s", **args)

# processors = [
#         structlog.processors.add_log_level,
#         structlog.processors.TimeStamper(),
#     ]
# processors.append(render_orjson)
# # processors.append(structlog.processors.JSONRenderer())
# # processors.append()
# # processors.append(structlog.processors.JSONRenderer(serializer=mydumps))

# # logger = wrap_logger(
# #     logging.getLogger(__name__),
# #     processors=processors,
# # )

# structlog.configure(
#     processors=processors,
# )
# logger = structlog.get_logger()

# return logger


import execute as e

# from execute import run_notebook


def fail():
    # 1 / 0
    e.run_notebook()


def main():
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(),
    ]
    if sys.stdout.isatty():
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(render_orjson)
    # A list of functions that will be called in order to process the log event.
    # processors.append(structlog.processors.JSONRenderer(serializer=mydumps))

    structlog.configure(
        processors=processors,
    )
    log = structlog.get_logger()
    # log.info("ohai")

    try:
        fail()
    except Exception as e:
        log.exception(e, exc_info=e)


if __name__ == "__main__":
    main()
