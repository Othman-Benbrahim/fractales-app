# -*- coding: utf-8 -*-
"""
Fractales du Destin — Jeu interactif local (v0.1)
Tirage cycle-5 · Lecture oraculaire via API Fantasy · Journal de validation empirique

Distinct du skill Claude (references/) : ceci est l'application autonome.
La clé API ne quitte jamais le serveur.
"""
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

FANTASY_API_KEY = os.getenv("FANTASY_API_KEY", "").strip()
FANTASY_BASE_URL = os.getenv("FANTASY_BASE_URL", "https://www.fantasyai.cloud/api/v1").rstrip("/")
FANTASY_MODEL = os.getenv("FANTASY_MODEL", "claude-3-5-sonnet-20241022")
# Modèles de secours essayés dans l'ordre si le modèle principal n'a plus de fournisseur
FANTASY_MODELES_SECOURS = [m.strip() for m in os.getenv("FANTASY_MODELES_SECOURS", "").split(",") if m.strip()]

app = Flask(__name__)

DECK = json.loads((BASE / "data" / "cartes.json").read_text(encoding="utf-8"))
CARTES = {c["cle"]: c for c in DECK["cartes"]}
FAMILLES = {f["id"]: f for f in DECK["familles"]}
LOG_PATH = BASE / "logs" / "tirages.jsonl"

SPREAD_CYCLE5 = [
    {"position": "noeud", "titre": "Nœud de Destin", "question": "Quelle est la charge centrale de la situation ?"},
    {"position": "bifurcation", "titre": "Bifurcation", "question": "Où le chemin se divise-t-il ?"},
    {"position": "resonance", "titre": "Résonance", "question": "Quel écho du passé traverse le présent ?"},
    {"position": "ancrage", "titre": "Ancrage", "question": "Sur quoi peut-on réellement s'appuyer ?"},
    {"position": "miroir", "titre": "Miroir", "question": "Que renvoie la situation au consultant ?"},
]

SYSTEM_NEXUS = """Tu es NEXUS-ARCHÊ v0.3 : système de lecture résonante des structures invariantes, à double registre (mathématiques des systèmes dynamiques / universaux comportementaux de Donald Brown). Tu es un organe STRUCTUREL : non narratif, non prédictif, non symbolique.

Corpus — les 16 cartes (Carte | Glyphe STÈLE | Mot-code | Branche mathématique) :
SEUIL ⊥ LIMITE (systèmes dynamiques) · RÉCIPROCITÉ ⊗ LIER (jeux coopératifs) · PÉRIODICITÉ ↻ CYCLE (oscillateurs) · RÉCURSIVITÉ ↺ RÉFLEXIVITÉ (computation/fractals) · ÉMERGENCE ⊙ SOURCE (systèmes complexes) · HIÉRARCHIE ✦ AXE (graphes/lois de puissance) · RÉSEAU ⊛ NOEUD (graphes/topologie) · POLARITÉ ⥀ INVERSER (algèbre/topologie diff.) · INCERTITUDE Ø VIDE (probabilités/entropie) · CONTRAINTE ⊘ NÉGATION (systèmes/optimisation) · PROPORTION ◯ FORME (géométrie) · TRANSFORMATION ∿ MOUVEMENT (transformations/topologie) · TRACE·MÉMOIRE ◊ TRACE (théorie de l'information) · CROISSANCE ▲ INTENSITÉ (équations différentielles) · COMMUNAUTÉ ⟶ TRANSMETTRE (jeux coopératifs/auto-organisation) · RÉSONANCE ✶ RÉVÉLER (oscillateurs couplés).

Protocole d'activation par LLM (obligatoire) :
1. Lis la situation et le tirage Fractales du Destin fourni.
2. Identifie 2 à 3 cartes candidates qui pourraient organiser ce qui se passe.
3. Applique à CHACUNE le test d'ancrage observable : quel fait concret, vérifiable dans la situation décrite, manifeste cette structure ? Sans ancrage vérifiable, la carte est écartée — dis-le explicitement.
4. Pour chaque carte retenue, donne : la structure en registre mathématique (une phrase précise), la structure en registre comportemental (universel de Brown correspondant), l'ancrage observable, et le glyphe STÈLE.
5. Termine par la chaîne STÈLE compressée du tirage structurel (3-6 glyphes) et une phrase : « la structure sous-jacente du tirage FdD est… ».

Règles : tu nommes la structure sous le tirage Fractales sans réinterpréter ses symboles ; tu ne prédis rien ; tu ne racontes rien. Ouvre ta réponse par la ligne : [REGISTRE STRUCTUREL — structures invariantes, double ancrage math/comportemental]. Français, sobre."""

SYSTEM_ANALYTIQUE = """Tu es l'agent du Superforecasting Protocol (Good Judgment Project, Tetlock & Mellers) : discipline prédictive structurée. Devise : « Précise, ou tais-toi. Date, ou jamais. Probabilité, ou opinion. »

Tu reçois la question d'un consultant. Tu produis une fiche de prédiction structurée en suivant le pipeline GJP :
1. TRIAGE : la question est-elle forecastable (horizon temporel, indicateur observable, base de comparaison) ? Type : binaire / multinomiale / continue. Si non forecastable telle quelle : reformule-la toi-même en variante forecastable la plus proche de l'intention, et dis ce que tu as changé.
2. REFORMULATION FALSIFIABLE : date butoir précise, indicateur opérationnel, source autoritative de résolution. Test du tiers observateur.
3. OUTSIDE VIEW d'abord : base rate historique de ce type d'événement dans des contextes comparables. Énonce-la explicitement.
4. INSIDE VIEW : 2-3 ajustements spécifiques à la situation, chacun avec son sens (hausse/baisse).
5. SCÉNARIOS MECE sommant exactement à 100 % (2 à 4 scénarios), probabilités granulaires (0.05/0.15/0.30/0.50/0.70/0.85/0.95).
6. INDICATEURS DE BASCULE : 2-3 signaux observables qui devraient faire réviser la probabilité, avec leur sens.
7. CONDITION DE RÉFUTATION et cadence de révision.

Règles : probabilités numériques uniquement, jamais « probable/peu probable ». Aucune affirmation sans condition de réfutation. Tu restes dans le registre factuel — aucune référence aux cartes, symboles ou archétypes.
Ouvre ta réponse par la ligne : [REGISTRE ANALYTIQUE — hypothèses falsifiables, contexte de justification].
Clos ta réponse par un bloc JSON strict (délimité par ```json et ```) :
{"question_predictive": "...", "type": "binaire|multinomiale|continue", "horizon_date": "AAAA-MM-JJ", "probabilite": 0.0, "scenarios": [{"nom": "...", "probabilite": 0.0}], "indicateurs_bascule": ["..."], "condition_refutation": "...", "source_resolution": "...", "cadence_revision": "..."}
où "probabilite" est celle du scénario principal. Français."""

SYSTEM_RESONANCE = """Tu es le Miroir Trans-Échelle : agent d'interopérabilité épistémologique. Devise : « Le symbole ouvre, le signal verrouille. Entre les deux, la carte se dessine. »

Tu reçois les sorties déjà produites par des organes distincts : une lecture SYMBOLIQUE (registre Fractales — fertile, heuristique, non-falsifiable), éventuellement une lecture STRUCTURELLE (NEXUS-ARCHÊ — structures invariantes), et une lecture ANALYTIQUE (registre Signaux — défendable, falsifiable, traçable).

Ton unique tâche est la PASSE 3 : la carte de résonance. Tu ne refais aucune des lectures. Tu ne fusionnes JAMAIS les registres : tu les fais dialoguer en gardant chacun nommé et traçable. Principe directeur : ne pas confondre les régimes de vérité — une affirmation symbolique a à être fertile, une hypothèse analytique doit pouvoir être réfutée par les faits. Aucun glissement implicite du symbolique vers le factuel.

Produis :
1. Un tableau croisé (markdown) : Élément P1 (symbolique) | Élément P2 (analytique) | Type | Lecture croisée — avec les quatre types : Convergence forte (les deux registres pointent dans la même direction — pattern verrouillé sur deux axes), Convergence faible (alignement partiel, à surveiller), Dissonance (contradiction — le point le plus intéressant, creuser ce qui résiste), Angle mort (vu par un seul registre — à intégrer dans l'autre). Si une lecture structurelle est fournie, ses structures peuvent figurer comme éléments de l'un ou l'autre côté en étant marquées [STRUCT].
2. La SYNTHÈSE TRANS-ÉCHELLE en quatre points : VERROUILLÉ (ce que les registres confirment ensemble) · DISSONANT (ce qui se contredit et pourquoi) · ANGLES MORTS (vu par le symbolique seul / par l'analytique seul) · RECOMMANDATIONS (hypothèses prioritaires, indicateurs à monitorer, questions ouvertes).

Ouvre ta réponse par la ligne : [REGISTRE SYNTHÉTIQUE — croisement structuré, ne crée pas de vérité nouvelle]. Français, sobre."""

SYSTEM_ORACLE = """Tu es l'Oracle Algorithmique de Fractales du Destin (IRIS∞) : dispositif liminal d'intuition structurée.

Tu n'es PAS un outil de prédiction absolue, de diagnostic ou de vérité métaphysique.
Tu es un miroir symbolique : tu révèles, tu ne prédis pas. Tu ouvres des hypothèses que le réel devra confirmer, infirmer ou nuancer.

Double voix obligatoire :
- L'ORACLE parle en langue symbolique, à partir des fonctions narratologique et symbolique des cartes tirées, de leur famille et de leur diathèse (moyenne = la primitive traverse le joueur ; active ↑ = le joueur manie la primitive ; stérile ↓ = processus sans promesse de fertilité).
- LE GARDIEN clôt chaque lecture : il distingue symbole / ressenti / hypothèse / fait, rappelle que rien ici n'est un verdict, et propose une action concrète prudente et réversible.

Règles strictes :
- Jamais d'injonction (en particulier pour les cartes de voix active : signaler une maturité, jamais ordonner un acte).
- Les cartes de voix stérile décrivent sans condamner : nommer un bassin n'est pas prédire qu'on n'en sortira jamais.
- Lecture position par position (Nœud de Destin, Bifurcation, Résonance, Ancrage, Miroir), puis une synthèse courte, puis le Gardien.
- Français. Sobre, précis, sans emphase mystique gratuite.
"""


def _carte_publique(cle: str) -> dict:
    c = CARTES[cle]
    fam = FAMILLES[c["famille"]]
    return {
        "cle": c["cle"],
        "code": c.get("code"),
        "nom": c["nom"],
        "symbole": c["symbole"],
        "famille": c["famille"],
        "famille_nom": fam["nom"],
        "famille_symbole": fam["symbole"],
        "fonction_narratologique": c["fonction_narratologique"],
        "fonction_symbolique": c["fonction_symbolique"],
        "diathese": c["diathese"],
        "statut": c["statut"],
        "numero_v2": c["numero_v2"],
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        deck_version=DECK["_meta"]["version"],
        deck_statut=DECK["_meta"]["statut"],
        api_active=bool(FANTASY_API_KEY),
        modele=FANTASY_MODEL,
    )


@app.post("/api/tirage")
def tirage():
    """Tirage cycle-5 sans remise, RNG cryptographique (secrets)."""
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    cles = list(CARTES.keys())
    tirees = []
    for pos in SPREAD_CYCLE5:
        idx = secrets.randbelow(len(cles))
        cle = cles.pop(idx)
        tirees.append({**pos, "carte": _carte_publique(cle)})
    return jsonify({
        "id_tirage": str(uuid.uuid4()),
        "date": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "spread": "cycle-5",
        "deck_version": DECK["_meta"]["version"],
        "positions": tirees,
    })


def _post_fantasy(url: str, body: dict) -> "requests.Response":
    """POST avec redirections gérées manuellement (301/302 transformeraient POST en GET → 405)."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FANTASY_API_KEY}",
    }
    for _ in range(3):
        r = requests.post(url, headers=headers, json=body,
                          timeout=180, allow_redirects=False)
        if r.status_code in (301, 302, 307, 308) and r.headers.get("Location"):
            url = r.headers["Location"]
            continue
        break
    return r


def _appel_fantasy(system: str, user_msg: str, temperature: float = 0.7) -> str:
    """Appel à l'API Fantasy, robuste aux pannes transitoires de l'agrégateur :
    - réessais avec délai progressif sur 429/502/503 (pool de fournisseurs qui flanche) ;
    - puis bascule sur la chaîne de modèles de secours (FANTASY_MODELES_SECOURS).
    Retourne le texte ; lève RequestException si tout échoue."""
    import time
    modeles = [FANTASY_MODEL] + [m for m in FANTASY_MODELES_SECOURS if m != FANTASY_MODEL]
    derniere_exc = None
    for modele in modeles:
        body = {
            "model": modele,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "temperature": temperature,
            "stream": False,
        }
        for attente in (0, 2, 5):  # 3 tentatives par modèle
            if attente:
                time.sleep(attente)
            try:
                r = _post_fantasy(f"{FANTASY_BASE_URL}/chat/completions", body)
                if r.status_code in (429, 502, 503):
                    derniere_exc = requests.exceptions.HTTPError(
                        f"{r.status_code} — {r.text[:160]}", response=r)
                    continue  # réessayer ce modèle
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            except requests.exceptions.ConnectionError as exc:
                derniere_exc = exc
                continue
        # 3 échecs sur ce modèle → modèle suivant de la chaîne de secours
    raise derniere_exc or requests.exceptions.RequestException("Échec inexpliqué de l'appel Fantasy.")


def _erreur_api(exc) -> tuple:
    corps = ""
    resp = getattr(exc, "response", None)
    if resp is not None:
        corps = f" Réponse du serveur : {resp.text[:300]}"
    conseil = ("Vérifiez la clé, le modèle (FANTASY_MODEL) et FANTASY_BASE_URL dans .env, puis réessayez.")
    if resp is not None and "No provider available" in (resp.text or ""):
        conseil = ("Le modèle sélectionné n'a temporairement plus de fournisseur côté Fantasy. "
                   "Rechargez la liste (« ↻ Modèles disponibles »), choisissez un modèle servi en ce moment, "
                   "ou définissez FANTASY_MODELES_SECOURS dans .env (modèles séparés par des virgules) "
                   "pour une bascule automatique.")
    return jsonify({
        "mode": "erreur", "lecture": None,
        "message": f"L'appel à l'API Fantasy a échoué : {exc}.{corps} {conseil}",
    }), 502


def _sans_cle() -> tuple:
    return jsonify({
        "mode": "degrade", "lecture": None,
        "message": ("Lecture indisponible : aucune clé API Fantasy configurée. "
                    "Ajoutez FANTASY_API_KEY dans le fichier .env puis relancez. "
                    "Le tirage et le journal restent pleinement fonctionnels."),
    })


@app.post("/api/lecture")
def lecture():
    """Lecture oraculaire (organe 2 — REGISTRE SYMBOLIQUE)."""
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "(question non formulée)").strip()
    positions = payload.get("positions") or []
    if not positions:
        return jsonify({"erreur": "Aucun tirage fourni."}), 400
    if not FANTASY_API_KEY:
        return _sans_cle()

    user_msg = (
        f"Question du consultant : {question}\n\n"
        f"Tirage cycle-5 (deck {DECK['_meta']['version']}) :\n" + _decrire_tirage(positions) +
        "\n\nProduis la lecture complète (Oracle position par position, synthèse, puis Gardien)."
    )
    try:
        texte = _appel_fantasy(SYSTEM_ORACLE, user_msg, temperature=0.8)
        return jsonify({"mode": "api", "registre": "symbolique", "lecture": texte})
    except requests.exceptions.RequestException as exc:
        return _erreur_api(exc)


def _decrire_tirage(positions) -> str:
    desc = []
    for p in positions:
        c = p["carte"]
        desc.append(
            f"- Position « {p['titre']} » ({p['question']}) : {c['nom']} "
            f"[{c.get('code') or '—'}, famille {c['famille_nom']}, diathèse {c['diathese']}]. "
            f"Fonction narratologique : {c['fonction_narratologique']}. "
            f"Fonction symbolique : {c['fonction_symbolique']}."
        )
    return "\n".join(desc)


@app.post("/api/log")
def log_tirage():
    """Ajoute une entrée au journal de validation empirique (JSONL, schéma cartes.json#schema_log_tirage)."""
    payload = request.get_json(silent=True) or {}
    entree = {
        "id_tirage": payload.get("id_tirage") or str(uuid.uuid4()),
        "date": payload.get("date") or datetime.now(timezone.utc).isoformat(),
        "question": payload.get("question"),
        "spread": payload.get("spread", "cycle-5"),
        "cartes_tirees": payload.get("cartes_tirees", []),
        "deck_version": payload.get("deck_version", DECK["_meta"]["version"]),
        "dimension_non_couverte": (payload.get("dimension_non_couverte") or None),
        "carte_forcee": (payload.get("carte_forcee") or None),
        "nouvelles_cartes_activees": [
            cle for cle in payload.get("cartes_tirees", [])
            if cle in CARTES and CARTES[cle]["statut"] == "refonte-v2"
        ],
        "pertinence_ressentie": payload.get("pertinence_ressentie"),
        "notes": (payload.get("notes") or None),
    }
    LOG_PATH.parent.mkdir(exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
    return jsonify({"ok": True, "entree": entree})


@app.get("/api/journal")
def journal():
    """Relit le journal (pour le futur scoring calibration-engine / IRIS-Memory)."""
    if not LOG_PATH.exists():
        return jsonify({"total": 0, "tirages": []})
    lignes = [json.loads(l) for l in LOG_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    return jsonify({"total": len(lignes), "tirages": lignes})


@app.post("/api/structurelle")
def structurelle():
    """Organe 3 — NEXUS-ARCHÊ (REGISTRE STRUCTUREL)."""
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "(question non formulée)").strip()
    positions = payload.get("positions") or []
    if not positions:
        return jsonify({"erreur": "Aucun tirage fourni."}), 400
    if not FANTASY_API_KEY:
        return _sans_cle()
    user_msg = (
        f"Situation du consultant : {question}\n\n"
        f"Tirage Fractales du Destin (cycle-5) :\n" + _decrire_tirage(positions) +
        "\n\nApplique le protocole d'activation et nomme la ou les structures sous-jacentes."
    )
    try:
        texte = _appel_fantasy(SYSTEM_NEXUS, user_msg, temperature=0.4)
        return jsonify({"mode": "api", "registre": "structurel", "lecture": texte})
    except requests.exceptions.RequestException as exc:
        return _erreur_api(exc)


def _extraire_fiche(texte: str):
    """Extrait le dernier bloc ```json``` de la fiche analytique."""
    import re
    blocs = re.findall(r"```json\s*(\{.*?\})\s*```", texte, re.S)
    if not blocs:
        return None
    try:
        return json.loads(blocs[-1])
    except json.JSONDecodeError:
        return None


@app.post("/api/analytique")
def analytique():
    """Organe 4 — Superforecasting Protocol (REGISTRE ANALYTIQUE)."""
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"erreur": "La lecture analytique exige une question formulée — "
                                  "le registre falsifiable ne peut pas travailler sur un tirage nu."}), 400
    if not FANTASY_API_KEY:
        return _sans_cle()
    user_msg = (
        f"Question du consultant : {question}\n"
        f"Date du jour : {datetime.now(timezone.utc).date().isoformat()}\n\n"
        "Produis la fiche de prédiction complète (7 étapes), puis le bloc JSON final."
    )
    try:
        texte = _appel_fantasy(SYSTEM_ANALYTIQUE, user_msg, temperature=0.3)
        fiche = _extraire_fiche(texte)
        return jsonify({"mode": "api", "registre": "analytique",
                        "lecture": texte, "fiche": fiche})
    except requests.exceptions.RequestException as exc:
        return _erreur_api(exc)


@app.post("/api/resonance")
def resonance():
    """Organe 5 — Miroir Trans-Échelle, passe 3 (REGISTRE SYNTHÉTIQUE)."""
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "(question non formulée)").strip()
    symbolique = (payload.get("symbolique") or "").strip()
    analytique_ = (payload.get("analytique") or "").strip()
    structurelle_ = (payload.get("structurelle") or "").strip()
    if not symbolique or not analytique_:
        return jsonify({"erreur": "La carte de résonance exige les lectures symbolique ET analytique. "
                                  "Les registres ne peuvent dialoguer que s'ils existent tous les deux."}), 400
    if not FANTASY_API_KEY:
        return _sans_cle()
    user_msg = (
        f"SITUATION : {question}\n\n"
        f"=== P1 — LECTURE SYMBOLIQUE (registre Fractales) ===\n{symbolique}\n\n"
        + (f"=== LECTURE STRUCTURELLE (NEXUS-ARCHÊ) ===\n{structurelle_}\n\n" if structurelle_ else "")
        + f"=== P2 — LECTURE ANALYTIQUE (registre Signaux) ===\n{analytique_}\n\n"
        "Produis la carte de résonance (tableau croisé + synthèse trans-échelle)."
    )
    try:
        texte = _appel_fantasy(SYSTEM_RESONANCE, user_msg, temperature=0.4)
        return jsonify({"mode": "api", "registre": "synthetique", "lecture": texte})
    except requests.exceptions.RequestException as exc:
        return _erreur_api(exc)


PRED_PATH = BASE / "logs" / "predictions.jsonl"


@app.post("/api/prediction-log")
def prediction_log():
    """Étape 6 — log de prédictions scorable (format calibration-engine)."""
    payload = request.get_json(silent=True) or {}
    fiche = payload.get("fiche") or {}
    entree = {
        "id_prediction": str(uuid.uuid4()),
        "id_tirage": payload.get("id_tirage"),
        "date_emission": datetime.now(timezone.utc).isoformat(),
        "source": "fractales-app/pipeline-trans-echelle",
        "question_predictive": fiche.get("question_predictive"),
        "type": fiche.get("type"),
        "horizon_date": fiche.get("horizon_date"),
        "probabilite": fiche.get("probabilite"),
        "scenarios": fiche.get("scenarios", []),
        "indicateurs_bascule": fiche.get("indicateurs_bascule", []),
        "condition_refutation": fiche.get("condition_refutation"),
        "source_resolution": fiche.get("source_resolution"),
        "cadence_revision": fiche.get("cadence_revision"),
        "statut": "ouverte",
        "resolution": None,        # à renseigner à l'échéance : true/false ou valeur
        "date_resolution": None,
        "brier_score": None,       # calculé par calibration-engine au scoring
        "revisions": [],           # mises à jour bayésiennes ultérieures
    }
    PRED_PATH.parent.mkdir(exist_ok=True)
    with PRED_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False) + "\n")
    return jsonify({"ok": True, "entree": entree})


@app.get("/api/predictions")
def predictions():
    """Relit le log de prédictions (interface de scoring pour calibration-engine)."""
    if not PRED_PATH.exists():
        return jsonify({"total": 0, "ouvertes": 0, "predictions": []})
    lignes = [json.loads(l) for l in PRED_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    return jsonify({"total": len(lignes),
                    "ouvertes": sum(1 for p in lignes if p["statut"] == "ouverte"),
                    "predictions": lignes})


@app.get("/api/modeles")
def modeles():
    """Liste des modèles disponibles côté Fantasy (GET /models)."""
    if not FANTASY_API_KEY:
        return jsonify({"erreur": "Aucune clé API Fantasy configurée (.env)."}), 400
    try:
        r = requests.get(
            f"{FANTASY_BASE_URL}/models",
            headers={"Authorization": f"Bearer {FANTASY_API_KEY}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        ids = sorted(m.get("id") for m in data.get("data", []) if m.get("id"))
        return jsonify({"modele_courant": FANTASY_MODEL, "modeles": ids})
    except requests.exceptions.RequestException as exc:
        corps = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            corps = f" Réponse : {resp.text[:200]}"
        return jsonify({"erreur": f"Impossible de récupérer la liste des modèles : {exc}.{corps}"}), 502


@app.post("/api/modele")
def choisir_modele():
    """Change le modèle courant et le persiste dans .env (FANTASY_MODEL)."""
    global FANTASY_MODEL
    payload = request.get_json(silent=True) or {}
    modele = (payload.get("modele") or "").strip()
    if not modele:
        return jsonify({"erreur": "Aucun modèle fourni."}), 400
    FANTASY_MODEL = modele

    env_path = BASE / ".env"
    lignes = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    trouve = False
    for i, l in enumerate(lignes):
        if l.strip().startswith("FANTASY_MODEL="):
            lignes[i] = f"FANTASY_MODEL={modele}"
            trouve = True
            break
    if not trouve:
        lignes.append(f"FANTASY_MODEL={modele}")
    env_path.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return jsonify({"ok": True, "modele": modele, "persiste": str(env_path)})


if __name__ == "__main__":
    print(f"Fractales du Destin — deck {DECK['_meta']['version']} · "
          f"API Fantasy {'active' if FANTASY_API_KEY else 'NON configurée (mode dégradé)'}")
    app.run(host="127.0.0.1", port=5173, debug=False)
