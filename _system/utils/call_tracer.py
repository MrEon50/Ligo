"""Call Tracer — śledzenie call chain między modułami dla debugowania i profilingu.

Każde wywołanie usługi jest rejestrowane z:
    - caller_key → callee_key (kto wywołał kogo)
    - timestamp + duration_ms
    - depth w call stacku

Eksport do JSON grafu zależności służącego do wizualizacji przepływu danych.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any


class CallTracer:
    """Śledzi wywołania usług i generuje call graph dla debugowania.

    Użyj:
        tracer = CallTracer(max_depth=20)
        trace_entry = tracer.trace(caller_key="main", callee_key="greeting.pl")
        service = registry.get_service("greeting.pl")  # wrapper weryfikuje depth
        tracer.end(trace_entry)

    Po zakończeniu pracy:
        graph = tracer.export_call_graph()  # {"caller": ["callee1", "callee2"]}
        json.dump(graph, open("call_trace.json", "w"))
    """

    def __init__(self, max_depth: int = 20) -> None:
        self.max_depth = max_depth
        self._active_chain: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Trace API
    # ------------------------------------------------------------------

    def trace(self, caller_key: str, callee_key: str) -> dict[str, Any]:
        """Zarejestruj wywołanie usługi. Zwracany obiekt do end() po zakończeniu."""
        start_time = time.time()
        depth = len(self._active_chain) + 1

        if depth > self.max_depth:
            raise RuntimeError(
                f"Call chain too deep ({depth} > {self.max_depth}). "
                f"Possible infinite recursion detected."
            )

        entry = {
            "caller_key": caller_key,
            "callee_key": callee_key,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "start_time": start_time,
            "depth": depth,
            "call_duration_ms": None,
        }

        self._active_chain.append(entry)
        return entry

    def end(self, trace_entry: dict[str, Any]) -> dict[str, Any]:
        """Zakończ wywołanie i zapisz duration. Pop z active chain."""
        if not self._active_chain:
            raise RuntimeError("No active call to close")

        entry = self._active_chain.pop()
        end_time = time.time()
        entry["call_duration_ms"] = round((end_time - entry["start_time"]) * 1000, 3)
        return entry

    def get_active_chain(self) -> list[dict[str, Any]]:
        """Zwrot aktywnego call chain (deep copy)."""
        return [dict(e) for e in self._active_chain]

    # ------------------------------------------------------------------
    # Export / Visualization
    # ------------------------------------------------------------------

    def export_call_graph(self) -> dict[str, list[str]]:
        """Eksport grafu zależności: {caller_key: [callee_keys]}."""
        graph: dict[str, set[str]] = {}

        for entry in self._active_chain:
            caller = entry["caller_key"]
            callee = entry["callee_key"]

            if caller not in graph:
                graph[caller] = set()
            graph[caller].add(callee)

        return {k: sorted(list(v)) for k, v in graph.items()}

    def export_full_trace(self) -> list[dict[str, Any]]:
        """Eksport pełnego logu wywołań (z duration)."""
        return [dict(e) for e in self._active_chain]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Podsumowanie statystyk profilowania."""
        if not self._active_chain:
            return {"total_calls": 0, "avg_duration_ms": None}

        durations = [e["call_duration_ms"] for e in self._active_chain if e["call_duration_ms"] is not None]
        total = len(self._active_chain)
        avg = sum(durations) / len(durations) if durations else 0
        max_dur = max(durations) if durations else 0

        return {
            "total_calls": total,
            "avg_duration_ms": round(avg, 3),
            "max_duration_ms": round(max_dur, 3),
            "active_chain_length": len(self._active_chain),
        }


class PerformanceProfiler:
    """Profilowanie wydajności modułów — wykrywa powolne usługi.

    Użyj jako wrapper wokół ServiceRegistry.get_service().
    Przykład:
        profiler = PerformanceProfiler()
        service = profiler.wrap(registry, "greeting.pl")  # returns wrapped callable
        result = service.greet("World", {"hour": 10})
        stats = profiler.get_stats()
    """

    def __init__(self) -> None:
        self._call_times: list[dict[str, Any]] = []

    def wrap(
        self,
        registry,
        key: str,
        caller_key: str | None = None,
    ) -> Any:
        """Zawieć usługę w profiler — zwraca proxy z mierzeniem czasu."""
        from utils.call_tracer import CallTracer

        tracer = CallTracer()
        trace_entry = tracer.trace(caller_key or "profiler", key)

        service = registry.get_service(key)

        # Stwórz proxy który mierzy czas wywołania
        class ProfilingProxy:
            def __init__(self, svc, entry):
                self._service = svc
                self._trace_entry = entry
                self.__class__ = type(svc.__class__.__name__, (svc.__class__,), {})  # hack

            def __getattr__(self, name: str) -> Any:
                attr = getattr(self._service, name)
                if callable(attr):
                    return _ProfilingMethodWrapper(attr, self._trace_entry, tracer)
                return attr

        proxy = ProfilingProxy(service, trace_entry)

        # Override __call__ for direct calls like registry.get_service("key")(...)
        class _CallWrapper:
            def __init__(self, svc):
                self._service = svc

            def __getattr__(self, name):
                attr = getattr(self._service, name)
                if callable(attr):
                    return _ProfilingMethodWrapper(attr, proxy._trace_entry, tracer)
                return attr

        return _CallWrapper(service)


class _ProfilingMethodWrapper:
    """Wrapp around a single method for timing measurement."""

    def __init__(self, func, trace_entry: dict[str, Any], tracer: CallTracer) -> None:
        self._func = func
        self._trace_entry = trace_entry
        self._tracer = tracer

    def __call__(self, *args, **kwargs):
        start = time.time()
        result = self._func(*args, **kwargs)
        end = time.time()
        duration_ms = (end - start) * 1000

        # Update trace entry with actual duration
        for entry in self._tracer.get_active_chain():
            if entry["callee_key"] == self._trace_entry["callee_key"]:
                entry["call_duration_ms"] = round(duration_ms, 3)
                break

        return result

    def __repr__(self) -> str:
        method_name = getattr(self._func, "__name__", "?")
        duration = self._trace_entry.get("call_duration_ms") or "?"
        return f"<ProfilingMethod: {method_name} ({duration}ms)>"


if __name__ == "__main__":
    tracer = CallTracer()

    # Demo trace
    caller_keys = ["orchestrator.main", "registry.lookup"]
    callee_keys = ["greeting.pl", "notification.sms", "validation.checker"]

    for i, (caller, callee) in enumerate(zip(caller_keys, callee_keys)):
        entry = tracer.trace(caller, callee)
        import time; time.sleep(0.001)  # Simulate work
        tracer.end(entry)

    print("=== Call Graph ===")
    graph = tracer.export_call_graph()
    for caller, callees in graph.items():
        print(f"  {caller} → {', '.join(callees)}")

    print("\n=== Stats ===")
    print(json.dumps(tracer.get_stats(), indent=2))
