"""Supervision terminale pour tester le serveur Modbus avant le GUI."""

from __future__ import annotations

import os
import sys
import time

from src.alarm_manager import AlarmManager
from src.email_alerts import EmailAlertService
from src.etat_procede import lire_etat, valider_debit
from src.historique_csv import HistoriqueCSV
from src.modbus_service import (
    COIL_FORC_ARR,
    COIL_FORC_MAR,
    REG_DEBIT_1,
    REG_DEBIT_2,
    REG_DEBIT_3,
    ModbusService,
)


def effacer() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def afficher_etat(etat) -> None:
    print("=== Supervision terminal - Production de jus ===")
    print(f"Communication : {'OK' if etat.communication_ok else 'PERDUE'}")
    print(f"Phase         : {etat.phase}")
    print(f"Pompes        : P1={etat.p1} P2={etat.p2} P3={etat.p3}")
    niveau_pct = "?" if etat.niveau_pct is None else f"{etat.niveau_pct:.1f}%"
    print(f"Niveau        : {etat.niveau if etat.niveau is not None else '?'} ({niveau_pct})")
    print(f"Debits        : D1={etat.debit_1} D2={etat.debit_2} D3={etat.debit_3}")
    print("Alarmes       : " + (", ".join(etat.alarmes) if etat.alarmes else "Aucune"))
    print()
    print("1 Demarrer | 2 Arret urgence | 3 Reset arret | 4 Debit 1 | 5 Debit 2 | 6 Debit 3 | q Quitter")


def modifier_debit(service: ModbusService, alarmes: AlarmManager, registre: int) -> None:
    valeur = input("Nouvelle valeur de debit (0..500): ")
    ok, debit, message = valider_debit(valeur)
    if not ok or debit is None:
        alarmes.signaler_valeur_refusee(message)
        print(message)
        time.sleep(1.2)
        return
    alarmes.acquitter_valeur_refusee()
    if not service.ecrire_registre(registre, debit):
        print("Ecriture Modbus impossible.")
        time.sleep(1.2)


def main() -> int:
    service = ModbusService()
    alarmes = AlarmManager()
    emails = EmailAlertService()
    historique = HistoriqueCSV()
    dernier_csv = 0.0

    try:
        while True:
            etat = lire_etat(service)
            alarmes.verifier_alarmes(etat)
            emails.notifier_si_nouvelles(etat)
            maintenant = time.monotonic()
            if maintenant - dernier_csv >= 1.0:
                historique.enregistrer(etat)
                dernier_csv = maintenant

            effacer()
            afficher_etat(etat)
            choix = input("Commande (Entree pour rafraichir): ").strip().lower()

            if choix == "q":
                return 0
            if not choix:
                continue
            if not etat.communication_ok:
                print("Commande ignoree: communication Modbus perdue.")
                time.sleep(1.2)
                continue
            if choix == "1":
                service.ecrire_bit(COIL_FORC_MAR, True)
            elif choix == "2":
                service.ecrire_bit(COIL_FORC_ARR, True)
            elif choix == "3":
                service.ecrire_bit(COIL_FORC_ARR, False)
            elif choix == "4":
                modifier_debit(service, alarmes, REG_DEBIT_1)
            elif choix == "5":
                modifier_debit(service, alarmes, REG_DEBIT_2)
            elif choix == "6":
                modifier_debit(service, alarmes, REG_DEBIT_3)
            else:
                print("Commande inconnue.")
                time.sleep(1.0)
    except KeyboardInterrupt:
        return 0
    finally:
        emails.fermer()
        historique.fermer()
        service.fermer()


if __name__ == "__main__":
    sys.exit(main())
