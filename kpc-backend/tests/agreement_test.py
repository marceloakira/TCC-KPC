import json
import os
import tempfile
import unittest
from unittest import mock

from keyphrase_curation.util.agreement import \
    _nltk_agreement, align_clusters, cf_agreement, cluster_sets, \
    kc_agreement, kc_metrics, ks_agreement

CLUSTER_IDS_LENGTH = 33


def load_fixture():
    filepath = os.path.join(
        os.getcwd(), 'tests', 'fixtures', 'agreement_table3.json')
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)


def make_data(clusters, n_keyphrases):
    '''Annotation data with clusters {cluster_id: [keyphrase ids]}'''
    return {
        'keyphrases': {
            str(i): {'keyphrase': f'keyphrase {i}'}
            for i in range(1, n_keyphrases + 1)},
        'clusters': {
            str(cluster_id): {
                'keyphrases': clusters.get(cluster_id, []),
                'selected': 0,
                'keyphrase1_selected': 0,
                'keyphrase2_selected': 0,
                'alias': ''}
            for cluster_id in range(1, CLUSTER_IDS_LENGTH + 1)},
    }


# Same 7 keyphrases grouped alike, with different cluster numbers
CLUSTERS1 = {1: [1, 2, 3], 2: [4, 5], 3: [6], 33: [7]}
CLUSTERS2 = {5: [1, 2, 3], 9: [4, 5], 2: [6], 33: [7]}


class TestTable3(unittest.TestCase):
    '''Table 3 of the article (akira x alexandre), as in the notebooks'''

    expected = {
        'death_penalty': {
            'ari': 0.34, 'ami': 0.50, 'fms': 0.38, 'cf': 0.38, 'ks': 0.63},
        'marijuana_legalization': {
            'ari': 0.39, 'ami': 0.51, 'fms': 0.41, 'cf': 0.26, 'ks': 0.65},
    }

    def setUp(self):
        self.fixture = load_fixture()

    def test_keyphrase_clustering(self):
        for topic, expected in self.expected.items():
            labels = self.fixture[topic]['kc_labels']
            metrics = kc_metrics(labels['akira'], labels['alexandre'])
            for metric in ('ari', 'ami', 'fms'):
                self.assertEqual(
                    round(metrics[metric], 2), expected[metric],
                    f'{topic} {metric}')

    def test_cluster_filtering_and_keyphrase_selection(self):
        for topic, expected in self.expected.items():
            akira, alexandre = (
                {'clusters': self.fixture[topic]['clusters'][user]}
                for user in ('akira', 'alexandre'))
            mapping = align_clusters(
                cluster_sets(akira, CLUSTER_IDS_LENGTH),
                cluster_sets(alexandre, CLUSTER_IDS_LENGTH),
                CLUSTER_IDS_LENGTH)
            self.assertEqual(
                round(cf_agreement(akira, alexandre, mapping), 2),
                expected['cf'], topic)
            self.assertEqual(
                round(ks_agreement(akira, alexandre, mapping), 2),
                expected['ks'], topic)

    def test_article_examples(self):
        # the article truncates these values to -0.09 and 0.43
        cf = _nltk_agreement(
            [frozenset('ab'), frozenset('c'), frozenset('def')],
            [frozenset('cf'), frozenset('bd'), frozenset('g')], 'alpha')
        ks = _nltk_agreement(
            [frozenset('ag'), frozenset('di'), frozenset('l')],
            [frozenset('g'), frozenset('di'), frozenset('j')], 'multi_kappa')
        self.assertAlmostEqual(cf, -0.0976, places=4)
        self.assertAlmostEqual(ks, 0.4375, places=4)


class TestAlignment(unittest.TestCase):

    def test_renumbered_clusters_are_matched(self):
        result = kc_agreement(
            make_data(CLUSTERS1, 7), make_data(CLUSTERS2, 7),
            CLUSTER_IDS_LENGTH)
        self.assertEqual(result['mapping'][5], 1)
        self.assertEqual(result['mapping'][9], 2)
        self.assertEqual(result['mapping'][2], 3)
        self.assertEqual(result['mapping'][33], 33)
        self.assertEqual(result['convergent'], 7)
        self.assertEqual(result['mean_matched_jaccard'], 1.0)
        self.assertAlmostEqual(result['kc']['ari'], 1.0)

    def test_aligned_files_keep_numbering(self):
        result = kc_agreement(
            make_data(CLUSTERS1, 7), make_data(CLUSTERS1, 7),
            CLUSTER_IDS_LENGTH)
        self.assertTrue(
            all(id2 == id1 for id2, id1 in result['mapping'].items()))

    def test_empty_clusters(self):
        # blank annotation: every cluster is empty
        result = kc_agreement(
            make_data({}, 7), make_data({}, 7), CLUSTER_IDS_LENGTH)
        self.assertFalse(result['complete'])
        self.assertEqual(result['not_clustered'], [7, 7])
        self.assertIsNone(result['kc'])
        self.assertIsNone(result['mean_matched_jaccard'])

    def test_incomplete_annotation(self):
        result = kc_agreement(
            make_data(CLUSTERS1, 7), make_data({1: [1, 2]}, 7),
            CLUSTER_IDS_LENGTH)
        self.assertFalse(result['complete'])
        self.assertEqual(result['not_clustered'], [0, 5])
        self.assertIsNone(result['kc'])

    def test_different_keyphrases(self):
        with self.assertRaises(ValueError):
            kc_agreement(
                make_data(CLUSTERS1, 7), make_data(CLUSTERS1, 8),
                CLUSTER_IDS_LENGTH)

    def test_no_variation_is_undefined(self):
        # nobody selected any cluster: NLTK would return a vacuous 1
        data = make_data(CLUSTERS1, 7)
        mapping = {i: i for i in range(1, CLUSTER_IDS_LENGTH + 1)}
        self.assertIsNone(cf_agreement(data, data, mapping))


class TestAdjudicatorData(unittest.TestCase):
    '''GET /topic/adjudicator_data renumbers annotator 2 and sends agreement'''

    def adjudicator_clusters_data(self, annotator1, annotator2):
        from keyphrase_curation.api import topic as topic_api

        with tempfile.TemporaryDirectory() as tmp:
            files = {
                'annotator1.json': annotator1,
                'annotator2.json': annotator2,
                'adjudicator.json': make_data({}, 7),
            }
            for filename, data in files.items():
                with open(os.path.join(tmp, filename), 'w') as f:
                    json.dump(data, f)

            uac = mock.Mock()
            uac.get_annotation_files.return_value = {
                'sources': ['annotator1.kpc', 'annotator2.kpc']}
            uac.get_annotation_filepaths.return_value = {
                'target': os.path.join(tmp, 'adjudicator.kpc')}
            with mock.patch.object(
                    topic_api, 'UserAttributionController',
                    return_value=uac), \
                    mock.patch.dict(topic_api.config, {'dataset_path': tmp}):
                return topic_api._get_adjudicator_clusters_data(
                    'adjudicator', 'topic')

    def test_renumbers_annotator2_and_sends_agreement(self):
        result = self.adjudicator_clusters_data(
            make_data(CLUSTERS1, 7), make_data(CLUSTERS2, 7))
        for cluster_id in ('1', '2', '3', '33'):
            self.assertEqual(
                result['annotator2'][cluster_id][1],
                result['annotator1'][cluster_id][1])
        self.assertEqual(result['annotator2']['5'][1], [])
        agreement = result['agreement']
        self.assertTrue(agreement['complete'])
        self.assertEqual(agreement['convergent'], 7)
        self.assertEqual(
            agreement['kc'], {'ari': 1.0, 'ami': 1.0, 'fms': 1.0})
        self.assertEqual(
            agreement['reference'], {'ari': 0.36, 'ami': 0.50, 'fms': 0.39})

    def test_different_keyphrases_keep_screen_working(self):
        annotator2 = make_data(CLUSTERS2, 7)
        annotator2['keyphrases']['7']['keyphrase'] = 'another keyphrase'
        result = self.adjudicator_clusters_data(
            make_data(CLUSTERS1, 7), annotator2)
        self.assertIsNone(result['agreement'])
        self.assertEqual(
            result['annotator2']['5'][1],
            ['keyphrase 1(1)', 'keyphrase 2(2)', 'keyphrase 3(3)'])


if __name__ == '__main__':
    unittest.main()
