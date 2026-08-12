import os, json, math, collections
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import hdbscan
except Exception:
    hdbscan = None

MODEL_NAME = os.getenv('BTS_EMBEDDING_MODEL', 'BAAI/bge-m3')
BATCH_SIZE = int(os.getenv('BTS_EMBED_BATCH', '32'))
MAX_INPUT = int(os.getenv('BTS_SEMANTIC_MAX_INPUT', '10000'))
MAX_OUTPUT = int(os.getenv('BTS_SEMANTIC_MAX_OUTPUT', '4500'))
MIN_SIM = float(os.getenv('BTS_MIN_PAIN_SIMILARITY', '0.42'))

PAINS = {
    'grow_with_child_ergonomics': [
        'Εργονομική καρέκλα μελέτης για παιδί ή έφηβο που μεγαλώνει, με πραγματική ρύθμιση βάθους καθίσματος, ύψους πλάτης και υποπόδιο ώστε η πλάτη και τα πόδια να στηρίζονται σωστά.',
        'A grow-with-child study chair with adjustable seat depth, back height, foot support and verified fit for children and teenagers, not merely seat-height adjustment.'
    ],
    'compact_space_study': [
        'Ποιοτικό γραφείο μελέτης για πολύ μικρό παιδικό ή φοιτητικό δωμάτιο, πτυσσόμενο ή επιτοίχιο, που εξοικονομεί πραγματικά χώρο και παραμένει σταθερό και ανθεκτικό.',
        'A durable space-saving study desk for a small bedroom, preferably wall-mounted, folding, floating or transformable, with useful storage and strong construction.'
    ],
    'premium_safe_audio': [
        'Ποιοτικά ακουστικά για μαθητή με ασφαλές όριο έντασης, πραγματική ενεργή ακύρωση θορύβου, καλό μικρόφωνο, άνεση πολλών ωρών και μεγάλη μπαταρία.',
        'Premium student headphones combining safe volume limiting, real ANC, microphone, long battery life and comfortable fit for study and online lessons.'
    ],
    'teen_carry_ergonomics': [
        'Σακίδιο για έφηβο που μεταφέρει βιβλία και laptop χωρίς παιδική εμφάνιση, με πραγματική εργονομική πλάτη, σωστή κατανομή βάρους, ανθεκτικότητα και προστασία συσκευής.',
        'Teen school and laptop backpack with genuine load distribution, padded ergonomic back, durable water-resistant construction and mature design.'
    ],
    'focus_and_organization': [
        'Λύση οργάνωσης ή συγκέντρωσης για μικρό χώρο μελέτης που μειώνει ακαταστασία ή θόρυβο και αξιοποιεί κάθετο ή κρυφό χώρο χωρίς να είναι απλό commodity organizer.',
        'Study-focus and organization solution using vertical, modular, under-desk, acoustic or privacy design for small rooms, beyond generic commodity organizers.'
    ],
    'stem_creator_tools': [
        'Ποιοτικό εργαλείο STEM ή δημιουργίας άνω των 50 ευρώ που δίνει πραγματική εκπαιδευτική χρησιμότητα σε μαθητή ή φοιτητή, όπως μικροσκόπιο, robotics/coding kit, drawing tablet ή creator hardware.',
        'High-quality STEM or creator hardware over EUR 50 with genuine educational utility for students, such as microscopy, robotics, coding, drawing or document-capture tools.'
    ],
}


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, float(v)))


def product_text(p):
    parts = [
        p.get('product_name'), p.get('model_name'), p.get('brand_name'), p.get('category_raw'),
        p.get('description'), p.get('size'), p.get('colour')
    ]
    return ' | '.join(str(x) for x in parts if x)


def normalize_rows(x):
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n[n == 0] = 1
    return x / n


def main():
    rows = []
    with open('bts-pre-candidates.jsonl', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= MAX_INPUT:
                break
            rows.append(json.loads(line))
    if not rows:
        raise RuntimeError('No BTS pre-candidates found')

    model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
    texts = [product_text(p) for p in rows]
    emb = model.encode(texts, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=True)
    emb = np.asarray(emb, dtype=np.float32)

    pain_names = list(PAINS)
    pain_texts = [' '.join(PAINS[k]) for k in pain_names]
    pain_emb = np.asarray(model.encode(pain_texts, batch_size=8, normalize_embeddings=True), dtype=np.float32)
    sims = emb @ pain_emb.T

    cluster_labels = np.full(len(rows), -1, dtype=int)
    if hdbscan is not None and len(rows) >= 60:
        # Cluster in the original semantic space. This discovers solution families missed by the seed labels.
        try:
            clusterer = hdbscan.HDBSCAN(min_cluster_size=12, min_samples=5, metric='euclidean', cluster_selection_method='eom')
            cluster_labels = clusterer.fit_predict(normalize_rows(emb))
        except Exception as exc:
            print(json.dumps({'warning': 'hdbscan_failed', 'error': str(exc)[:300]}), flush=True)

    ranked = []
    unsup = collections.defaultdict(list)
    for i, p in enumerate(rows):
        order = np.argsort(-sims[i])
        best_j = int(order[0])
        best_sim = float(sims[i, best_j])
        second = float(sims[i, int(order[1])]) if len(order) > 1 else 0.0
        semantic_score = clamp((best_sim - .25) / .55 * 100)
        specificity = clamp((best_sim - second + .05) / .25 * 100)
        pre = float(p.get('bts_prefilter_score') or 0)
        major_penalty = 16 if p.get('major_merchant_source') else 0
        score = clamp(semantic_score * .50 + pre * .38 + specificity * .12 - major_penalty)
        p['semantic_pain_cluster'] = pain_names[best_j]
        p['semantic_pain_similarity'] = round(best_sim, 5)
        p['semantic_second_similarity'] = round(second, 5)
        p['semantic_specificity'] = round(specificity, 2)
        p['unsupervised_solution_cluster'] = int(cluster_labels[i])
        p['semantic_stage_score'] = round(score, 3)
        if best_sim >= MIN_SIM:
            ranked.append(p)
        if cluster_labels[i] >= 0:
            unsup[int(cluster_labels[i])].append((score, i, p.get('product_name'), p.get('category_raw'), p.get('merchant_name')))

    ranked.sort(key=lambda p: p['semantic_stage_score'], reverse=True)
    ranked = ranked[:MAX_OUTPUT]
    with open('bts-semantic-candidates.jsonl', 'w', encoding='utf-8') as f:
        for p in ranked:
            f.write(json.dumps(p, ensure_ascii=False, default=str) + '\n')

    cluster_summary = {}
    for label, items in unsup.items():
        items.sort(reverse=True)
        cluster_summary[str(label)] = {
            'size': len(items),
            'examples': [
                {'score': round(x[0], 2), 'product_name': x[2], 'category': x[3], 'merchant': x[4]}
                for x in items[:12]
            ]
        }
    Path('bts-unsupervised-clusters.json').write_text(json.dumps(cluster_summary, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {
        'embedding_model': MODEL_NAME,
        'input': len(rows),
        'semantic_survivors': len(ranked),
        'minimum_similarity': MIN_SIM,
        'unsupervised_clusters': len(cluster_summary),
        'policy': 'semantic retrieval is discovery evidence only; Greek demand, competition, offline scarcity, quality and true-deal audits remain mandatory'
    }
    Path('bts-semantic-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
