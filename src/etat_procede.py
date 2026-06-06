"""Lecture et interpretation de l'etat procede."""

from __future__ import annotations

from dataclasses import dataclass, field

from .modbus_service import (
    COIL_SUP_CONV1,
    COIL_SUP_CONV2,
    COIL_SUP_CONV3,
    COIL_SUP_CYC_M,
    COIL_SUP_CYC_R,
    COIL_SUP_CYC_V,
    REG_DEBIT_1,
    REG_DEBIT_2,
    REG_DEBIT_3,
    REG_SUP_NIV_C,
    ModbusService,
)


PHASE_ARRET = "ARRET"
PHASE_REMPLISSAGE = "REMPLISSAGE/MELANGE"
PHASE_EMBOUTEILLAGE = "EMBOUTEILLAGE"
PHASE_ARRET_URGENCE = "ARRET_URGENCE"
PHASE_INCOHERENT = "ETAT_INCOHERENT"
PHASE_COMM_PERDUE = "COMMUNICATION_PERDUE"

NIVEAU_MIN = 0
NIVEAU_MAX = 10000
DEBIT_MIN = 0
DEBIT_MAX = 500


@dataclass
class EtatProcede:
    communication_ok: bool = False
    systeme: bool = False
    remplissage: bool = False
    embouteillage: bool = False
    p1: bool = False
    p2: bool = False
    p3: bool = False
    niveau: int | None = None
    niveau_pct: float | None = None
    debit_1: int | None = None
    debit_2: int | None = None
    debit_3: int | None = None
    phase: str = PHASE_COMM_PERDUE
    alarmes: list[str] = field(default_factory=list)


def valider_debit(valeur: object) -> tuple[bool, int | None, str]:
    """Valide une valeur utilisateur avant ecriture Modbus."""
    if isinstance(valeur, bool):
        return False, None, "Le debit doit etre un entier entre 0 et 500."
    try:
        if isinstance(valeur, str):
            texte = valeur.strip()
            if texte == "":
                raise ValueError
            debit = int(texte, 10)
        elif isinstance(valeur, int):
            debit = valeur
        else:
            raise ValueError
    except (TypeError, ValueError):
        return False, None, "Valeur refusee: saisissez un entier numerique."

    if debit < DEBIT_MIN:
        return False, None, "Valeur refusee: le debit ne peut pas etre negatif."
    if debit > DEBIT_MAX:
        return False, None, "Valeur refusee: le debit ne peut pas depasser 500."
    return True, debit, "Debit valide."


def _debit_hors_plage(valeur: int | None) -> bool:
    return valeur is None or valeur < DEBIT_MIN or valeur > DEBIT_MAX


def determiner_phase(etat: EtatProcede) -> str:
    if not etat.communication_ok:
        return PHASE_COMM_PERDUE

    if etat.remplissage and etat.embouteillage:
        return PHASE_INCOHERENT
    if etat.niveau is None or etat.niveau < NIVEAU_MIN or etat.niveau > NIVEAU_MAX:
        return PHASE_INCOHERENT
    if any(_debit_hors_plage(v) for v in (etat.debit_1, etat.debit_2, etat.debit_3)):
        return PHASE_INCOHERENT

    if etat.remplissage:
        if not (etat.p1 and etat.p2) or etat.p3:
            return PHASE_INCOHERENT
        return PHASE_REMPLISSAGE

    if etat.embouteillage:
        if etat.p1 or etat.p2 or not etat.p3:
            return PHASE_INCOHERENT
        return PHASE_EMBOUTEILLAGE

    if etat.systeme and not (etat.p1 or etat.p2 or etat.p3):
        return PHASE_ARRET_URGENCE
    if etat.p1 or etat.p2 or etat.p3:
        return PHASE_INCOHERENT
    return PHASE_ARRET


def lire_etat(service: ModbusService) -> EtatProcede:
    """Lit toutes les variables Modbus et retourne un etat structure."""
    service.connecter()
    if not service.communication_ok:
        return EtatProcede(communication_ok=False, phase=PHASE_COMM_PERDUE)

    values = {
        "systeme": service.lire_bit(COIL_SUP_CYC_M),
        "remplissage": service.lire_bit(COIL_SUP_CYC_R),
        "embouteillage": service.lire_bit(COIL_SUP_CYC_V),
        "p1": service.lire_bit(COIL_SUP_CONV1),
        "p2": service.lire_bit(COIL_SUP_CONV2),
        "p3": service.lire_bit(COIL_SUP_CONV3),
        "niveau": service.lire_registre(REG_SUP_NIV_C),
        "debit_1": service.lire_registre(REG_DEBIT_1),
        "debit_2": service.lire_registre(REG_DEBIT_2),
        "debit_3": service.lire_registre(REG_DEBIT_3),
    }
    communication_ok = service.communication_ok and all(v is not None for v in values.values())
    niveau = values["niveau"] if isinstance(values["niveau"], int) else None
    niveau_pct = None if niveau is None else niveau / NIVEAU_MAX * 100.0

    etat = EtatProcede(
        communication_ok=communication_ok,
        systeme=bool(values["systeme"]),
        remplissage=bool(values["remplissage"]),
        embouteillage=bool(values["embouteillage"]),
        p1=bool(values["p1"]),
        p2=bool(values["p2"]),
        p3=bool(values["p3"]),
        niveau=niveau,
        niveau_pct=niveau_pct,
        debit_1=values["debit_1"] if isinstance(values["debit_1"], int) else None,
        debit_2=values["debit_2"] if isinstance(values["debit_2"], int) else None,
        debit_3=values["debit_3"] if isinstance(values["debit_3"], int) else None,
    )
    etat.phase = determiner_phase(etat)
    return etat
