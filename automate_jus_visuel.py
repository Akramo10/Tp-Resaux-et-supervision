"""Simulateur Modbus TCP simple pour tester la supervision du TP.

Ce fichier remplace temporairement le simulateur fourni par l'enseignant si
celui-ci est absent. Il expose les adresses demandees sur 127.0.0.1:9502.
"""

from __future__ import annotations

import time

from pyModbusTCP.server import DataBank, ModbusServer


HOST = "127.0.0.1"
PORT = 9502

FORC_MAR = 201
FORC_ARR = 202
SUP_CYC_R = 300
SUP_CYC_V = 301
SUP_CYC_M = 302
SUP_CONV1 = 303
SUP_CONV2 = 304
SUP_CONV3 = 305

DEBIT_1 = 11
DEBIT_2 = 12
DEBIT_3 = 13
SUP_NIV_C = 30

NIVEAU_MIN = 0
NIVEAU_MAX = 10000
SEUIL_HAUT = 8200
SEUIL_BAS = 1200


class AutomateJus:
    def __init__(self) -> None:
        self.db = DataBank()
        self.server = ModbusServer(host=HOST, port=PORT, no_block=True, data_bank=self.db)
        self.marche = False
        self.arret_urgence = False
        self.phase = "ARRET"
        self.niveau = 1000
        self._initialiser_memoires()

    def _initialiser_memoires(self) -> None:
        self.db.set_holding_registers(DEBIT_1, [120])
        self.db.set_holding_registers(DEBIT_2, [120])
        self.db.set_holding_registers(DEBIT_3, [180])
        self.db.set_holding_registers(SUP_NIV_C, [self.niveau])
        self._set_coils(False, False, False, False, False, False)

    def _get_coil(self, adresse: int) -> bool:
        valeur = self.db.get_coils(adresse, 1)
        return bool(valeur and valeur[0])

    def _get_reg(self, adresse: int, defaut: int) -> int:
        valeur = self.db.get_holding_registers(adresse, 1)
        if not valeur:
            return defaut
        return int(valeur[0])

    def _set_coils(self, remplissage: bool, embouteillage: bool, systeme: bool, p1: bool, p2: bool, p3: bool) -> None:
        self.db.set_coils(SUP_CYC_R, [remplissage])
        self.db.set_coils(SUP_CYC_V, [embouteillage])
        self.db.set_coils(SUP_CYC_M, [systeme])
        self.db.set_coils(SUP_CONV1, [p1])
        self.db.set_coils(SUP_CONV2, [p2])
        self.db.set_coils(SUP_CONV3, [p3])

    def demarrer(self) -> None:
        self.marche = True
        self.arret_urgence = False
        if self.phase == "ARRET":
            self.phase = "REMPLISSAGE"

    def arreter_urgence(self) -> None:
        self.marche = False
        self.arret_urgence = True
        self.phase = "ARRET_URGENCE"

    def reset_arret(self) -> None:
        self.arret_urgence = False
        self.phase = "ARRET"
        self.db.set_coils(FORC_ARR, [False])

    def lire_commandes(self) -> None:
        if self._get_coil(FORC_ARR):
            self.arreter_urgence()
            return
        if self.arret_urgence and not self._get_coil(FORC_ARR):
            self.reset_arret()
        if self._get_coil(FORC_MAR) and not self.arret_urgence:
            self.demarrer()

    def cycle(self, dt: float) -> None:
        self.lire_commandes()

        d1 = max(0, min(500, self._get_reg(DEBIT_1, 120)))
        d2 = max(0, min(500, self._get_reg(DEBIT_2, 120)))
        d3 = max(0, min(500, self._get_reg(DEBIT_3, 180)))

        if not self.marche or self.arret_urgence:
            self._set_coils(False, False, self.marche, False, False, False)
            self.db.set_holding_registers(SUP_NIV_C, [self.niveau])
            return

        if self.phase == "REMPLISSAGE":
            self.niveau += int((d1 + d2) * dt * 2.0)
            if self.niveau >= SEUIL_HAUT:
                self.niveau = SEUIL_HAUT
                self.phase = "EMBOUTEILLAGE"
            self._set_coils(True, False, True, True, True, False)
        elif self.phase == "EMBOUTEILLAGE":
            self.niveau -= int(d3 * dt * 2.4)
            if self.niveau <= SEUIL_BAS:
                self.niveau = SEUIL_BAS
                self.phase = "REMPLISSAGE"
            self._set_coils(False, True, True, False, False, True)
        else:
            self.phase = "REMPLISSAGE"

        self.niveau = max(NIVEAU_MIN, min(NIVEAU_MAX, self.niveau))
        self.db.set_holding_registers(SUP_NIV_C, [self.niveau])

    def afficher(self) -> None:
        print(
            f"\rServeur {HOST}:{PORT} | phase={self.phase:<14} "
            f"niveau={self.niveau:5d} | marche={self.marche} | urgence={self.arret_urgence}",
            end="",
            flush=True,
        )

    def run(self) -> None:
        self.server.start()
        print(f"Serveur Modbus TCP lance sur {HOST}:{PORT}")
        print("Ctrl+C pour quitter.")
        dernier = time.monotonic()
        try:
            while True:
                maintenant = time.monotonic()
                dt = maintenant - dernier
                dernier = maintenant
                self.cycle(dt)
                self.afficher()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nArret du simulateur.")
        finally:
            self.server.stop()


if __name__ == "__main__":
    AutomateJus().run()
