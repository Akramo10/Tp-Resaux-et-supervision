# Supervision graphique d'une unité de production de jus

## Prérequis

Python 3 est requis.

Installer les dépendances :

```bash
pip install pyModbusTCP pygame
```

## Alertes par e-mail avec Resend

Les alarmes peuvent être envoyées par e-mail via l'API Resend.

Avant de lancer la supervision, configurer les variables d'environnement :

```powershell
$env:RESEND_API_KEY="votre_cle_resend"
$env:ALERTE_EMAIL_DEST="akram.Alerte@telxia.fr"
```

Variable optionnelle :

```powershell
$env:ALERTE_EMAIL_FROM="Supervision Jus <Akram.Alerte@telxia.fr>"
```

> Remarque : pour utiliser un domaine vérifié avec Resend, remplacer `ALERTE_EMAIL_FROM` par une adresse appartenant au domaine autorisé.

Dans l'interface graphique, le champ **Email réception** permet de modifier l'adresse de destination pendant l'exécution.

Le bouton **Email test** permet d'envoyer un message de test à l'adresse saisie.

## Ordre de lancement

1. Lancer le simulateur fourni par l'enseignant :

```bash
python automate_jus_visuel.py
```

2. Lancer une supervision :

```bash
python supervision_terminal.py
```

ou :

```bash
python supervision_graphique.py
```

## Structure du projet

```text
supervision_graphique.py : point d'entrée de l'interface graphique pygame
supervision_terminal.py  : supervision en console
src/modbus_service.py    : communication Modbus TCP centralisée
src/etat_procede.py      : lecture des données, dataclass EtatProcede,
                           détermination de la phase et validation des débits
src/alarm_manager.py     : gestion des alarmes instantanées et du niveau bloqué
src/historique_csv.py    : écriture non bloquante du fichier historique.csv
src/gui_pygame.py        : dessin et interactions de l'interface pygame
README.txt               : documentation du projet
plan_tests.txt           : plan de test
```

## Commandes disponibles

### Mode terminal

| Commande | Action |
|---|---|
| `1` | Démarrer |
| `2` | Arrêt d'urgence |
| `3` | Réinitialiser l'arrêt |
| `4` | Modifier le débit 1 |
| `5` | Modifier le débit 2 |
| `6` | Modifier le débit 3 |
| `q` | Quitter |

### Mode graphique

- **Démarrer**
- **Arrêt urgence**
- **Reset arrêt**
- **Débit 1 + / -**
- **Débit 2 + / -**
- **Débit 3 + / -**
- **Quitter**
<img width="1174" height="790" alt="image" src="https://github.com/user-attachments/assets/0724491d-25fa-4977-b77a-150096792171" />

## Fonctionnalités réalisées

- Client Modbus TCP connecté à `127.0.0.1:9502`.
- Déclaration des adresses Modbus sous forme de constantes.
- Centralisation de la communication dans `ModbusService`.
- Lecture structurée des données dans `EtatProcede`.
- Détermination automatique de la phase du procédé.
- Validation des débits entre `0` et `500`.
- Gestion des alarmes :
  - perte de communication ;
  - incohérence des données ;
  - niveau anormal ;
  - débit incorrect ;
  - défaut pompe ;
  - niveau bloqué.
- Génération automatique d'un historique CSV avec une ligne par seconde.
- Supervision indépendante en mode terminal.
- Interface graphique pygame avec :
  - réservoirs ;
  - cuve ;
  - pompes ;
  - jauge ;
  - ligne de production ;
  - affichage des alarmes.
- Gestion de la perte de communication sans fermeture de l'application.
- Envoi non bloquant des nouvelles alarmes par e-mail via Resend, si les variables d'environnement sont configurées.

## Fonctionnalité non réalisée

- La saisie clavier directe des débits dans l'interface graphique n'a pas été implémentée.  
  L'interface utilise des boutons `+ / -` avec un pas de `10`, conformément à la demande.

## Limites connues

- La phase `ARRET_URGENCE` est déduite à partir des coils disponibles, car aucun coil spécifique d'arrêt d'urgence n'est fourni en lecture.
- Si le simulateur utilise une logique différente pour acquitter l'arrêt d'urgence, le bouton **Reset arrêt** peut nécessiter une adaptation.
- L'alarme de niveau bloqué repose sur une variation minimale de `20` points pendant `5` secondes.
