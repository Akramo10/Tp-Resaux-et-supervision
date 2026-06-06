Supervision graphique d'une unite de production de jus
======================================================

Bibliotheques necessaires
-------------------------
Python 3 est requis.

Installer les dependances :
pip install pyModbusTCP pygame

Alertes mail Resend
-------------------
Les alarmes peuvent etre envoyees par email avec l'API Resend.
Configurer les variables d'environnement avant de lancer la supervision :

$env:RESEND_API_KEY="votre_cle_resend"
$env:ALERTE_EMAIL_DEST="akram.Alerte@telxia.fr"

Optionnel :
$env:ALERTE_EMAIL_FROM="Supervision Jus <Akram.Alerte@telxia.fr>"

Remarque : pour un domaine Resend verifie, remplacer ALERTE_EMAIL_FROM par une adresse du domaine autorise.
Dans l'interface graphique, le champ "Email reception" permet de modifier l'adresse de destination pendant l'execution.
Le bouton "Email test" envoie un message de test a l'adresse saisie.

Ordre de lancement
------------------
1. Lancer le simulateur fourni par l'enseignant :
   python automate_jus_visuel.py

2. Lancer une supervision :
   python supervision_terminal.py
   ou
   python supervision_graphique.py

Structure du projet
-------------------
supervision_graphique.py : point d'entree de l'interface pygame
supervision_terminal.py  : supervision en console
src/modbus_service.py    : communication Modbus TCP centralisee
src/etat_procede.py      : lecture, dataclass EtatProcede, phase et validation debit
src/alarm_manager.py     : alarmes instantanees et niveau bloque
src/historique_csv.py    : ecriture non bloquante de historique.csv
src/gui_pygame.py        : dessin et interactions pygame
README.txt               : ce fichier
plan_tests.txt           : plan de test

Commandes disponibles
---------------------
Terminal :
1 demarrer
2 arret urgence
3 reset arret
4 modifier debit 1
5 modifier debit 2
6 modifier debit 3
q quitter

Graphique :
Boutons Demarrer, Arret urgence, Reset arret, Debit 1 +/-, Debit 2 +/-, Debit 3 +/-, Quitter.

Fonctionnalites realisees
-------------------------
- Client Modbus TCP sur 127.0.0.1:9502.
- Adresses Modbus declarees en constantes.
- Communication centralisee dans ModbusService.
- Lecture structuree dans EtatProcede.
- Determination automatique de phase.
- Validation des debits entre 0 et 500.
- Alarmes de communication, incoherence, niveau, debit, pompes et niveau bloque.
- Historique CSV genere automatiquement avec une ligne par seconde.
- Interface terminale independante.
- Interface pygame avec reservoirs, cuve, pompes, jauge, ligne et alarmes.
- Gestion de perte de communication sans fermeture de l'application.
- Envoi non bloquant des nouvelles alarmes par email via Resend si les variables d'environnement sont configurees.

Fonctionnalites non realisees
-----------------------------
- Saisie clavier directe des debits dans l'interface graphique. Le GUI utilise des boutons +/- par pas de 10, comme demande.

Limites connues
---------------
- La phase ARRET_URGENCE est deduite des coils disponibles, car aucun coil specifique d'arret d'urgence n'est fourni en lecture.
- Si le simulateur utilise une logique differente pour acquitter l'arret d'urgence, le bouton Reset arret peut devoir etre adapte.
- L'alarme de niveau bloque utilise une variation minimale de 20 points pendant 5 secondes.
