"""Gestion des alarmes instantanees et temporelles."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .etat_procede import (
    DEBIT_MAX,
    DEBIT_MIN,
    NIVEAU_MAX,
    NIVEAU_MIN,
    PHASE_EMBOUTEILLAGE,
    PHASE_INCOHERENT,
    PHASE_REMPLISSAGE,
    EtatProcede,
)


@dataclass
class AlarmManager:
    variation_min: int = 20
    duree_blocage: float = 5.0

    def __post_init__(self) -> None:
        self._niveau_ref: int | None = None
        self._temps_ref = time.monotonic()
        self._derniere_phase: str | None = None
        self.alarme_utilisateur: str | None = None

    def signaler_valeur_refusee(self, message: str) -> None:
        self.alarme_utilisateur = message

    def acquitter_valeur_refusee(self) -> None:
        self.alarme_utilisateur = None

    def verifier_alarmes(self, etat: EtatProcede) -> list[str]:
        alarmes: list[str] = []

        if not etat.communication_ok:
            alarmes.append("Perte de communication Modbus")
            self._reset_suivi_niveau(etat)
            etat.alarmes = alarmes
            return alarmes

        if etat.phase == "ARRET_URGENCE":
            alarmes.append("Arret d'urgence actif")
        if etat.remplissage and etat.embouteillage:
            alarmes.append("Deux phases actives en meme temps")
        if etat.niveau is None or etat.niveau < NIVEAU_MIN or etat.niveau > NIVEAU_MAX:
            alarmes.append("Niveau hors plage")
        if any(
            d is None or d < DEBIT_MIN or d > DEBIT_MAX
            for d in (etat.debit_1, etat.debit_2, etat.debit_3)
        ):
            alarmes.append("Debit hors plage")
        if etat.phase == PHASE_INCOHERENT:
            alarmes.append("Pompe active incoherente avec la phase")

        alarme_blocage = self._verifier_niveau_bloque(etat)
        if alarme_blocage:
            alarmes.append(alarme_blocage)

        if self.alarme_utilisateur:
            alarmes.append("Valeur utilisateur refusee: " + self.alarme_utilisateur)

        etat.alarmes = alarmes
        return alarmes

    def _reset_suivi_niveau(self, etat: EtatProcede) -> None:
        self._niveau_ref = etat.niveau
        self._temps_ref = time.monotonic()
        self._derniere_phase = etat.phase

    def _verifier_niveau_bloque(self, etat: EtatProcede) -> str | None:
        if etat.niveau is None or etat.phase not in (PHASE_REMPLISSAGE, PHASE_EMBOUTEILLAGE):
            self._reset_suivi_niveau(etat)
            return None

        if self._niveau_ref is None or etat.phase != self._derniere_phase:
            self._reset_suivi_niveau(etat)
            return None

        variation = etat.niveau - self._niveau_ref
        maintenant = time.monotonic()

        if etat.phase == PHASE_REMPLISSAGE and variation >= self.variation_min:
            self._reset_suivi_niveau(etat)
            return None
        if etat.phase == PHASE_EMBOUTEILLAGE and variation <= -self.variation_min:
            self._reset_suivi_niveau(etat)
            return None

        if maintenant - self._temps_ref >= self.duree_blocage:
            if etat.phase == PHASE_REMPLISSAGE:
                return "Niveau bloque pendant le remplissage"
            return "Niveau bloque pendant l'embouteillage"
        return None


def verifier_alarmes(etat: EtatProcede) -> list[str]:
    """Fonction simple pour les usages sans etat temporel persistant."""
    return AlarmManager().verifier_alarmes(etat)
