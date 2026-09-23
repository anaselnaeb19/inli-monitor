# inli-monitor

Surveille les nouvelles annonces de location sur [inli.fr](https://www.inli.fr) pour les 8 departements
d'Ile-de-France (75, 77, 78, 91, 92, 93, 94, 95) et envoie une notification Telegram des qu'une nouvelle
annonce apparait. Tourne automatiquement toutes les heures via GitHub Actions, sans avoir besoin de laisser
un PC allume.

## Comment ca marche

- `monitor.py` recupere la page de resultats de chaque departement, extrait chaque annonce (reference,
  ville, prix, pieces, surface, lien) et compare avec la liste enregistree lors de l'execution precedente
  (`state.json`).
- Les references jamais vues declenchent un message Telegram.
- `state.json` est mis a jour et re-commite dans le repo a chaque execution (c'est ce qui permet de
  "se souvenir" d'une execution a l'autre sur GitHub Actions, qui ne garde rien entre deux runs).
- Le premier lancement n'envoie aucune notification (il sert juste a enregistrer l'etat de depart) : sinon
  toutes les annonces deja en ligne seraient notifiees comme "nouvelles".

## Mise en place (une seule fois)

### 1. Creer le bot Telegram

1. Dans Telegram, ouvrez une conversation avec **@BotFather**.
2. Envoyez `/newbot`, suivez les instructions (nom, puis identifiant se terminant par `bot`).
3. BotFather vous donne un **token** du type `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`. Gardez-le.
4. Envoyez n'importe quel message a votre nouveau bot (obligatoire pour qu'il puisse ensuite vous ecrire).
5. Recuperez votre **chat_id** : ouvrez dans un navigateur, en remplacant `<TOKEN>` par votre token :
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   Cherchez `"chat":{"id":123456789,...}` dans la reponse JSON : c'est votre `chat_id`.

### 2. Creer le depot GitHub

1. Sur [github.com](https://github.com), creez un nouveau depot (public ou prive, peu importe), par exemple
   `inli-monitor`. Ne cochez aucune option d'initialisation (pas de README/gitignore, ce dossier en a deja).
2. Depuis ce dossier `inli-monitor/`, executez :

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<votre-utilisateur>/inli-monitor.git
   git push -u origin main
   ```

### 3. Ajouter les secrets GitHub

Dans le depot GitHub : **Settings > Secrets and variables > Actions > New repository secret**, ajoutez :

- `TELEGRAM_BOT_TOKEN` = le token recupere aupres de BotFather
- `TELEGRAM_CHAT_ID` = votre chat_id

### 4. Verifier que les Actions sont actives

Onglet **Actions** du depot GitHub > si demande, cliquez sur "I understand my workflows, go ahead and
enable them". Le workflow `Surveillance inli.fr` tourne ensuite automatiquement toutes les heures
(cron `5 * * * *`).

Vous pouvez aussi le lancer manuellement pour tester tout de suite : onglet **Actions** >
"Surveillance inli.fr" > **Run workflow**.

## Modifier les zones surveillees

La liste des departements est dans `monitor.py`, dictionnaire `DEPARTMENTS` (code -> nom, slug d'URL).
Ajoutez/retirez une ligne pour changer la zone couverte. Pour retrouver le slug exact d'un departement,
ouvrez sa page de recherche sur inli.fr et copiez la fin de l'URL (apres `/locations/offres/`).

## Tester en local (optionnel)

```bash
pip install -r requirements.txt
set TELEGRAM_BOT_TOKEN=votre_token
set TELEGRAM_CHAT_ID=votre_chat_id
python monitor.py
```

(Sous PowerShell : `$env:TELEGRAM_BOT_TOKEN="votre_token"` etc.)
