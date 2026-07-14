"""Per-processing-call budget shared safely across concurrent extraction nodes."""
from contextvars import ContextVar
from contextlib import contextmanager
from threading import Lock
from app.core.config import settings


class ProviderBudgetExceeded(RuntimeError): pass


class ProviderBudget:
    def __init__(self, max_calls=None, max_output_tokens=None):
        self.max_calls = max_calls if max_calls is not None else settings.provider_max_calls
        self.max_output_tokens = max_output_tokens if max_output_tokens is not None else settings.provider_max_output_tokens
        self.calls = self.reserved_output = self.input_tokens = self.output_tokens = 0
        self.exhausted = False
        self.stage_timings = {}
        self.lock = Lock()

    def reserve(self, output_tokens):
        with self.lock:
            if self.calls >= self.max_calls or self.reserved_output+output_tokens > self.max_output_tokens:
                self.exhausted = True
                raise ProviderBudgetExceeded("Provider budget exhausted; human review is required.")
            self.calls += 1
            self.reserved_output += output_tokens

    def usage(self, input_tokens=0, output_tokens=0):
        with self.lock:
            self.input_tokens += int(input_tokens or 0)
            self.output_tokens += int(output_tokens or 0)

    def snapshot(self):
        with self.lock:
            return {"calls": self.calls, "reserved_output_tokens": self.reserved_output, "input_tokens": self.input_tokens, "output_tokens": self.output_tokens, "exhausted": self.exhausted, "cost": None, "stage_timings_ms": dict(self.stage_timings)}


_current: ContextVar[ProviderBudget | None] = ContextVar("provider_budget", default=None)


@contextmanager
def budget_scope():
    budget = ProviderBudget()
    token = _current.set(budget)
    try: yield budget
    finally: _current.reset(token)


def reserve(tokens):
    budget = _current.get()
    if budget is not None: budget.reserve(tokens)


def record_usage(input_tokens=0, output_tokens=0):
    budget = _current.get()
    if budget is not None: budget.usage(input_tokens, output_tokens)


def record_stage(name, milliseconds):
    budget = _current.get()
    if budget is not None:
        with budget.lock: budget.stage_timings[name] = budget.stage_timings.get(name, 0)+milliseconds
