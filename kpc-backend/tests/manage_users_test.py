import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from keyphrase_curation.model.user_attribution import UserAttribution

CLUSTER_IDS_LENGTH = 33
SCRIPT_PATH = Path(os.getcwd()) / 'scripts' / 'manage_users.py'

spec = importlib.util.spec_from_file_location('manage_users', SCRIPT_PATH)
manage_users = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage_users)


def write_dataset(dataset_path):
    '''Two topics with embeddings (both TSV header spellings) and one
    without embeddings'''
    collected = dataset_path / 'keyphrases' / 'collected'
    embeddings = dataset_path / 'keyphrases' / 'embeddings'
    collected.mkdir(parents=True)
    embeddings.mkdir(parents=True)
    (collected / 'topic_a.tsv').write_bytes(
        b'collected_from\tkeyphrase\r\n'
        b'chatgpt_pro\tFirst keyphrase\r\n'
        b'chatgpt_con\tSecond keyphrase\r\n')
    (collected / 'topic_b.tsv').write_bytes(
        b'id\tcolected_from\tkeyphrase\r\n'
        b'1\tchatgpt_pro\tAnother one\r\n')
    (collected / 'topic_c.tsv').write_bytes(
        b'collected_from\tkeyphrase\r\nchatgpt_pro\tNo embeddings\r\n')
    for topic in ('topic_a', 'topic_b'):
        (embeddings / f'{topic}.pkl').write_bytes(b'')


class TestManageUsers(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dataset_path = Path(self.tmp.name)
        self.attributions_filepath = self.dataset_path / 'attributions.toml'
        write_dataset(self.dataset_path)

    def tearDown(self):
        self.tmp.cleanup()

    def attributions(self):
        return manage_users.Attributions(
            self.dataset_path, self.attributions_filepath,
            CLUSTER_IDS_LENGTH)

    def add_annotator(self, user, topics, password='first-password'):
        attributions = self.attributions()
        attributions.add_user(user, password)
        for topic in topics:
            attributions.create_blank_file(attributions.assign(user, topic))
        attributions.save()

    def test_add_user_with_topics(self):
        self.add_annotator('maria', ['topic_a', 'topic_b'])

        # the backend reads the new attributions
        model = UserAttribution(str(self.attributions_filepath))
        self.assertEqual(model.get_topics('maria'), ['topic_a', 'topic_b'])
        self.assertEqual(model.get_annotation_profile('maria', 'topic_a'),
                         'annotator')
        self.assertEqual(
            model.get_annotation_files('maria', 'topic_a')['target'],
            'annotations/maria/topic_a.kpc')
        self.assertTrue(model.validate_password('maria', 'first-password'))
        self.assertFalse(model.validate_password('maria', 'wrong-password'))

        with open(self.dataset_path / 'annotations/maria/topic_a.json') as f:
            data = json.load(f)
        self.assertEqual(data['keyphrases'], {
            '1': {'keyphrase': 'First keyphrase',
                  'collected_from': 'chatgpt_pro'},
            '2': {'keyphrase': 'Second keyphrase',
                  'collected_from': 'chatgpt_con'}})
        self.assertEqual(len(data['clusters']), CLUSTER_IDS_LENGTH)
        self.assertTrue(all(
            cluster['keyphrases'] == [] for cluster in
            data['clusters'].values()))

        with open(self.dataset_path / 'annotations/maria/topic_b.json') as f:
            data = json.load(f)
        self.assertEqual(data['keyphrases']['1']['collected_from'],
                         'chatgpt_pro')

    def test_invalid_commands_change_nothing(self):
        self.add_annotator('maria', ['topic_a'])
        before = self.attributions_filepath.read_bytes()
        attributions = self.attributions()
        invalid = [
            lambda: attributions.add_user('maria', 'other-password'),
            lambda: attributions.add_user('Maria Silva', 'other-password'),
            lambda: attributions.assign('maria', 'topic_a'),
            lambda: attributions.assign('maria', 'topic_c'),
            lambda: attributions.assign('maria', 'unknown_topic'),
            lambda: attributions.assign('nobody', 'topic_b'),
        ]
        for command in invalid:
            with self.assertRaises(manage_users.ManageUsersError):
                command()
        self.assertEqual(self.attributions_filepath.read_bytes(), before)

    def test_adjudicator(self):
        self.add_annotator('maria', ['topic_a'])
        self.add_annotator('joao', ['topic_a'])
        attributions = self.attributions()
        attributions.add_user('ana', 'adjudicator-password')
        with self.assertRaises(manage_users.ManageUsersError):
            # ana does not annotate topic_a
            attributions.assign_adjudicator('ana', 'topic_a', ['maria', 'ana'])
        target = attributions.assign_adjudicator(
            'ana', 'topic_a', ['maria', 'joao'])
        attributions.create_blank_file(target)
        attributions.save()

        model = UserAttribution(str(self.attributions_filepath))
        self.assertEqual(model.get_annotation_profile('ana', 'topic_a'),
                         'adjudicator')
        self.assertEqual(
            model.get_annotation_files('ana', 'topic_a')['sources'],
            ['annotations/maria/topic_a.kpc', 'annotations/joao/topic_a.kpc'])
        self.assertTrue(
            (self.dataset_path / 'annotations/ana/topic_a.json').exists())

    def test_set_password(self):
        self.add_annotator('maria', ['topic_a'])
        self.add_annotator('joao', ['topic_a'], password='joao-password')
        attributions = self.attributions()
        attributions.set_password('maria', 'second-password')
        attributions.save()

        model = UserAttribution(str(self.attributions_filepath))
        self.assertTrue(model.validate_password('maria', 'second-password'))
        self.assertFalse(model.validate_password('maria', 'first-password'))
        self.assertTrue(model.validate_password('joao', 'joao-password'))

    def test_existing_annotation_is_kept(self):
        annotation = self.dataset_path / 'annotations/maria/topic_a.json'
        annotation.parent.mkdir(parents=True)
        annotation.write_text('{"keep": true}')
        self.add_annotator('maria', ['topic_a'])
        self.assertEqual(annotation.read_text(), '{"keep": true}')

    def test_keeps_existing_content_and_line_endings(self):
        existing = (
            b'[admin] # admin profile\r\n'
            b'password = "hash"\r\n')
        self.attributions_filepath.write_bytes(existing)
        self.add_annotator('maria', ['topic_a'])
        content = self.attributions_filepath.read_bytes()
        self.assertTrue(content.startswith(existing))
        self.assertNotIn(b'\n', content.replace(b'\r\n', b''))

    def test_blank_file_matches_existing_annotations(self):
        # same keyphrases as the annotation files of the dataset
        dataset_path = Path(os.getcwd()) / 'dataset'
        existing = dataset_path / 'annotations/akira/death_penalty.json'
        if not existing.exists():
            self.skipTest('dataset not available')
        blank = manage_users.blank_annotation(
            dataset_path / 'keyphrases/collected/death_penalty.tsv',
            CLUSTER_IDS_LENGTH)
        with open(existing) as f:
            data = json.load(f)
        self.assertEqual(blank['keyphrases'], data['keyphrases'])
        self.assertEqual(blank['clusters'].keys(), data['clusters'].keys())


if __name__ == '__main__':
    unittest.main()
