# Fractales du Destin — Jeu interactif 

Application locale, **distincte du skill** (`fractales-du-destin/references/` reste le domaine du skill Claude).
Implémente le **pipeline trans-échelle complet en 6 étapes** : l'application est l'orchestrateur
(« corps calleux logiciel ») — chaque registre est un organe distinct, appelé en séquence,
et chaque sortie est marquée de son régime épistémologique. Les registres ne sont jamais fusionnés.

## Fournisseur d'IA : n'importe quelle API compatible OpenAI

L'application ne dépend **d'aucun fournisseur en particulier**. Elle parle le standard
`POST /chat/completions` (format OpenAI) avec authentification `Authorization: Bearer <clé>`,
et liste les modèles via `GET /models`. Tout service exposant ce standard fonctionne sans
toucher au code : seul le fichier `.env` change.

> Note de compatibilité : les variables gardent le préfixe `FANTASY_` (nom du premier
> fournisseur utilisé) pour ne pas casser les configurations existantes. Leur contenu
> peut pointer vers n'importe quel service.

### Configurations standard

| Fournisseur | FANTASY_BASE_URL | Exemple de FANTASY_MODEL | Remarques |
|---|---|---|---|
| **OpenRouter** | `https://openrouter.ai/api/v1` | `anthropic/claude-sonnet-4` | Agrégateur multi-modèles, remplaçant naturel de Fantasy |
| **Mistral** | `https://api.mistral.ai/v1` | `mistral-large-latest` | Fournisseur direct, européen |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | Très rapide, offre gratuite limitée |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o` | Fournisseur direct |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` | Fournisseur direct |
| **Ollama (local)** | `http://localhost:11434/v1` | `llama3.1` | 100 % local, aucune clé requise (mettre une valeur factice) |
| **LM Studio (local)** | `http://localhost:1234/v1` | nom du modèle chargé | 100 % local, idem |
| Fantasy AI | `https://www.fantasyai.cloud/api/v1` | selon catalogue | Configuration d'origine |

Vérifier les URL et noms de modèles dans la documentation du fournisseur choisi —
les catalogues évoluent. L'API native d'Anthropic (`/v1/messages`) n'est **pas** au
format OpenAI : pour utiliser les modèles Claude, passer par un agrégateur compatible
(OpenRouter) ou tout service exposant Claude derrière `/chat/completions`.

### Migration depuis Fantasy en 30 secondes

1. Ouvrir `.env`
2. Remplacer `FANTASY_BASE_URL` par l'URL du nouveau fournisseur (tableau ci-dessus)
3. Remplacer `FANTASY_API_KEY` par la clé du nouveau fournisseur
4. Relancer `python app.py`, cliquer « ↻ Modèles disponibles », choisir, enregistrer

Aucune autre modification. Les réessais automatiques, la bascule de secours
(`FANTASY_MODELES_SECOURS`) et le sélecteur de modèles fonctionnent à l'identique
chez tout fournisseur conforme au standard.

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env        # puis renseigner clé + base URL du fournisseur choisi
python app.py               # http://127.0.0.1:5173
```

Sans clé valide, mode dégradé : tirage et journaux actifs, lectures indisponibles.

### Variables d'environnement (`.env`)

```bash
FANTASY_API_KEY=...                                  # clé du fournisseur choisi
FANTASY_BASE_URL=https://openrouter.ai/api/v1        # endpoint compatible OpenAI
FANTASY_MODEL=anthropic/claude-sonnet-4              # modèle principal
FANTASY_MODELES_SECOURS=mistral-large-latest,gpt-4o  # bascule auto si le principal échoue
```

## Le pipeline

| # | Étape | Organe (skill source) | Route | Registre |
|---|-------|----------------------|-------|----------|
| 1 | Tirage | moteur local (RNG cryptographique, cycle-5) | `POST /api/tirage` | — |
| 2 | Lecture symbolique | iris-oracle / fractales-du-destin | `POST /api/lecture` | SYMBOLIQUE |
| 3 | Lecture structurelle | NEXUS-ARCHÊ v0.3 (16 cartes, test d'ancrage observable) | `POST /api/structurelle` | STRUCTUREL |
| 4 | Lecture analytique | Superforecasting Protocol (GJP 7 étapes) | `POST /api/analytique` | ANALYTIQUE |
| 5 | Carte de résonance | Miroir Trans-Échelle (passe 3) | `POST /api/resonance` | SYNTHÉTIQUE |
| 6 | Logs | journal deck + log de prédictions scorable | `POST /api/log`, `POST /api/prediction-log` | — |

Garde-fous épistémiques câblés : la résonance **exige** les lectures symbolique ET analytique
(les registres ne dialoguent que s'ils existent tous les deux) ; l'analytique **exige** une
question formulée (le registre falsifiable ne travaille pas sur un tirage nu) ; l'analytique
n'a accès à aucune carte ni symbole.

## Robustesse aux pannes de fournisseur

- **Réessais automatiques** : 3 tentatives par modèle (délais 0 / 2 / 5 s) sur les
  erreurs transitoires 429, 502, 503.
- **Chaîne de secours** : si le modèle principal échoue trois fois, bascule sur
  `FANTASY_MODELES_SECOURS` dans l'ordre.
- **Diagnostic guidé** : en cas d'échec total, le message d'erreur indique la marche
  à suivre (recharger la liste des modèles, configurer la chaîne de secours).

## Structure

```
fractales-app/
├── app.py                    # orchestrateur Flask (4 organes + 2 logs)
├── data/
│   ├── cartes.json           # deck v2 (84 cartes, 10 familles) — source de vérité
│   └── cartes.schema.json    # invariants structurels (validation jsonschema)
├── templates/index.html      # interface (cercle à centre vide, panneaux par registre)
├── logs/
│   ├── tirages.jsonl         # journal de validation du deck (généré)
│   └── predictions.jsonl     # log de prédictions scorable (généré)
└── .env                      # clé + endpoint du fournisseur (jamais commité, jamais côté client)
```

## Les deux journaux (futur IRIS-Memory)

**`logs/tirages.jsonl`** — validation empirique du deck v2 : `dimension_non_couverte`,
`carte_forcee`, `nouvelles_cartes_activees` (détection automatique), `pertinence_ressentie`.
Critères de révision : `refonte-v2-arcanes.md` §8.

**`logs/predictions.jsonl`** — format calibration-engine : chaque fiche analytique consignée
porte `question_predictive`, `probabilite`, `horizon_date`, `scenarios` (MECE, somme 100 %),
`indicateurs_bascule`, `condition_refutation`, `statut: ouverte`, et les champs de scoring
(`resolution`, `date_resolution`, `brier_score`, `revisions`) à renseigner à l'échéance.
`GET /api/predictions` expose le log pour le scoring rétrospectif.
