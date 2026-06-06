"""Service unique d'acces au serveur Modbus TCP."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from pyModbusTCP.client import ModbusClient
except ImportError:  # pragma: no cover - message utile au lancement
    ModbusClient = None


HOST = "127.0.0.1"
PORT = 9502
UNIT_ID = 1
TIMEOUT = 1.5


COIL_FORC_MAR = 201
COIL_FORC_ARR = 202
COIL_SUP_CYC_R = 300
COIL_SUP_CYC_V = 301
COIL_SUP_CYC_M = 302
COIL_SUP_CONV1 = 303
COIL_SUP_CONV2 = 304
COIL_SUP_CONV3 = 305

REG_DEBIT_1 = 11
REG_DEBIT_2 = 12
REG_DEBIT_3 = 13
REG_SUP_NIV_C = 30


@dataclass(frozen=True)
class ModbusAddresses:
    forc_mar: int = COIL_FORC_MAR
    forc_arr: int = COIL_FORC_ARR
    sup_cyc_r: int = COIL_SUP_CYC_R
    sup_cyc_v: int = COIL_SUP_CYC_V
    sup_cyc_m: int = COIL_SUP_CYC_M
    sup_conv1: int = COIL_SUP_CONV1
    sup_conv2: int = COIL_SUP_CONV2
    sup_conv3: int = COIL_SUP_CONV3
    debit_1: int = REG_DEBIT_1
    debit_2: int = REG_DEBIT_2
    debit_3: int = REG_DEBIT_3
    niveau: int = REG_SUP_NIV_C


class ModbusService:
    """Isole tous les appels pyModbusTCP du reste de l'application."""

    def __init__(
        self,
        host: str = HOST,
        port: int = PORT,
        unit_id: int = UNIT_ID,
        timeout: float = TIMEOUT,
    ) -> None:
        if ModbusClient is None:
            raise RuntimeError(
                "pyModbusTCP est introuvable. Installez-le avec: pip install pyModbusTCP"
            )
        self.client = ModbusClient(
            host=host,
            port=port,
            unit_id=unit_id,
            auto_open=True,
            auto_close=False,
            timeout=timeout,
        )
        self.communication_ok = False

    def connecter(self) -> bool:
        try:
            self.communication_ok = bool(self.client.open())
        except Exception:
            self.communication_ok = False
        return self.communication_ok

    def fermer(self) -> None:
        try:
            self.client.close()
        finally:
            self.communication_ok = False

    def lire_bit(self, adresse: int) -> bool | None:
        try:
            valeurs = self.client.read_coils(adresse, 1)
            if valeurs is None:
                self.communication_ok = False
                return None
            self.communication_ok = True
            return bool(valeurs[0])
        except Exception:
            self.communication_ok = False
            return None

    def lire_registre(self, adresse: int) -> int | None:
        try:
            valeurs = self.client.read_holding_registers(adresse, 1)
            if valeurs is None:
                self.communication_ok = False
                return None
            self.communication_ok = True
            return int(valeurs[0])
        except Exception:
            self.communication_ok = False
            return None

    def ecrire_bit(self, adresse: int, valeur: bool) -> bool:
        if not self.communication_ok:
            self.connecter()
        if not self.communication_ok:
            return False
        try:
            ok = bool(self.client.write_single_coil(adresse, bool(valeur)))
            self.communication_ok = ok
            return ok
        except Exception:
            self.communication_ok = False
            return False

    def ecrire_registre(self, adresse: int, valeur: int) -> bool:
        if not self.communication_ok:
            self.connecter()
        if not self.communication_ok:
            return False
        try:
            ok = bool(self.client.write_single_register(adresse, int(valeur)))
            self.communication_ok = ok
            return ok
        except Exception:
            self.communication_ok = False
            return False
