from keyphrase_curation.model.annotation import (
    ClusterAnnotation, KeyphraseCurationFile,
    ClusterSelectionAnnotation, KeyphraseSelectionAnnotation, 
    KeyphraseAliasAnnotation, AdjudicatorAnnotation)
from keyphrase_curation.controller.user_attribution import \
    UserAttributionController
from keyphrase_curation import config
from keyphrase_curation.model.annotation import AnnotationTask
from keyphrase_curation.model.cluster import ClusterSorting
from keyphrase_curation.model.keyphrase import KeyphraseSorting


class AnnotationController:
    def __init__(self, topic: str, annotator: str):
        self.filepaths = \
            UserAttributionController().get_annotation_filepaths(
                annotator, topic)
        self.keyphrase_curation_file = \
            KeyphraseCurationFile(self.filepaths['target'])
        self.cluster_annotation: ClusterAnnotation = ClusterAnnotation(
            topic=topic,
            embeddings_path=config['embeddings_path'],
            keyphrase_curation_file=self.keyphrase_curation_file,
            cluster_ids_length=config['cluster_ids_length'])
        self.cluster_selection_annotation = ClusterSelectionAnnotation(
            keyphrase_curation_file=self.keyphrase_curation_file,
            cluster_ids_length=config['cluster_ids_length'])
        self.keyphrase_selection_annotation = KeyphraseSelectionAnnotation(
            keyphrase_curation_file=self.keyphrase_curation_file,
            cluster_ids_length=config['cluster_ids_length'])
        self.keyphrase_alias_annotation = KeyphraseAliasAnnotation(
            keyphrase_curation_file=self.keyphrase_curation_file,
            cluster_ids_length=config['cluster_ids_length'])
        self.adjudicator_annotation = AdjudicatorAnnotation(
            keyphrase_curation_file=self.keyphrase_curation_file,
            cluster_ids_length=config['cluster_ids_length'])

    def get_keyphrase_clustering(
            self,
            sort_by: KeyphraseSorting = KeyphraseSorting.ALPHABETICAL):
        keyphrase_descriptions = self.cluster_annotation.\
            get_keyphrase_descriptions(sort_by)
        keyphrase_clustering = {}
        for keyphrase_id in keyphrase_descriptions:
            keyphrase_clustering[keyphrase_id] = {
                "description": keyphrase_descriptions[keyphrase_id],
                "clustering": self.cluster_annotation.clustering[keyphrase_id-1]
            }
        return keyphrase_clustering

    def get_cluster_selection(self):
        return self.cluster_selection_annotation.get_cluster_selection()

    def get_keyphrases_selection(self):
        return self.keyphrase_selection_annotation.get_keyphrases_selection()

    def get_keyphrases_aliases(self):
        return self.keyphrase_alias_annotation.get_keyphrase_aliases()

    def get_curated_keyphrases(self):
        return self.keyphrase_selection_annotation.get_curated_keyphrases()

    def get_clusters(
            self,
            sort_by: ClusterSorting = ClusterSorting.NUMERICAL):
        clusters = {}
        clusters_meta_info = {}
        total_cohesion = 0
        total_average_similarity = 0
        cluster_objects, clusters_meta_info = \
            self.cluster_annotation.get_clusters(sort_by=sort_by)
        for cluster in cluster_objects:
            descriptions = \
                cluster.get_descriptions(KeyphraseSorting.ALPHABETICAL)
            if sort_by.name == ClusterSorting.NUMERICAL.name:
                descriptions = \
                    cluster.get_descriptions(KeyphraseSorting.NUMERICAL)
                alias = f"Cluster {cluster.get_alias()}"
            elif sort_by.name == ClusterSorting.CLUSTER_COHESION.name:
                cohesion = cluster.get_cohesion()
                alias = \
                    f"Cluster {cluster.get_alias()}" \
                    f" - cohesion: {cohesion:.2f}"
                total_cohesion += cohesion
            elif sort_by.name == ClusterSorting.PAIRWISE_SIMILARITY.name:
                similar_cluster = \
                    clusters_meta_info[cluster.id]['similar_cluster']
                similarity = clusters_meta_info[cluster.id]['similarity']
                if similarity == 0:
                    alias = f"Cluster {cluster.get_alias()} - not paired"
                else:
                    alias = \
                        f"Cluster {cluster.get_alias()}" \
                        f" - similar to: {similar_cluster} "\
                        f"- similarity: {similarity:.2f}"
            elif sort_by.name == ClusterSorting.CENTROID_SIMILARITY.name:
                descriptions = \
                    cluster.get_descriptions(
                        ClusterSorting.CENTROID_SIMILARITY)
                cluster_centroid = \
                    clusters_meta_info[cluster.id]['cluster_centroid']
                average_similarity = \
                    clusters_meta_info[
                        cluster.id]['average_similarity_from_centroid']
                alias = \
                    f"Cluster {cluster.get_alias()}" \
                    f" - cluster centroid: {cluster_centroid}"\
                    f" - average similarity: {average_similarity:.2f}"
                total_average_similarity += average_similarity
            clusters[cluster.id] = (alias, descriptions)
        if sort_by.name == ClusterSorting.CLUSTER_COHESION.name:
            clusters_meta_info['average_cohesion'] = \
                total_cohesion/len(clusters)
        elif sort_by.name == ClusterSorting.CENTROID_SIMILARITY.name:
            clusters_meta_info['average_centroid_similarity'] = \
                total_average_similarity/len(clusters)
        return (clusters, clusters_meta_info)

    def move_to_cluster(self, keyphrase_id, cluster_id):
        self.cluster_annotation.move_to_cluster(keyphrase_id, cluster_id)

    def select_cluster(self, cluster_id, selected):
        self.cluster_selection_annotation.select_cluster(cluster_id, selected)

    def select_keyphrase(self, cluster_id, order, keyphrase_id):
        self.keyphrase_selection_annotation.select_keyphrase(
            cluster_id, order, keyphrase_id)

    def set_alias(self, cluster_id, alias):
        self.keyphrase_alias_annotation.set_alias(cluster_id, alias)

    def get_adjudicator_clusters(self):
        return self.adjudicator_annotation.get_adjudicator_clusters()

    def adjudicate(self, cluster_id, keyphrase_id, action):
        self.adjudicator_annotation.adjudicate(
            cluster_id, keyphrase_id, action)

    def save_adjudication(self):
        return self.adjudicator_annotation.save()

    def save(self, task):
        if task == AnnotationTask.KEYPHRASE_CLUSTERING:
            return self.cluster_annotation.save()
        elif task == AnnotationTask.CLUSTER_SELECTION:
            return self.cluster_selection_annotation.save()
        elif task == AnnotationTask.KEYPHRASE_SELECTION:
            return self.keyphrase_selection_annotation.save()
        elif task == AnnotationTask.KEYPHRASE_ALIAS:
            return self.keyphrase_alias_annotation.save()
        else:
            raise Exception("Invalid task")
