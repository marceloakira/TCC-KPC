'''
Inter-annotator agreement (IAA) between two keyphrase curation files

Metrics follow section 4.3 of the keyphrase curation article and the
notebooks/*-agreement.ipynb that produced its Table 3:
- Keyphrase Clustering (KC): ARI, AMI, NMI and FMS (scikit-learn)
- Cluster Filtering (CF): Krippendorff's alpha with Jaccard distance (NLTK)
- Keyphrase Selection (KS): Fleiss' kappa with Jaccard distance (NLTK)

The notebook reported as "NMI" is adjusted_mutual_info_score, i.e. AMI.

KC metrics do not depend on cluster numbering. CF and KS compare cluster i
of one annotator with cluster i of the other, so independent annotations
must be aligned first (align_clusters).
'''
from statistics import mean

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_mutual_info_score, \
    adjusted_rand_score, fowlkes_mallows_score, normalized_mutual_info_score

from keyphrase_curation.model.annotation import ClusterSetsMatcher

# Table 3 averages (death penalty and marijuana legalization)
ARTICLE_KC_REFERENCE = {'ari': 0.36, 'ami': 0.50, 'fms': 0.39}

# Tie breaker: keeps the current numbering when it is already a best matching
_SAME_ID_BONUS = 1e-6


def check_same_keyphrases(data1, data2):
    '''Raise ValueError if both files do not annotate the same keyphrases'''
    keyphrases1 = {
        int(k): v['keyphrase'] for k, v in data1['keyphrases'].items()}
    keyphrases2 = {
        int(k): v['keyphrase'] for k, v in data2['keyphrases'].items()}
    if keyphrases1 != keyphrases2:
        raise ValueError('Annotation files have different keyphrases')


def cluster_labels(data):
    '''Cluster id of each keyphrase, ordered by keyphrase id
    (0 means not clustered)
    '''
    labels = [0] * len(data['keyphrases'])
    for cluster_id, cluster in data['clusters'].items():
        for keyphrase_id in cluster['keyphrases']:
            labels[int(keyphrase_id) - 1] = int(cluster_id)
    return labels


def cluster_sets(data, cluster_ids_length):
    '''{cluster_id: set of keyphrase ids}, for every cluster id'''
    sets = {i: set() for i in range(1, cluster_ids_length + 1)}
    for cluster_id, cluster in data['clusters'].items():
        sets[int(cluster_id)] = {int(k) for k in cluster['keyphrases']}
    return sets


def align_clusters(sets1, sets2, cluster_ids_length):
    '''Match each cluster of annotator 2 to a cluster of annotator 1

    Hungarian algorithm over the Jaccard index of the keyphrase sets. The
    discard cluster (last id) is always matched to itself.

    Returns:
        dict: {cluster_id of annotator 2: cluster_id of annotator 1}
    '''
    discard_id = cluster_ids_length
    ids = list(range(1, discard_id))
    cost_matrix = np.array(ClusterSetsMatcher.get_cost_matrix(
        {i: sets1[i] for i in ids},
        {i: sets2[i] for i in ids}), dtype=float)
    cost_matrix += np.eye(len(ids)) * _SAME_ID_BONUS
    rows, cols = linear_sum_assignment(cost_matrix, maximize=True)
    mapping = {ids[c]: ids[r] for r, c in zip(rows, cols)}
    mapping[discard_id] = discard_id
    return mapping


def mean_matched_jaccard(sets1, sets2, mapping):
    '''Mean Jaccard index of matched clusters, ignoring the discard cluster
    and pairs of empty clusters
    '''
    discard_id = max(mapping)
    values = []
    for id2, id1 in mapping.items():
        if id2 == discard_id:
            continue
        union = sets1[id1] | sets2[id2]
        if union:
            values.append(len(sets1[id1] & sets2[id2]) / len(union))
    return mean(values) if values else None


def kc_metrics(labels1, labels2):
    '''Keyphrase Clustering agreement (independent of cluster numbering)'''
    return {
        'ari': adjusted_rand_score(labels1, labels2),
        'ami': adjusted_mutual_info_score(labels1, labels2),
        'nmi': normalized_mutual_info_score(labels1, labels2),
        'fms': fowlkes_mallows_score(labels1, labels2),
    }


def kc_agreement(data1, data2, cluster_ids_length):
    '''Keyphrase Clustering agreement between two annotation files

    Returns:
        dict: complete (no keyphrase left in cluster 0), n_keyphrases,
        not_clustered (per annotator), convergent (keyphrases in matched
        clusters), mean_matched_jaccard, mapping (see align_clusters) and
        kc (kc_metrics, or None if an annotation is incomplete)
    '''
    check_same_keyphrases(data1, data2)
    labels1 = cluster_labels(data1)
    labels2 = cluster_labels(data2)
    sets1 = cluster_sets(data1, cluster_ids_length)
    sets2 = cluster_sets(data2, cluster_ids_length)
    mapping = align_clusters(sets1, sets2, cluster_ids_length)
    aligned_labels2 = [mapping.get(label, label) for label in labels2]
    not_clustered = [labels1.count(0), labels2.count(0)]
    complete = not_clustered == [0, 0]
    return {
        'complete': complete,
        'n_keyphrases': len(labels1),
        'not_clustered': not_clustered,
        'convergent': sum(
            1 for a, b in zip(labels1, aligned_labels2) if a == b != 0),
        'mean_matched_jaccard': mean_matched_jaccard(sets1, sets2, mapping),
        'mapping': mapping,
        'kc': kc_metrics(labels1, labels2) if complete else None,
    }


def _nltk_agreement(labels1, labels2, method):
    '''NLTK AnnotationTask metric with Jaccard distance; None when undefined
    (a single label overall, where NLTK would return a vacuous 1)
    '''
    # NLTK is only needed by CF/KS (agreement report), not by the API
    from nltk.metrics.agreement import AnnotationTask
    from nltk.metrics.distance import jaccard_distance
    if len(set(labels1) | set(labels2)) < 2:
        return None
    data = [('1', i, label) for i, label in enumerate(labels1)] + \
        [('2', i, label) for i, label in enumerate(labels2)]
    task = AnnotationTask(data=data, distance=jaccard_distance)
    try:
        return float(getattr(task, method)())
    except ZeroDivisionError:
        return None


def _aligned_clusters(data1, data2, mapping, cluster_ids):
    '''Pairs (cluster of annotator 1, matched cluster of annotator 2)'''
    inverse = {id1: id2 for id2, id1 in mapping.items()}
    empty = {}
    return [
        (data1['clusters'].get(str(i), empty),
         data2['clusters'].get(str(inverse[i]), empty))
        for i in cluster_ids
    ]


def cf_agreement(data1, data2, mapping):
    '''Cluster Filtering agreement: Krippendorff's alpha with Jaccard
    distance over the selection (CS) of matched clusters, discard cluster
    excluded. None when undefined (e.g. no variation at all).
    '''
    discard_id = max(mapping)
    pairs = _aligned_clusters(data1, data2, mapping, range(1, discard_id))
    labels1 = [frozenset([int(c1.get('selected', 0))]) for c1, _ in pairs]
    labels2 = [frozenset([int(c2.get('selected', 0))]) for _, c2 in pairs]
    return _nltk_agreement(labels1, labels2, 'alpha')


def ks_agreement(data1, data2, mapping):
    '''Keyphrase Selection agreement: Fleiss' kappa (NLTK multi_kappa) with
    Jaccard distance over {S1, S2} of matched clusters, discard cluster
    included, as in the notebooks. None when undefined.
    '''
    discard_id = max(mapping)
    pairs = _aligned_clusters(data1, data2, mapping, range(1, discard_id + 1))

    def selection(cluster):
        return frozenset((int(cluster.get('keyphrase1_selected', 0)),
                          int(cluster.get('keyphrase2_selected', 0))))

    labels1 = [selection(c1) for c1, _ in pairs]
    labels2 = [selection(c2) for _, c2 in pairs]
    return _nltk_agreement(labels1, labels2, 'multi_kappa')
