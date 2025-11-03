import json, os
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer, util
    sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    sbert_model = None


def load_tm_models(path=None):
    if not path:
        path = os.path.join("models", "tm_models.json")
    with open(path, "r") as f:
        return json.load(f)


def save_tm_models(models, path=None):
    if not path:
        path = os.path.join("models", "tm_models.json")

    backup_path = path.replace(".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    # Create a backup before overwriting
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2)


def semantic_match(phrase, keywords, threshold=0.55):
    if sbert_model:
        try:
            sims = util.pytorch_cos_sim(
                sbert_model.encode(phrase, convert_to_tensor=True),
                sbert_model.encode(keywords, convert_to_tensor=True),
            )
            max_sim = float(sims.max())
            return max_sim >= threshold, max_sim
        except Exception:
            pass
    for kw in keywords:
        if kw.lower() in phrase.lower() or phrase.lower() in kw.lower():
            return True, 1.0
    return False, 0.0


def assess_coverage(extracted_phrases, semantic=True, tm_model_file=None, auto_update=True):
    """
    Evaluate extracted FATF risks against TM models.
    Optionally auto-update tm_models.json for uncovered risks.
    """
    tm_models = load_tm_models(tm_model_file)
    updated = False
    results = []

    for model in tm_models:
        matched = []
        partially_matched = []
        not_covered_risks = []

        all_known_risks = (
            model.get("covered_risks", [])
            + model.get("partially_covered_risks", [])
            + model.get("not_covered_risks", [])
        )

        for phrase in extracted_phrases:
            phrase_l = phrase.lower()
            found = False

            # Exact or partial matches
            for cat, bucket in {
                "Covered": model.get("covered_risks", []),
                "Partially Covered": model.get("partially_covered_risks", []),
            }.items():
                for kw in bucket:
                    if kw.lower() in phrase_l or phrase_l in kw.lower():
                        matched.append(phrase)
                        found = True
                        break
                if found:
                    break

            # Semantic fallback
            if not found and semantic:
                matched_flag, score = semantic_match(phrase, all_known_risks)
                if matched_flag and score >= 0.7:
                    partially_matched.append(f"{phrase} (sim={score:.2f})")
                    found = True

            # Not covered case
            if not found:
                not_covered_risks.append(phrase)
                # Update tm_model.json dynamically
                if auto_update:
                    if phrase not in model.get("not_covered_risks", []):
                        model.setdefault("not_covered_risks", []).append(phrase)
                        updated = True

        # Assign coverage label
        if len(matched) == len(extracted_phrases):
            coverage = "Completely Covered"
        elif matched or partially_matched:
            coverage = "Partially Covered"
        elif not extracted_phrases:
            coverage = "No Risks Found"
        else:
            coverage = "Not Covered"

        results.append(
            {
                "model_name": model.get("model_name"),
                "matched_risks": ", ".join(matched + partially_matched) or "None",
                "newly_added_not_covered": ", ".join(not_covered_risks) or "None",
                "coverage_status": coverage,
            }
        )

    # Save updated models back if needed
    if auto_update and updated:
        save_tm_models(tm_models)
        print("✅ tm_models.json updated with new uncovered risks.")

    return results
