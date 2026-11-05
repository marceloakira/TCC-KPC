'''
Cadastro de usuários e atribuições (dataset/attributions.toml)

Cria usuários, atribui tópicos e cria os arquivos de anotação em branco
(dataset/annotations/<usuário>/<tópico>.json) a partir das keyphrases
coletadas (dataset/keyphrases/collected/<tópico>.tsv). As senhas são
gravadas como hash bcrypt e nunca são exibidas; a exceção é a senha gerada
com --generate, mostrada uma única vez.

O arquivo de atribuições só recebe tabelas novas no final (ou a troca da
linha de senha), então o conteúdo existente é mantido como está. Arquivos
de anotação que já existem nunca são sobrescritos.

Uso (de kpc-backend, com src no PYTHONPATH):
    python scripts/manage_users.py add maria --topics death_penalty gun_control
    python scripts/manage_users.py add joao --generate --topics death_penalty
    python scripts/manage_users.py assign maria marijuana_legalization
    python scripts/manage_users.py adjudicator ana death_penalty \
        --annotators maria joao
    python scripts/manage_users.py password maria
    python scripts/manage_users.py list

No servidor (deploy/README.md):
    docker compose exec backend python scripts/manage_users.py list
'''
import argparse
import csv
import getpass
import json
import logging
import os
import re
import secrets
import sys
from pathlib import Path

import tomli

from keyphrase_curation import config
from keyphrase_curation.util.security import \
    get_password_hash, verify_password

# passlib 1.7.4 warns (with a traceback) that it cannot read the version
# of bcrypt 4; hashing works
logging.getLogger('passlib').setLevel(logging.ERROR)

USERNAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]{2,31}$')
TOPIC_PATTERN = re.compile(r'^[a-z0-9_]+$')
TABLE_HEADER_PATTERN = re.compile(r'^\s*\[\s*([^\]\s]+)\s*\]')
PASSWORD_LINE_PATTERN = re.compile(r'^\s*password\s*=')
MIN_PASSWORD_LENGTH = 8


class ManageUsersError(Exception):
    '''Invalid command: nothing is changed'''


def blank_annotation(collected_filepath, cluster_ids_length):
    '''Annotation data with every keyphrase of the topic and empty clusters,
    in the format of dataset/annotations/<user>/<topic>.json'''
    with open(collected_filepath, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    # keyphrase ids follow the order of the rows, as in the existing files
    keyphrases = {
        str(keyphrase_id): {
            'keyphrase': row['keyphrase'],
            # some files spell the column "colected_from"
            'collected_from':
                row.get('collected_from', row.get('colected_from', '')),
        }
        for keyphrase_id, row in enumerate(rows, 1)
    }
    clusters = {
        str(cluster_id): {
            'keyphrases': [],
            'selected': 0,
            'keyphrase1_selected': 0,
            'keyphrase2_selected': 0,
            'alias': '',
        }
        for cluster_id in range(1, cluster_ids_length + 1)
    }
    return {'keyphrases': keyphrases, 'clusters': clusters}


class Attributions:
    '''The attributions file and the annotation files of the dataset'''

    def __init__(self, dataset_path, attributions_filepath,
                 cluster_ids_length):
        self.dataset_path = Path(dataset_path)
        self.filepath = Path(attributions_filepath)
        self.cluster_ids_length = cluster_ids_length
        self.text = ''
        if self.filepath.exists():
            # newline='' keeps the line endings of the file
            with open(self.filepath, encoding='utf-8', newline='') as f:
                self.text = f.read()
        self.newline = '\r\n' if '\r\n' in self.text else '\n'
        self.data = self._parse(self.text)

    @staticmethod
    def _parse(text):
        try:
            return tomli.loads(text)
        except tomli.TOMLDecodeError as e:
            raise ManageUsersError(f'arquivo de atribuições inválido: {e}')

    # queries

    def users(self):
        return sorted(self.data)

    def attributions(self, user):
        return self.data.get(user, {}).get('attributions', {})

    def collected_filepath(self, topic):
        return self.dataset_path / 'keyphrases' / 'collected' / f'{topic}.tsv'

    def embeddings_filepath(self, topic):
        return self.dataset_path / 'keyphrases' / 'embeddings' / f'{topic}.pkl'

    def json_filepath(self, target):
        return (self.dataset_path / target).with_suffix('.json')

    def available_topics(self):
        collected_path = self.dataset_path / 'keyphrases' / 'collected'
        return sorted(path.stem for path in collected_path.glob('*.tsv'))

    # checks

    def check_new_user(self, user):
        if not USERNAME_PATTERN.match(user):
            raise ManageUsersError(
                f'nome de usuário inválido: {user} (use de 3 a 32 letras '
                'minúsculas, números, "_" ou "-")')
        if user in self.data:
            raise ManageUsersError(f'o usuário {user} já existe')

    def check_user(self, user):
        if user not in self.data:
            raise ManageUsersError(f'o usuário {user} não existe')

    def check_topic(self, user, topic):
        if not TOPIC_PATTERN.match(topic) \
                or not self.collected_filepath(topic).exists():
            raise ManageUsersError(
                f'tópico desconhecido: {topic} (tópicos com keyphrases '
                f'coletadas: {", ".join(self.available_topics())})')
        if not self.embeddings_filepath(topic).exists():
            raise ManageUsersError(
                f'o tópico {topic} não tem embeddings '
                f'({self.embeddings_filepath(topic)}); sem eles a tela de '
                'agrupamento não abre')
        if topic in self.attributions(user):
            raise ManageUsersError(
                f'o tópico {topic} já está atribuído a {user}')

    # changes

    def _append(self, block):
        text = self.text
        if text and not text.endswith('\n'):
            text += self.newline
        if text:
            text += self.newline
        text += block.replace('\n', self.newline)
        self.data = self._parse(text)
        self.text = text

    def add_user(self, user, password):
        self.check_new_user(user)
        self._append(
            f'[{user}]\n'
            f'password = "{get_password_hash(password)}"\n'
            f'\n'
            f'[{user}.attributions]\n')

    def assign(self, user, topic):
        '''Attributes the topic to the user, as annotator'''
        self.check_user(user)
        self.check_topic(user, topic)
        target = f'annotations/{user}/{topic}.kpc'
        source = f'keyphrases/collected/{topic}.tsv'
        self._append(
            f'[{user}.attributions.{topic}]\n'
            f'profile = "annotator"\n'
            f'annotation_files.source = "{source}"\n'
            f'annotation_files.target = "{target}"\n'
            f'annotation_status = "assigned"\n'
            f'annotation_task = "keyphrase_clustering"\n')
        return target

    def assign_adjudicator(self, user, topic, annotators):
        '''Attributes the topic to the user, as adjudicator of the two
        annotators'''
        self.check_user(user)
        self.check_topic(user, topic)
        if len(set(annotators)) != 2 or user in annotators:
            raise ManageUsersError(
                'informe dois anotadores diferentes do adjudicador')
        sources = []
        for annotator in annotators:
            attribution = self.attributions(annotator).get(topic, {})
            if attribution.get('profile') != 'annotator':
                raise ManageUsersError(
                    f'{annotator} não é anotador do tópico {topic}')
            sources.append(attribution['annotation_files']['target'])
        target = f'annotations/{user}/{topic}.kpc'
        sources_list = ', '.join(f'"{source}"' for source in sources)
        self._append(
            f'[{user}.attributions.{topic}]\n'
            f'profile = "adjudicator"\n'
            f'annotation_files.sources = [{sources_list}]\n'
            f'annotation_files.target = "{target}"\n'
            f'annotation_status = "assigned"\n'
            f'annotation_task = "keyphrase_clustering"\n')
        return target

    def set_password(self, user, password):
        '''Replaces the password line in the table of the user'''
        self.check_user(user)
        lines = self.text.splitlines(keepends=True)
        table = None
        replaced = 0
        for i, line in enumerate(lines):
            header = TABLE_HEADER_PATTERN.match(line)
            if header:
                table = header.group(1)
            elif table == user and PASSWORD_LINE_PATTERN.match(line):
                ending = line[len(line.rstrip('\r\n')):] or self.newline
                lines[i] = \
                    f'password = "{get_password_hash(password)}"{ending}'
                replaced += 1
        if replaced != 1:
            raise ManageUsersError(
                f'linha de senha de {user} não encontrada no arquivo')
        text = ''.join(lines)
        data = self._parse(text)
        if not verify_password(password, data[user]['password']):
            raise ManageUsersError('a troca de senha falhou')
        self.text, self.data = text, data

    def create_blank_file(self, target):
        '''Creates the blank annotation file of the target, if it does not
        exist; returns True if it was created'''
        json_filepath = self.json_filepath(target)
        if json_filepath.exists():
            return False
        topic = json_filepath.stem
        data = blank_annotation(
            self.collected_filepath(topic), self.cluster_ids_length)
        json_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(json_filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return True

    def save(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp_filepath = self.filepath.with_name(self.filepath.name + '.tmp')
        with open(tmp_filepath, 'w', encoding='utf-8', newline='') as f:
            f.write(self.text)
        # the backend reads the file on every request: swap it in one step
        os.replace(tmp_filepath, self.filepath)


def read_password(generate):
    '''(password, generated)'''
    if generate:
        return secrets.token_urlsafe(12), True
    password = getpass.getpass('Senha: ')
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ManageUsersError(
            f'a senha deve ter pelo menos {MIN_PASSWORD_LENGTH} caracteres')
    if getpass.getpass('Repita a senha: ') != password:
        raise ManageUsersError('as senhas não conferem')
    return password, False


def assign_topics(attributions, user, topics):
    targets = []
    for topic in topics:
        targets.append(attributions.assign(user, topic))
    return targets


def report_files(attributions, targets):
    for target in targets:
        created = attributions.create_blank_file(target)
        status = 'criado' if created else 'já existia, mantido'
        print(f'  {attributions.json_filepath(target)}: {status}')


def list_attributions(attributions):
    for user in attributions.users():
        user_attributions = attributions.attributions(user)
        if not user_attributions:
            print(f'{user:<16} (sem tópicos)')
        for topic, attribution in sorted(user_attributions.items()):
            target = attribution.get('annotation_files', {}).get('target')
            file_status = 'arquivo ok' if target and \
                attributions.json_filepath(target).exists() \
                else 'ARQUIVO FALTANDO'
            line = (f'{user:<16} {topic:<24} '
                    f'{attribution.get("profile", "?"):<12} {file_status}')
            sources = attribution.get('annotation_files', {}).get('sources')
            if sources:
                annotators = [Path(source).parent.name for source in sources]
                line += f'  (anotadores: {", ".join(annotators)})'
            print(line)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Cadastro de usuários e atribuições do KPC')
    commands = parser.add_subparsers(dest='command', required=True)

    add = commands.add_parser(
        'add', help='cria um usuário (e atribui tópicos como anotador)')
    add.add_argument('user')
    add.add_argument('--topics', nargs='*', default=[],
                     help='tópicos atribuídos como anotador')
    add.add_argument('--generate', action='store_true',
                     help='gera uma senha aleatória e mostra uma vez')

    assign = commands.add_parser(
        'assign', help='atribui tópicos a um usuário como anotador')
    assign.add_argument('user')
    assign.add_argument('topics', nargs='+')

    adjudicator = commands.add_parser(
        'adjudicator', help='atribui um tópico a um usuário como adjudicador')
    adjudicator.add_argument('user')
    adjudicator.add_argument('topic')
    adjudicator.add_argument('--annotators', nargs=2, required=True,
                             metavar=('ANOTADOR1', 'ANOTADOR2'))

    password = commands.add_parser('password', help='troca a senha')
    password.add_argument('user')
    password.add_argument('--generate', action='store_true',
                          help='gera uma senha aleatória e mostra uma vez')

    commands.add_parser('list', help='lista usuários e atribuições')

    args = parser.parse_args(argv)
    attributions = Attributions(
        config['dataset_path'], config['attributions_filepath'],
        config['cluster_ids_length'])

    try:
        if args.command == 'list':
            list_attributions(attributions)
            return 0

        generated_password = None
        targets = []
        if args.command == 'add':
            attributions.check_new_user(args.user)
            password_value, generated = read_password(args.generate)
            attributions.add_user(args.user, password_value)
            targets = assign_topics(attributions, args.user, args.topics)
            generated_password = password_value if generated else None
        elif args.command == 'assign':
            targets = assign_topics(attributions, args.user, args.topics)
        elif args.command == 'adjudicator':
            targets = [attributions.assign_adjudicator(
                args.user, args.topic, args.annotators)]
        elif args.command == 'password':
            attributions.check_user(args.user)
            password_value, generated = read_password(args.generate)
            attributions.set_password(args.user, password_value)
            generated_password = password_value if generated else None
    except ManageUsersError as e:
        print(f'Erro: {e}. Nada foi alterado.', file=sys.stderr)
        return 1

    # blank files first: a failure here leaves the attributions untouched
    report_files(attributions, targets)
    attributions.save()
    print(f'{attributions.filepath} atualizado ({args.command} {args.user}).')
    if generated_password:
        print(f'Senha gerada para {args.user} (anote; ela não será '
              f'mostrada de novo): {generated_password}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
