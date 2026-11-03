'''
Inter-annotator agreement report (Table 3 of the keyphrase curation article)

For each topic and each pair of annotators, computes the agreement of
Keyphrase Clustering (ARI, AMI, NMI, FMS), Cluster Filtering (Krippendorff's
alpha) and Keyphrase Selection (Fleiss' kappa) and writes a CSV file.
Annotators and their files come from the attributions file (profile
"annotator"). CF and KS are computed over aligned clusters.

Usage (from kpc-backend, with src in PYTHONPATH):
    python scripts/agreement_report.py
    python scripts/agreement_report.py --topics death_penalty \
        --annotators akira victor --out agreement.csv
    python scripts/agreement_report.py --excel   # ';' and decimal comma
'''
import argparse
import csv
import sys
from itertools import combinations

from keyphrase_curation import config
from keyphrase_curation.model.annotation import KeyphraseCurationFile
from keyphrase_curation.model.user_attribution import UserAttribution
from keyphrase_curation.util.agreement import \
    cf_agreement, kc_agreement, ks_agreement

FIELDS = [
    'topic', 'annotator1', 'annotator2', 'n_keyphrases', 'complete',
    'not_clustered1', 'not_clustered2', 'convergent', 'mean_matched_jaccard',
    'kc_ari', 'kc_ami', 'kc_nmi', 'kc_fms',
    'selected_clusters1', 'selected_clusters2', 'cf_alpha', 'ks_kappa',
]


def get_annotation_files(topics=None, annotators=None):
    '''{topic: {annotator: annotation filepath}} from the attributions file'''
    attributions = UserAttribution(
        config['attributions_filepath']).attributions
    files = {}
    for user, user_data in attributions.items():
        if annotators and user not in annotators:
            continue
        for topic, attribution in user_data.get('attributions', {}).items():
            if topics and topic not in topics:
                continue
            if attribution.get('profile') != 'annotator':
                continue
            target = attribution['annotation_files']['target']
            files.setdefault(topic, {})[user] = \
                f"{config['dataset_path']}/{target}"
    return files


def selected_clusters(data):
    return sum(1 for cluster in data['clusters'].values()
               if int(cluster.get('selected', 0)) == 1)


def agreement_row(topic, annotator1, annotator2, data1, data2):
    kc = kc_agreement(data1, data2, config['cluster_ids_length'])
    row = {
        'topic': topic,
        'annotator1': annotator1,
        'annotator2': annotator2,
        'n_keyphrases': kc['n_keyphrases'],
        'complete': kc['complete'],
        'not_clustered1': kc['not_clustered'][0],
        'not_clustered2': kc['not_clustered'][1],
        'convergent': kc['convergent'],
        'mean_matched_jaccard': kc['mean_matched_jaccard'],
        'selected_clusters1': selected_clusters(data1),
        'selected_clusters2': selected_clusters(data2),
    }
    # metrics are only meaningful when both clusterings are complete
    if kc['complete']:
        for metric, value in kc['kc'].items():
            row[f'kc_{metric}'] = value
        # CF/KS only when both annotators did the cluster filtering
        if row['selected_clusters1'] and row['selected_clusters2']:
            row['cf_alpha'] = cf_agreement(data1, data2, kc['mapping'])
            row['ks_kappa'] = ks_agreement(data1, data2, kc['mapping'])
    return row


def format_value(value, decimal_comma=False):
    if isinstance(value, float):
        text = f'{value:.4f}'
        return text.replace('.', ',') if decimal_comma else text
    return '' if value is None else value


def main():
    parser = argparse.ArgumentParser(
        description='Inter-annotator agreement report (CSV)')
    parser.add_argument('--topics', nargs='*',
                        help='topics (default: all)')
    parser.add_argument('--annotators', nargs='*',
                        help='annotators (default: all)')
    parser.add_argument('--out', default='agreement_report.csv',
                        help='output CSV file')
    parser.add_argument('--excel', action='store_true',
                        help="use ';' as separator and decimal comma")
    args = parser.parse_args()

    rows = []
    files = get_annotation_files(args.topics, args.annotators)
    for topic in sorted(files):
        data = {}
        for annotator, filepath in sorted(files[topic].items()):
            try:
                data[annotator] = KeyphraseCurationFile(
                    filepath).get_data_from_json(check_consistency=False)
            except FileNotFoundError:
                print(f'skipped {annotator}/{topic}: file not found',
                      file=sys.stderr)
        for annotator1, annotator2 in combinations(sorted(data), 2):
            try:
                rows.append(agreement_row(
                    topic, annotator1, annotator2,
                    data[annotator1], data[annotator2]))
            except ValueError as e:
                print(f'skipped {topic} {annotator1} x {annotator2}: {e}',
                      file=sys.stderr)

    with open(args.out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=FIELDS, delimiter=';' if args.excel else ',')
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: format_value(row.get(field), args.excel)
                for field in FIELDS})

    for row in rows:
        metrics = '  '.join(
            f"{field}={format_value(row.get(field)) or '-'}"
            for field in ('kc_ari', 'kc_ami', 'kc_fms', 'cf_alpha',
                          'ks_kappa'))
        print(f"{row['topic']}  {row['annotator1']} x {row['annotator2']}  "
              f"{metrics}")
    print(f'{len(rows)} pairs written to {args.out}')


if __name__ == '__main__':
    main()
