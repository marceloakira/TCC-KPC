from scipy.optimize import linear_sum_assignment
from itertools import islice

import numpy as np

import datetime
import shutil
import json
from pathlib import Path

from enum import Enum
from keyphrase_curation.model.cluster import KeyphraseClustering


class AnnotationTask(Enum):
    KEYPHRASE_CLUSTERING = "keyphrase_clustering"
    CLUSTER_SELECTION = "cluster_selection"
    KEYPHRASE_SELECTION = "keyphrase_selection"
    KEYPHRASE_ALIAS = "keyphrase_alias"


class KeyphraseCurationFile:
    '''
    Class for loading and saving annotations
    '''

    def __init__(self, filepath):
        self.filepath = filepath
        self.json_filepath = str(Path(filepath).with_suffix('.json'))

    def get_clustering_from_clusters(self, data, check_consistency=True):
        clusters = data['clusters']
        keyphrases = data['keyphrases']
        clustering = [0] * len(keyphrases)
        for cluster_id in clusters:
            for keyphrase_id in clusters[cluster_id]['keyphrases']:
                position = int(keyphrase_id) - 1
                if clustering[position] != 0 and check_consistency:
                    raise ValueError(
                        f'Error: keyphrase {keyphrase_id} already clustered')
                clustering[int(keyphrase_id)-1] = int(cluster_id)
        return clustering

    def is_clustering_consistent(self, data):
        try:
            self.get_clustering_from_clusters(data, False)
        except ValueError:
            return False
        return True

    def get_data_from_json(self, check_consistency=True):
        data = json.load(open(self.json_filepath))
        if check_consistency:
            if not self.is_clustering_consistent(data):
                raise ValueError('Error: clustering not consistent')
        return data

    def backup_file(self, filepath=None):
        if filepath is None:
            filepath = self.filepath
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        try:
            shutil.copy(
                self.filepath, self.filepath + '.' + timestamp + '.bkp')
        except Exception as e:
            print(f'Backup failed: {e}')
            return False
        return True

    def save_annotations_to_json(self, annotations,
                                 annotation_task, backup=False):
        if len(annotations) == 0:
            return True
        if backup:
            if self.backup_file(self.json_filepath):
                print('Backup created.')
            else:
                print('Backup not created.')
                return False
        data = self.get_data_from_json()
        try:
            if annotation_task == AnnotationTask.KEYPHRASE_CLUSTERING:
                clustering = self.get_clustering_from_clusters(data)
                for kw_id in annotations:
                    old_cluster = clustering[int(kw_id)-1]
                    cluster_id = str(annotations[kw_id])
                    if old_cluster != 0:
                        data['clusters'][str(old_cluster)]['keyphrases'].\
                            remove(kw_id)
                    data['clusters'][cluster_id]['keyphrases'].\
                        append(kw_id)
            elif annotation_task == AnnotationTask.CLUSTER_SELECTION:
                for cluster_id in annotations:
                    data['clusters'][str(cluster_id)]['selected'] = \
                        annotations[cluster_id]
            elif annotation_task == AnnotationTask.KEYPHRASE_SELECTION:
                for cluster_id in annotations:
                    selected1 = annotations[cluster_id]['selected1']
                    selected2 = annotations[cluster_id]['selected2']
                    data['clusters'][str(cluster_id)][
                        'keyphrase1_selected'] = selected1
                    data['clusters'][str(cluster_id)][
                        'keyphrase2_selected'] = selected2
            elif annotation_task == AnnotationTask.KEYPHRASE_ALIAS:
                for cluster_id in annotations:
                    data['clusters'][str(cluster_id)]['alias'] = annotations[
                        cluster_id]
            else:
                raise ValueError(f'Unknown annotation task: {annotation_task}')
            with open(self.json_filepath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f'Save failed: {e}')
            return False
        return True

    def get_annotations_from_json(self, annotation_task: AnnotationTask):
        annotations = {}
        data = json.load(open(self.json_filepath))
        if annotation_task == AnnotationTask.KEYPHRASE_CLUSTERING:
            for cluster_id in data['clusters']:
                cluster_id = str(cluster_id)
                for keyphrase_id in data['clusters'][cluster_id]['keyphrases']:
                    keyphrase_id = str(keyphrase_id)
                    annotations[str(keyphrase_id)] = {
                        'clustering': int(cluster_id),
                        'keyphrase':
                            data['keyphrases'][keyphrase_id]['keyphrase'],
                        'selected':
                            data['clusters'][cluster_id]['selected'],
                        'selected1':
                            data['clusters'][
                                cluster_id]['keyphrase1_selected'],
                        'selected2':
                            data['clusters'][cluster_id]['keyphrase2_selected'],
                        'alias':
                            data['clusters'][cluster_id]['alias']
                    }
        elif annotation_task == AnnotationTask.CLUSTER_SELECTION:
            for cluster_id in data['clusters']:
                cluster_id = str(cluster_id)
                annotations[cluster_id] = \
                    data['clusters'][cluster_id]['selected']
        elif annotation_task == AnnotationTask.KEYPHRASE_SELECTION:
            for cluster_id in data['clusters']:
                cluster_id = str(cluster_id)
                selected1 = data['clusters'][cluster_id]['keyphrase1_selected']
                selected2 = data['clusters'][cluster_id]['keyphrase2_selected']
                keyphrase1 = keyphrase2 = ''
                if selected1 != 0:
                    keyphrase1 = data['keyphrases'][str(
                        selected1)]['keyphrase']
                    if selected2 != 0:
                        keyphrase2 = data['keyphrases'][str(
                            selected2)]['keyphrase']
                annotations[cluster_id] = {
                    'selected1': selected1,
                    'selected2': selected2,
                    'keyphrase1': keyphrase1,
                    'keyphrase2': keyphrase2
                }
        elif annotation_task == AnnotationTask.KEYPHRASE_ALIAS:
            for cluster_id in data['clusters']:
                cluster_id = str(cluster_id)
                annotations[cluster_id] = data['clusters'][cluster_id]['alias']
        else:
            raise ValueError(f'Unknown annotation task: {annotation_task}')
        return annotations


class ClusterAnnotation(KeyphraseClustering):
    '''
    Models a cluster keyphrase annotation
    '''

    def __init__(self,
                 topic,
                 embeddings_path,
                 keyphrase_curation_file: KeyphraseCurationFile = None,
                 cluster_ids_length=33):
        super().__init__(topic, embeddings_path, cluster_ids_length)

        self.annotations_not_saved = {}

        self.keyphrase_curation_file = keyphrase_curation_file
        self.load_annotations_from_file()

    def add_annotation_not_saved(self, kw_id, cluster_id):
        self.annotations_not_saved[kw_id] = cluster_id

    def load_annotations_from_file(self):
        annotations = self.keyphrase_curation_file.get_annotations_from_json(
            annotation_task=AnnotationTask.KEYPHRASE_CLUSTERING)
        for kp_id in annotations:
            cluster_id = annotations[kp_id]['clustering']
            self.clustering[int(kp_id)-1] = cluster_id
        return annotations

    def save(self):
        return self.keyphrase_curation_file.save_annotations_to_json(
            self.annotations_not_saved,
            annotation_task=AnnotationTask.KEYPHRASE_CLUSTERING)

    def move_to_cluster(self, kw_id, cluster_id):
        keyphrase = self.get_keyphrase_by_id(kw_id)
        cluster = self.get_cluster_by_id(cluster_id)
        super().move_to_cluster(keyphrase, cluster)
        self.add_annotation_not_saved(kw_id, cluster_id)


class ClusterSetsMatcher:
    '''Algorithms for matching two KeyphraseClustering objects
    '''

    def __init__(self,
                 clustering1: KeyphraseClustering,
                 clustering2: KeyphraseClustering):
        '''Initialize the matcher with two cluster sets.
        '''
        self.clustering1 = clustering1
        self.clustering2 = clustering2

    def jaccard_index(ksa, ksb):
        return round(len(ksa.intersection(ksb)) / len(ksa.union(ksb)), 2)

    def cluster_similarity(
            self,
            cluster_id1: int,
            cluster_id2: int):
        '''Get cluster similarity
        '''
        cluster1 = self.clustering1.get_cluster_by_id(cluster_id1)
        cluster2 = self.clustering2.get_cluster_by_id(cluster_id2)
        return cluster1.get_similarity(cluster2)

    def get_cost_matrix(keyphrase_sets1, keyphrase_sets2):
        '''Get cost matrix
        '''
        cost_matrix = []
        for keyphrase_set_id1 in keyphrase_sets1:
            jaccard_indexes = []
            for keyphrase_set_id2 in keyphrase_sets2:
                keyphrase_set1 = keyphrase_sets1[keyphrase_set_id1]
                keyphrase_set2 = keyphrase_sets2[keyphrase_set_id2]
                jaccard_index = ClusterSetsMatcher.jaccard_index(
                    keyphrase_set1, keyphrase_set2)
                jaccard_indexes.append(jaccard_index)
            cost_matrix.append(jaccard_indexes)
        return cost_matrix

    def get_best_matching(self):
        '''Get best matching
        '''
        # ignore last cluster, it's the cluster of ignored keyphrases
        last_cluster_index = len(self.clustering1.clusters) - 1
        keyphrase_sets1 = self.clustering1.get_keyphrase_sets()
        keyphrase_sets2 = self.clustering2.get_keyphrase_sets()
        keyphrase_sets1_without_last_cluster = dict(islice(
            keyphrase_sets1.items(), last_cluster_index))
        keyphrase_sets2_without_last_cluster = dict(islice(
            keyphrase_sets2.items(), last_cluster_index))
        cost_matrix = np.array(ClusterSetsMatcher.get_cost_matrix(
            keyphrase_sets1_without_last_cluster,
            keyphrase_sets2_without_last_cluster))
        _, col_ind = linear_sum_assignment(cost_matrix, maximize=True)
        best_pairs = {}
        for r, c in enumerate(col_ind):
            jaccard_index = cost_matrix[r][c]
            similarity = self.cluster_similarity(r+1, c+1)
            best_pairs[(r+1, c+1)] = (jaccard_index, similarity)
        jaccard_index = ClusterSetsMatcher.jaccard_index(
            keyphrase_sets1[last_cluster_index+1],
            keyphrase_sets2[last_cluster_index+1]
        )
        similarity = self.cluster_similarity(
            last_cluster_index+1, last_cluster_index+1)
        best_pairs[(last_cluster_index+1, last_cluster_index+1)] = (
            jaccard_index, similarity
        )
        return [
            (k, best_pairs[k][0], best_pairs[k][1])
            for k in sorted(
                best_pairs, key=lambda k: (best_pairs[k][0], best_pairs[k][1]),
                reverse=True)
        ]

    def best_matching_reorder(self):
        '''Reorder clustering based on best matching
        '''
        best_matching = self.get_best_matching()
        ordered_clustering1 = self.clustering1.clustering.copy()
        ordered_clustering2 = self.clustering2.clustering.copy()
        from_to1 = {}
        from_to2 = {}
        for i, pairs in enumerate(best_matching):
            from1 = pairs[0][0]
            from2 = pairs[0][1]
            from_to1[from1] = i + 1
            from_to2[from2] = i + 1
        clustering_size = len(self.clustering1.clustering)
        ignored_cluster_id = len(self.clustering1.clusters)
        from_to1[ignored_cluster_id] = from_to2[ignored_cluster_id] = \
            ignored_cluster_id
        for i in range(clustering_size):
            ordered_clustering1[i] = from_to1[ordered_clustering1[i]]
            ordered_clustering2[i] = from_to2[ordered_clustering2[i]]
        return [ordered_clustering1, ordered_clustering2]


class ClusterSelectionAnnotation():
    '''
    Model selection of clusters annotation
    '''

    def __init__(self,
                 keyphrase_curation_file: KeyphraseCurationFile = None,
                 cluster_ids_length=33):

        self.cluster_ids_length = cluster_ids_length
        self.annotations_not_saved = {}
        self.keyphrase_curation_file = keyphrase_curation_file
        self.cluster_selection = [0] * self.cluster_ids_length

        self.load_annotations_from_file()

    def get_cluster_selection(self):
        result = {}
        for i in range(len(self.cluster_selection)):
            result[str(i+1)] = str(self.cluster_selection[i])
        return result

    def add_annotation_not_saved(self, cluster_id, selection):
        self.annotations_not_saved[cluster_id] = selection

    def load_annotations_from_file(self):
        annotations = self.keyphrase_curation_file.get_annotations_from_json(
            annotation_task=AnnotationTask.CLUSTER_SELECTION)
        for cluster_id in annotations:
            selected = annotations[cluster_id]
            self.cluster_selection[int(cluster_id)-1] = selected
        return annotations

    def save(self):
        return self.keyphrase_curation_file.save_annotations_to_json(
            self.annotations_not_saved,
            annotation_task=AnnotationTask.CLUSTER_SELECTION)

    def select_cluster(self, cluster_id, selection):
        self.cluster_selection[cluster_id-1] = selection
        self.add_annotation_not_saved(cluster_id, selection)


class KeyphraseSelectionAnnotation:
    '''
    Model annotation of keyphrase selection in clusters
    '''

    def __init__(self,
                 keyphrase_curation_file: KeyphraseCurationFile = None,
                 cluster_ids_length=33):

        self.cluster_ids_length = cluster_ids_length
        self.annotations_not_saved = {}
        self.keyphrase_curation_file = keyphrase_curation_file
        self.keyphrases_selection = {}

        self.load_annotations_from_file()

    def get_keyphrases_selection(self):
        return self.keyphrases_selection

    def get_curated_keyphrases(self):
        curated_keyphrases = {}
        for cluster_id in self.keyphrases_selection:
            curated_keyphrases[cluster_id] = {
                'keyphrase1': self.keyphrases_selection[cluster_id]['keyphrase1'],
                'keyphrase2': self.keyphrases_selection[cluster_id]['keyphrase2']
            }
        return curated_keyphrases

    def load_annotations_from_file(self):
        annotations = self.keyphrase_curation_file.get_annotations_from_json(
            annotation_task=AnnotationTask.KEYPHRASE_SELECTION)
        for cluster_id in annotations:
            self.keyphrases_selection[cluster_id] = annotations[cluster_id]
        return annotations

    def save(self):
        return self.keyphrase_curation_file.save_annotations_to_json(
            self.annotations_not_saved,
            annotation_task=AnnotationTask.KEYPHRASE_SELECTION)

    def add_annotation_not_saved(self, cluster_id, selected_keyphrases):
        self.annotations_not_saved[cluster_id] = selected_keyphrases
        return True

    def select_keyphrase(self, cluster_id, order, keyphrase_id):
        cluster_id = str(cluster_id)
        selected_keyphrases = self.keyphrases_selection.get(cluster_id, {})
        if order == 1:
            if cluster_id in self.keyphrases_selection:
                self.keyphrases_selection[cluster_id]['selected1'] = \
                    keyphrase_id
                selected_keyphrases['selected1'] = keyphrase_id
        elif order == 2:
            if cluster_id in self.keyphrases_selection:
                if self.keyphrases_selection[cluster_id]['selected1'] != 0:
                    self.keyphrases_selection[cluster_id]['selected2'] = \
                        keyphrase_id
                    selected_keyphrases['selected2'] = keyphrase_id
                else:
                    raise ValueError(
                        'Error: second keyphrase '
                        'with no first keyphrase selected')
        else:
            raise ValueError(f'Unknown order: {order}')
        self.add_annotation_not_saved(cluster_id, selected_keyphrases)


class KeyphraseAliasAnnotation:
    '''
    Model annotation of keyphrase alias
    '''

    def __init__(self,
                 keyphrase_curation_file: KeyphraseCurationFile = None,
                 cluster_ids_length=33):

        self.cluster_ids_length = cluster_ids_length
        self.annotations_not_saved = {}
        self.keyphrase_curation_file = keyphrase_curation_file
        self.keyphrase_aliases = {}

        self.load_annotations_from_file()

    def load_annotations_from_file(self):
        annotations = self.keyphrase_curation_file.get_annotations_from_json(
            annotation_task=AnnotationTask.KEYPHRASE_ALIAS)
        for cluster_id in annotations:
            self.keyphrase_aliases[cluster_id] = annotations[cluster_id]
        return annotations

    def get_keyphrase_aliases(self):
        return self.keyphrase_aliases

    def save(self):
        return self.keyphrase_curation_file.save_annotations_to_json(
            self.annotations_not_saved,
            annotation_task=AnnotationTask.KEYPHRASE_ALIAS)

    def add_annotation_not_saved(self, cluster_id, alias):
        self.annotations_not_saved[cluster_id] = alias
        return True

    def set_alias(self, cluster_id, alias):
        self.keyphrase_aliases[cluster_id] = alias
        self.add_annotation_not_saved(cluster_id, alias)
        return True


class AdjudicatorAnnotation():
    '''
    Model annotation of adjudicator decisions.

    A decision is persisted as a KEYPHRASE_CLUSTERING move in the
    adjudicator's own annotation file:
    - consent:  keyphrase moves INTO the adjudicator's cluster
    - reject:   keyphrase moves OUT of the adjudicator's cluster
                (to the "thrash" cluster, i.e. cluster_ids_length)
    '''

    def __init__(self,
                 keyphrase_curation_file: KeyphraseCurationFile = None,
                 cluster_ids_length=33):

        self.cluster_ids_length = cluster_ids_length
        self.annotations_not_saved = {}
        self.keyphrase_curation_file = keyphrase_curation_file

        self.load_annotations_from_file()

    def load_annotations_from_file(self):
        annotations = self.keyphrase_curation_file.get_annotations_from_json(
            annotation_task=AnnotationTask.KEYPHRASE_CLUSTERING)
        return annotations

    def get_adjudicator_clusters(self):
        '''Returns {cluster_id: [keyphrase_id, ...]} from the file'''
        data = self.keyphrase_curation_file.get_data_from_json(
            check_consistency=False)
        clusters = {}
        for cluster_id in data['clusters']:
            clusters[str(cluster_id)] = \
                list(data['clusters'][cluster_id]['keyphrases'])
        return clusters

    def save(self):
        return self.keyphrase_curation_file.save_annotations_to_json(
            self.annotations_not_saved,
            annotation_task=AnnotationTask.KEYPHRASE_CLUSTERING)

    def adjudicate(self, cluster_id, keyphrase_id, action):
        '''Registers an adjudicator decision (consent or reject)

        Args:
            cluster_id (int): cluster id
            keyphrase_id (int): keyphrase id
            action (str): 'consent' or 'reject'
        '''
        if action not in ('consent', 'reject'):
            raise ValueError(f'Unknown action: {action}')
        # annotations_not_saved: {keyphrase_id: target_cluster_id}
        # keyphrase ids must be ints, as stored in the annotation file
        if action == 'consent':
            self.annotations_not_saved[int(keyphrase_id)] = int(cluster_id)
        else:
            # thrash cluster: id = cluster_ids_length (last one)
            self.annotations_not_saved[int(keyphrase_id)] = \
                int(self.cluster_ids_length)
        return True
