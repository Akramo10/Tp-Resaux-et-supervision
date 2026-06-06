"""Envoi non bloquant des alarmes par email avec l'API Resend."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .etat_procede import EtatProcede


RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "Supervision Jus <Akram.Alerte@telxia.fr>"


@dataclass
class EmailAlertConfig:
    api_key: str
    destinataire: str
    expediteur: str = DEFAULT_FROM
    delai_min: float = 60.0


class EmailAlertService:
    """Envoie un mail seulement quand une nouvelle alarme apparait."""

    def __init__(self, config: EmailAlertConfig | None = None) -> None:
        self.config = config or self.from_env()
        self._queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._dernier_envoi: dict[str, float] = {}
        self._actives_precedentes: set[str] = set()

        if self.est_configure:
            self._thread = threading.Thread(target=self._boucle_envoi, daemon=True)
            self._thread.start()

    @staticmethod
    def from_env() -> EmailAlertConfig:
        return EmailAlertConfig(
            api_key=os.getenv("RESEND_API_KEY", "").strip(),
            destinataire=os.getenv("ALERTE_EMAIL_DEST", "").strip(),
            expediteur=os.getenv("ALERTE_EMAIL_FROM", DEFAULT_FROM).strip(),
        )

    @property
    def est_configure(self) -> bool:
        return bool(self.config.api_key and self.config.destinataire)

    def definir_destinataire(self, email: str) -> None:
        self.config.destinataire = email.strip()
        if self.config.api_key and self.config.destinataire and self._thread is None:
            self._thread = threading.Thread(target=self._boucle_envoi, daemon=True)
            self._thread.start()

    def envoyer_test(self) -> tuple[bool, str]:
        if not self.config.api_key:
            return False, "Cle Resend manquante"
        if not self.config.destinataire:
            return False, "Adresse destinataire manquante"
        self._queue.put(
            (
                "Test alerte supervision jus",
                "Ceci est un email de test envoye depuis l'interface de supervision.",
            )
        )
        return True, "Email de test envoye"

    def notifier_si_nouvelles(self, etat: EtatProcede) -> None:
        if not self.est_configure:
            return

        alarmes_actives = set(etat.alarmes)
        nouvelles = sorted(alarmes_actives - self._actives_precedentes)
        self._actives_precedentes = alarmes_actives

        maintenant = time.monotonic()
        for alarme in nouvelles:
            dernier = self._dernier_envoi.get(alarme, 0.0)
            if maintenant - dernier < self.config.delai_min:
                continue
            self._dernier_envoi[alarme] = maintenant
            self._queue.put(self._preparer_email(alarme, etat))

    def fermer(self) -> None:
        if self._thread is None:
            return
        self._queue.put(None)
        self._thread.join(timeout=2.0)

    def _preparer_email(self, alarme: str, etat: EtatProcede) -> tuple[str, str]:
        sujet = f"Alerte supervision jus - {alarme}"
        niveau = "inconnu" if etat.niveau is None else f"{etat.niveau} ({etat.niveau_pct:.1f}%)"
        texte = (
            "Une alarme vient d'apparaitre sur la supervision de production de jus.\n\n"
            f"Alarme: {alarme}\n"
            f"Phase: {etat.phase}\n"
            f"Communication: {'OK' if etat.communication_ok else 'PERDUE'}\n"
            f"Niveau: {niveau}\n"
            f"Debits: D1={etat.debit_1}, D2={etat.debit_2}, D3={etat.debit_3}\n"
            f"Pompes: P1={etat.p1}, P2={etat.p2}, P3={etat.p3}\n"
            f"Toutes les alarmes: {', '.join(etat.alarmes)}\n"
        )
        return sujet, texte

    def _boucle_envoi(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                break
            sujet, texte = item
            try:
                self._envoyer(sujet, texte)
            except Exception as exc:
                print(f"Erreur envoi email alarme: {exc}")

    def _envoyer(self, sujet: str, texte: str) -> None:
        payload = {
            "from": self.config.expediteur,
            "to": [self.config.destinataire],
            "subject": sujet,
            "text": texte,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            RESEND_URL,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "supervision-jus/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Resend HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Resend HTTP {exc.code}: {detail}") from exc
