# Travel Planner V6.1 — Streamlit

## Lancement local
`pip install -r requirements.txt` puis `streamlit run app.py`.

## Publication
1. Créer un dépôt GitHub privé et y déposer les fichiers de ce dossier (attention : `data/trips.json` contient vos informations personnelles).
2. Dans Streamlit Community Cloud, choisir **Create app**, le dépôt, la branche et `app.py`.
3. Déployer puis ouvrir le lien fourni par Streamlit.

## Données
118 voyages de l’archive sont inclus. **Les modifications dans l'application ne sont pas persistantes** sur Streamlit Cloud : utilisez le bouton de sauvegarde JSON et restaurez votre fichier à la prochaine session. Pour une sauvegarde automatique multi-appareils, il faudra ajouter une base de données persistante et une authentification.

## Portée
Cette version est une adaptation fonctionnelle simplifiée, **pas une reproduction exacte** de l'interface JavaScript originale. Les fonctions météo, itinéraires et géocodage en ligne ne sont pas migrées. La carte utilise les coordonnées de centres-villes fournies par le correctif V6.1.
