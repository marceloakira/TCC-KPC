/**
 * AdjudicatorAgreementPanel.jsx - Concordância de agrupamento entre os anotadores
 *
 * Mostra ao adjudicator a concordância (KC) entre os dois anotadores do tópico,
 * comparada com a média da Tabela 3 do artigo.
 *
 * Formato de agreement (campo de GET /topic/adjudicator_data):
 * {
 *   complete: bool,              // nenhum anotador deixou keyphrase no cluster 0
 *   n_keyphrases: number,
 *   not_clustered: [n1, n2],     // keyphrases sem cluster por anotador
 *   convergent: number,          // keyphrases no mesmo cluster (após alinhamento)
 *   kc: { ari, ami, fms } | null,
 *   reference: { ari, ami, fms } // média do artigo
 * }
 */
import React from 'react';
import { Alert, Box, Paper, Tooltip, Typography } from '@mui/material';

const METRICS = [
  {
    key: 'ari',
    label: 'ARI',
    description: 'Adjusted Rand Index: proporção de pares de keyphrases que os dois '
      + 'anotadores colocaram juntos ou separados, descontado o acaso '
      + '(1 = agrupamentos idênticos, 0 = acaso).',
  },
  {
    key: 'ami',
    label: 'AMI',
    description: 'Adjusted Mutual Information: quanta informação um agrupamento dá '
      + 'sobre o outro, descontado o acaso. No artigo aparece como NMI.',
  },
  {
    key: 'fms',
    label: 'FMS',
    description: 'Fowlkes-Mallows Score: média geométrica da precisão e da revocação '
      + 'dos pares de keyphrases colocados no mesmo cluster.',
  },
];

const formatNumber = (value) =>
  value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function comparison(value, reference) {
  if (value > reference) return { text: 'acima', color: 'success.main' };
  if (value < reference) return { text: 'abaixo', color: 'warning.main' };
  return { text: 'igual', color: 'text.secondary' };
}

export default function AdjudicatorAgreementPanel({ agreement }) {
  if (!agreement) return null;

  if (!agreement.complete || !agreement.kc) {
    const [notClustered1, notClustered2] = agreement.not_clustered || [0, 0];
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        Concordância indisponível: anotação incompleta (Anotador 1: {notClustered1},
        Anotador 2: {notClustered2} keyphrases sem cluster).
      </Alert>
    );
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1.5 }}>
        Concordância do agrupamento: Anotador 1 × Anotador 2
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 1.5 }}>
        {METRICS.map(({ key, label, description }) => {
          const value = agreement.kc[key];
          const reference = agreement.reference[key];
          const { text, color } = comparison(value, reference);
          return (
            <Tooltip key={key} title={description} arrow>
              <Box sx={{ flex: '1 1 0', minWidth: 0, cursor: 'help' }}>
                <Typography variant="body2" color="text.secondary">
                  {label}
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 600 }}>
                  {formatNumber(value)}
                </Typography>
                <Typography variant="caption" sx={{ color }}>
                  {text} da média do artigo ({formatNumber(reference)})
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Box>

      <Typography variant="body2" color="text.secondary">
        Keyphrases no mesmo cluster nos dois anotadores: {agreement.convergent} de{' '}
        {agreement.n_keyphrases}
      </Typography>
    </Paper>
  );
}
