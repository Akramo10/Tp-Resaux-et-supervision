"""Interface graphique pygame pour la supervision du procede."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

from .alarm_manager import AlarmManager
from .email_alerts import EmailAlertService
from .etat_procede import EtatProcede, lire_etat, valider_debit
from .historique_csv import HistoriqueCSV
from .modbus_service import (
    COIL_FORC_ARR,
    COIL_FORC_MAR,
    REG_DEBIT_1,
    REG_DEBIT_2,
    REG_DEBIT_3,
    ModbusService,
)


LARGEUR = 1180
HAUTEUR = 760
FPS = 30

BLANC = (245, 247, 250)
NOIR = (20, 23, 28)
GRIS = (110, 119, 132)
GRIS_CLAIR = (225, 231, 238)
FOND = (236, 240, 244)
VERT = (32, 155, 89)
ROUGE = (210, 58, 55)
ORANGE = (240, 152, 38)
JAUNE = (244, 202, 71)
BLEU = (55, 128, 190)
BLEU_CLAIR = (120, 185, 220)


@dataclass
class Button:
    rect: pygame.Rect
    texte: str
    action: str

    def draw(self, surface, font, enabled: bool = True) -> None:
        couleur = (44, 92, 150) if enabled else (150, 158, 168)
        pygame.draw.rect(surface, couleur, self.rect, border_radius=6)
        pygame.draw.rect(surface, (22, 52, 92), self.rect, 2, border_radius=6)
        txt = font.render(self.texte, True, BLANC)
        surface.blit(txt, txt.get_rect(center=self.rect.center))


@dataclass
class TextInput:
    rect: pygame.Rect
    texte: str = ""
    actif: bool = False

    def handle_event(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.actif = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.actif:
            if event.key == pygame.K_BACKSPACE:
                self.texte = self.texte[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.actif = False
            elif len(self.texte) < 80 and event.unicode and event.unicode.isprintable():
                self.texte += event.unicode

    def draw(self, surface, font) -> None:
        bord = BLEU if self.actif else GRIS_CLAIR
        pygame.draw.rect(surface, BLANC, self.rect, border_radius=5)
        pygame.draw.rect(surface, bord, self.rect, 2, border_radius=5)
        affichage = self.texte[-34:] if self.texte else "adresse@email.fr"
        couleur = NOIR if self.texte else GRIS
        surface.blit(font.render(affichage, True, couleur), (self.rect.x + 8, self.rect.y + 8))


def texte(surface, font, contenu, x, y, couleur=NOIR) -> None:
    surface.blit(font.render(str(contenu), True, couleur), (x, y))


def dessiner_reservoir(surface, font, x, y, nom, couleur) -> None:
    rect = pygame.Rect(x, y, 130, 170)
    pygame.draw.rect(surface, (232, 236, 240), rect, border_radius=8)
    pygame.draw.rect(surface, GRIS, rect, 3, border_radius=8)
    liquide = pygame.Rect(x + 12, y + 60, 106, 96)
    pygame.draw.rect(surface, couleur, liquide, border_radius=5)
    texte(surface, font, nom, x + 18, y + 18)


def dessiner_pompe(surface, font, x, y, nom, active) -> None:
    couleur = VERT if active else GRIS
    pygame.draw.circle(surface, couleur, (x, y), 32)
    pygame.draw.circle(surface, NOIR, (x, y), 32, 2)
    texte(surface, font, nom, x - 16, y - 10, BLANC)
    texte(surface, font, "ON" if active else "OFF", x - 20, y + 42, couleur)


def dessiner_cuve(surface, font, etat: EtatProcede) -> None:
    x, y, w, h = 470, 180, 190, 360
    pygame.draw.rect(surface, (232, 236, 240), (x, y, w, h), border_radius=10)
    pygame.draw.rect(surface, NOIR, (x, y, w, h), 3, border_radius=10)
    pct = max(0.0, min(100.0, etat.niveau_pct or 0.0))
    niveau_h = int((h - 24) * pct / 100)
    pygame.draw.rect(surface, BLEU_CLAIR, (x + 12, y + h - 12 - niveau_h, w - 24, niveau_h), border_radius=6)
    texte(surface, font, "Cuve melange", x + 34, y + 18)
    texte(surface, font, f"{pct:.1f}%", x + 70, y + h // 2)


def dessiner_lignes(surface) -> None:
    pygame.draw.line(surface, GRIS, (250, 265), (360, 265), 8)
    pygame.draw.line(surface, GRIS, (250, 405), (360, 405), 8)
    pygame.draw.line(surface, GRIS, (392, 265), (470, 300), 8)
    pygame.draw.line(surface, GRIS, (392, 405), (470, 420), 8)
    pygame.draw.line(surface, GRIS, (660, 365), (780, 365), 8)
    pygame.draw.line(surface, GRIS, (845, 365), (1010, 365), 8)
    pygame.draw.rect(surface, (205, 211, 218), (860, 410, 220, 30), border_radius=4)
    for bx in range(875, 1060, 45):
        pygame.draw.rect(surface, (150, 75, 58), (bx, 380, 24, 48), border_radius=4)


def creer_boutons() -> list[Button]:
    labels = [
        ("Demarrer", "start"),
        ("Arret urgence", "stop"),
        ("Reset arret", "reset"),
        ("Debit 1 +", "d1+"),
        ("Debit 1 -", "d1-"),
        ("Debit 2 +", "d2+"),
        ("Debit 2 -", "d2-"),
        ("Debit 3 +", "d3+"),
        ("Debit 3 -", "d3-"),
        ("Email test", "email_test"),
        ("Quitter", "quit"),
    ]
    boutons: list[Button] = []
    x, y = 30, 585
    for i, (label, action) in enumerate(labels):
        rect = pygame.Rect(x + (i % 6) * 128, y + (i // 6) * 48, 118, 38)
        boutons.append(Button(rect, label, action))
    return boutons


def appliquer_action(
    service: ModbusService,
    alarmes: AlarmManager,
    emails: EmailAlertService,
    email_input: TextInput,
    action: str,
    etat: EtatProcede,
) -> bool:
    if action == "quit":
        return False
    if action == "email_test":
        emails.definir_destinataire(email_input.texte)
        ok, message = emails.envoyer_test()
        if ok:
            alarmes.acquitter_valeur_refusee()
        else:
            alarmes.signaler_valeur_refusee(message)
        return True
    if not etat.communication_ok:
        return True
    if action == "start":
        service.ecrire_bit(COIL_FORC_MAR, True)
    elif action == "stop":
        service.ecrire_bit(COIL_FORC_ARR, True)
    elif action == "reset":
        service.ecrire_bit(COIL_FORC_ARR, False)
    elif action in {"d1+", "d1-", "d2+", "d2-", "d3+", "d3-"}:
        registre = {"d1": REG_DEBIT_1, "d2": REG_DEBIT_2, "d3": REG_DEBIT_3}[action[:2]]
        courant = {"d1": etat.debit_1, "d2": etat.debit_2, "d3": etat.debit_3}[action[:2]]
        delta = 10 if action.endswith("+") else -10
        ok, debit, message = valider_debit((courant or 0) + delta)
        if ok and debit is not None:
            alarmes.acquitter_valeur_refusee()
            service.ecrire_registre(registre, debit)
        else:
            alarmes.signaler_valeur_refusee(message)
    return True


def dessiner_interface(
    surface,
    fonts,
    etat: EtatProcede,
    boutons: list[Button],
    email_input: TextInput,
    emails: EmailAlertService,
) -> None:
    font, grand, petit = fonts
    surface.fill(FOND)
    texte(surface, grand, "Supervision graphique - Production de jus", 30, 24)

    comm_couleur = VERT if etat.communication_ok else ROUGE
    pygame.draw.circle(surface, comm_couleur, (36, 86), 10)
    texte(surface, font, "Communication OK" if etat.communication_ok else "Communication perdue", 54, 76, comm_couleur)
    texte(surface, font, "Phase: " + etat.phase, 310, 76, BLEU if etat.communication_ok else ROUGE)

    dessiner_lignes(surface)
    dessiner_reservoir(surface, font, 90, 170, "Orange", ORANGE)
    dessiner_reservoir(surface, font, 90, 345, "Pomme", JAUNE)
    dessiner_pompe(surface, font, 380, 265, "P1", etat.p1)
    dessiner_pompe(surface, font, 380, 405, "P2", etat.p2)
    dessiner_cuve(surface, font, etat)
    dessiner_pompe(surface, font, 812, 365, "P3", etat.p3)
    texte(surface, font, "Ligne embouteillage", 880, 450)

    pygame.draw.rect(surface, BLANC, (820, 115, 320, 185), border_radius=8)
    pygame.draw.rect(surface, GRIS_CLAIR, (820, 115, 320, 185), 2, border_radius=8)
    texte(surface, font, "Variables Modbus", 840, 135)
    texte(surface, petit, f"Niveau brut: {etat.niveau if etat.niveau is not None else '?'}", 840, 170)
    texte(surface, petit, f"Debit 1: {etat.debit_1 if etat.debit_1 is not None else '?'}", 840, 198)
    texte(surface, petit, f"Debit 2: {etat.debit_2 if etat.debit_2 is not None else '?'}", 840, 226)
    texte(surface, petit, f"Debit 3: {etat.debit_3 if etat.debit_3 is not None else '?'}", 840, 254)

    pygame.draw.rect(surface, BLANC, (820, 500, 320, 190), border_radius=8)
    pygame.draw.rect(surface, ROUGE if etat.alarmes else GRIS_CLAIR, (820, 500, 320, 190), 2, border_radius=8)
    texte(surface, font, "Alarmes", 840, 520, ROUGE if etat.alarmes else VERT)
    if etat.alarmes:
        for i, alarme in enumerate(etat.alarmes[:5]):
            texte(surface, petit, "- " + alarme[:38], 840, 555 + i * 24, ROUGE)
    else:
        texte(surface, petit, "Aucune alarme active", 840, 555, VERT)

    texte(surface, petit, "Email reception", 30, 708)
    email_input.draw(surface, petit)
    statut_email = "Resend OK" if emails.config.api_key else "Cle Resend absente"
    texte(surface, petit, statut_email, 455, 710, VERT if emails.config.api_key else ROUGE)

    enabled = etat.communication_ok
    for bouton in boutons:
        bouton.draw(surface, petit, enabled or bouton.action in {"quit", "email_test"})


def main() -> int:
    if pygame is None:
        print("pygame est introuvable. Installez-le avec: pip install pygame")
        return 1

    pygame.init()
    surface = pygame.display.set_mode((LARGEUR, HAUTEUR))
    pygame.display.set_caption("Supervision graphique - Production de jus")
    clock = pygame.time.Clock()
    fonts = (
        pygame.font.SysFont("arial", 20),
        pygame.font.SysFont("arial", 30, bold=True),
        pygame.font.SysFont("arial", 17),
    )
    boutons = creer_boutons()
    service = ModbusService()
    alarmes = AlarmManager()
    emails = EmailAlertService()
    email_input = TextInput(pygame.Rect(150, 700, 290, 36), emails.config.destinataire)
    historique = HistoriqueCSV()
    etat = EtatProcede()
    dernier_poll = 0.0
    dernier_csv = 0.0
    running = True

    try:
        while running:
            for event in pygame.event.get():
                email_input.handle_event(event)
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for bouton in boutons:
                        if bouton.rect.collidepoint(event.pos):
                            running = appliquer_action(service, alarmes, emails, email_input, bouton.action, etat)

            maintenant = time.monotonic()
            if maintenant - dernier_poll >= 0.25:
                etat = lire_etat(service)
                alarmes.verifier_alarmes(etat)
                emails.definir_destinataire(email_input.texte)
                emails.notifier_si_nouvelles(etat)
                dernier_poll = maintenant
            if maintenant - dernier_csv >= 1.0:
                historique.enregistrer(etat)
                dernier_csv = maintenant

            dessiner_interface(surface, fonts, etat, boutons, email_input, emails)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        emails.fermer()
        historique.fermer()
        service.fermer()
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
