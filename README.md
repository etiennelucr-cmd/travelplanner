# Travel Planner V6.0 — Import corrigé (sans Tailscale)

Correctif pour l’erreur `Cannot read properties of undefined (reading toLowerCase)` lors de l’import.

- Prend en charge les lignes `Ville | Date | Statut` du fichier `villes_voyages(1).txt`, ainsi que le format Google Keep.
- Sépare noms, dates et statuts, notamment les dates en intervalle et les dates indicatives.
- Ignore les doublons de nom et date.
- Protège l’affichage contre les fiches sans nom.
- Reste accessible uniquement via `http://localhost:8787/` ; aucune fonction Tailscale.

## Installation sans perdre les voyages

1. Fermer le serveur actuel.
2. Décompresser cette archive dans un nouveau dossier.
3. Copier **depuis votre ancienne installation** `data/trips.json`, `data/records.json`, et `data/places-cache.json` si présent. Ne pas copier les fichiers de catalogue par-dessus les nouveaux.
4. Démarrer `Lancer-TravelPlanner-V5.9.bat`, puis actualiser avec Ctrl+F5.
5. Dans Mes destinations, cliquer « Importer liste Voyages (.txt) » et sélectionner votre fichier. Vérifier le nombre de nouveaux voyages avant confirmation.

**Attention** : l’import ajoute les voyages manquants ; il ne remplace pas ni ne corrige automatiquement les fiches existantes. Il est prudent de sauvegarder le dossier `data` avant import.
