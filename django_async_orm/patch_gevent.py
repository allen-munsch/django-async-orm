from concurrent.futures import Future
import concurrent.futures.TimeoutError
from gevent import monkey

from gevent.timeout import Timeout as GTimeout
from gevent._util import Lazy
from concurrent.futures import _base as cfb


def _ignore_error(future_proxy, fn):
    def cbwrap(_):
        del _
        # We're called with the async result (from the threadpool), but
        # be sure to pass in the user-visible _FutureProxy object..
        try:
            fn(future_proxy)
        except Exception: # pylint: disable=broad-except
            # Just print, don't raise to the hub's parent.
            future_proxy.hub.print_exception((fn, future_proxy), None, None, None)
    return cbwrap


def _wrap(future_proxy, fn):
    def f(_):
        fn(future_proxy)
    return f


class _FutureProxy(Future):
    def __init__(self, asyncresult):
        super(_FutureProxy, self).__init__()
        self.asyncresult = asyncresult

    # Internal implementation details of a c.f.Future
    @Lazy
    def _condition(self):
        if monkey.is_module_patched('threading') or self.done():
            import threading
            return threading.Condition()
        # We can only properly work with conditions
        # when we've been monkey-patched. This is necessary
        # for the wait/as_completed module functions.
        raise AttributeError("_condition fffffffffffffffffffffffffffff")

    @Lazy
    def _waiters(self):
        self.asyncresult.rawlink(self.__when_done)
        return []

    def __when_done(self, _):
        # We should only be called when _waiters has
        # already been accessed.
        waiters = getattr(self, '_waiters')
        for w in waiters: # pylint:disable=not-an-iterable
            if self.successful():
                w.add_result(self)
            else:
                w.add_exception(self)

    @property
    def _state(self):
        if self.done():
            return cfb.FINISHED
        return cfb.RUNNING

    def set_running_or_notify_cancel(self):
        # Does nothing, not even any consistency checks. It's
        # meant to be internal to the executor and we don't use it.
        return

    def result(self, timeout=None):
        try:
            return self.asyncresult.result(timeout=timeout)
        except GTimeout:
            # XXX: Theoretically this could be a completely
            # unrelated timeout instance. Do we care about that?
            raise concurrent.futures.TimeoutError()

    def exception(self, timeout=None):
        try:
            self.asyncresult.get(timeout=timeout)
            return self.asyncresult.exception
        except GTimeout:
            raise concurrent.futures.TimeoutError()

    def add_done_callback(self, fn):
        """Exceptions raised by *fn* are ignored."""
        if self.done():
            fn(self)
        else:
            self.asyncresult.rawlink(_ignore_error(self, fn))

    def rawlink(self, fn):
        self.asyncresult.rawlink(_wrap(self, fn))

    def __str__(self):
        return str(self.asyncresult)

    def __getattr__(self, name):
        print(self, name, 'gggggggggggggggggggggggg')
        return getattr(self.asyncresult, name)

