"""Journalisation CSV non bloquante."""

from __future__ import annotations

import csv
import queue
import threading
import time
from pathlib import Path

from .etat_procede import EtatProcede


class HistoriqueCSV:
    colonnes = [
        "time",
        "phase",
        "level",
        "level_pct",
        "d1",
        "d2",
        "d3",
        "p1",
        "p2",
        "p3",
        "alarms",
    ]

    def __init__(self, chemin: str | Path = "historique.csv") -> None:
        self.chemin = Path(chemin)
        self._file = self.chemin.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.colonnes)
        self._writer.writeheader()
        self._file.flush()
        self._queue: queue.Queue[dict[str, object] | None] = queue.Queue()
        self._thread = threading.Thread(target=self._boucle_ecriture, daemon=True)
        self._thread.start()

    def enregistrer(self, etat: EtatProcede) -> None:
        ligne = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "phase": etat.phase,
            "level": "" if etat.niveau is None else etat.niveau,
            "level_pct": "" if etat.niveau_pct is None else f"{etat.niveau_pct:.1f}",
            "d1": "" if etat.debit_1 is None else etat.debit_1,
            "d2": "" if etat.debit_2 is None else etat.debit_2,
            "d3": "" if etat.debit_3 is None else etat.debit_3,
            "p1": int(etat.p1),
            "p2": int(etat.p2),
            "p3": int(etat.p3),
            "alarms": " | ".join(etat.alarmes),
        }
        self._queue.put(ligne)

    def fermer(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=2.0)
        self._file.flush()
        self._file.close()

    def _boucle_ecriture(self) -> None:
        while True:
            ligne = self._queue.get()
            if ligne is None:
                break
            self._writer.writerow(ligne)
            self._file.flush()
