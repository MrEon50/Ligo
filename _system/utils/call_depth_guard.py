"""Call Depth Guard — zapobieganie infinite loops i rekurencji w ServiceRegistry.

Głębokość call chain jest śledzona na poziomie ServiceRegistry. Gdy wykryta zostanie
rekurencja (ten sam klucz powtarza się w aktywnym stacku) lub przekroczony zostanie
limit głębokości (domyślnie 20 wywołań), rzucony zostanie RuntimeError z jasnym msg,
że wykryto potencjalny infinite loop.

Używa prostego stack-based trackingu bez zewnętrznych zależności.
"""

from __future__ import annotations

import datetime as dt


class CallDepthGuard:
    """Śledzi głębokość aktywnych wywołań usług i blokuje rekurencję.

    Mechanizmy:
        1. **Call depth limit** — max_depth wywołań w aktywnej ścieżce (domyślnie 20)
        2. **Loop detection** — wykrywa cykl jeśli callee_key już występuje w aktywnym stacku
        3. **Anti-repetition** — liczy powtórzenia tego samego wywołania (proszek 3x)

    Przykład użycia:
        guard = CallDepthGuard(max_depth=20)
        chain = guard.get_chain()  # lista aktualnych wywołań
    """

    def __init__(self, max_depth: int = 20) -> None:
        self.max_depth = max_depth
        self._chain: list[tuple[str, str]] = []  # [(caller_key, callee_key)]
        self._errors: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_chain(self) -> list[dict[str, Any]]:
        """Zwróć aktualny call chain (deep copy)."""
        return [
            {"caller": caller, "callee": callee}
            for caller, callee in self._chain[:]
        ]

    def get_depth(self) -> int:
        """Aktualna głębokość call stacku."""
        return len(self._chain)

    def check(
        self, callee_key: str, caller_key: str | None = None
    ) -> dict[str, Any]:
        """Sprawdź czy wywołanie jest dozwolone. Zwróć wynik do logowania.

        Blokuje jeśli:
            -callee_key już występuje w aktywnym stacku (rekurencja/loop)
            -głębokość przekroczyłaby max_depth
        """
        current_depth = len(self._chain)
        new_depth = current_depth + 1

        # Check for loop: is callee_key already in the chain?
        if caller_key and self._key_in_chain(callee_key):
            return {
                "allowed": False,
                "error_code": "LOOP_DETECTED",
                "message": (
                    f"Loop detected! '{callee_key}' już występuje w call stacku. "
                    f"Aktualny chain: {' → '.join(f'{c}' for c, _ in self._chain)} → {callee_key}"
                ),
                "current_depth": current_depth,
                "loop_at_depth": new_depth,
            }

        # Check max depth limit
        if new_depth > self.max_depth:
            return {
                "allowed": False,
                "error_code": "MAX_DEPTH_EXCEEDED",
                "message": (
                    f"Max call depth exceeded ({new_depth} > {self.max_depth}). "
                    f"Possybilny infinite loop wykryty. "
                    f"Aktualny chain: {' → '.join(f'{c}' for c, _ in self._chain)} → {callee_key}"
                ),
                "current_depth": current_depth,
            }

        # Anti-repetition tracking — count how many times this key is called
        if callee_key not in self._errors:
            self._errors[callee_key] = 0

        self._errors[callee_key] += 1

        return {
            "allowed": True,
            "depth_after_call": new_depth,
            "repetition_count": self._errors[callee_key],
            "max_repetition_threshold": 3,
        }

    def _key_in_chain(self, key: str) -> bool:
        """Czy klucz już występuje w aktywnej ścieżce call chain?"""
        return any(callee == key for _, callee in self._chain)

    def push(self, caller_key: str, callee_key: str) -> None:
        """Dodać wywołanie na stack call chain."""
        self._chain.append((caller_key, callee_key))

    def pop(self) -> None:
        """Usunąć ostatnie wywołanie z stacku (po zakończeniu)."""
        if self._chain:
            self._chain.pop()

    def get_call_graph(self) -> dict[str, list[str]]:
        """Eksport grafu zależności: {caller_key: [callee_keys]}."""
        graph: dict[str, set[str]] = {}
        for caller, callee in self._chain:
            if caller not in graph:
                graph[caller] = set()
            graph[caller].add(callee)
        return {k: sorted(list(v)) for k, v in graph.items()}

    def get_repetition_report(self) -> dict[str, int]:
        """Zwrot raportu powtórzeń — które usługi są wywoływane najczęściej."""
        report: dict[str, int] = {}
        for key, count in self._errors.items():
            if count > 1:
                report[key] = count
        return report

    def get_error_count(self) -> int:
        """Suma błędów powtórzeń przekraczających próg."""
        return sum(1 for v in self._errors.values() if v >= 3)
