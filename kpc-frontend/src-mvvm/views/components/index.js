/**
 * Components Index - Exporta todos os componentes reutilizáveis MVVM
 * 
 * Este arquivo centraliza a exportação de todos os componentes UI puros,
 * facilitando a importação nas Views e mantendo a organização da arquitetura MVVM.
 */

// ============================================================================
// COMPONENTES BÁSICOS - Baseados no Material-UI
// ============================================================================

// Componente de botão padronizado
export { default as Button } from './Button.jsx';

// Componente de campo de texto padronizado  
export { default as TextField } from './TextField.jsx';

// Componente de chip padronizado
export { default as Chip } from './Chip.jsx';

// Componente de dialog/modal padronizado
export { default as Dialog } from './Dialog.jsx';

// ============================================================================
// COMPONENTES ESPECÍFICOS DO DOMÍNIO - Keyphrase Curation
// ============================================================================

// Componente para item individual de keyphrase
export { default as KeyphraseItem } from './KeyphraseItem.jsx';

// Componente para card de cluster com keyphrases
export { default as ClusterCard } from './ClusterCard.jsx';

// Componente para adjudicação de clusters (modo "clues_from_other_annotators")
export { default as AdjudicatorClusterChips } from './AdjudicatorClusterChips.jsx';

// Componentes de adjudicação migrados de keyphrase_curation/frontend
export { default as AdjudicatorChip } from './AdjudicatorChip.jsx';
export { default as AdjudicatorClusters } from './AdjudicatorClusters.jsx';

// Concordância entre os anotadores exibida ao adjudicator
export { default as AdjudicatorAgreementPanel } from './AdjudicatorAgreementPanel.jsx';

// ============================================================================
// METADATA DO MÓDULO
// ============================================================================

/**
 * Informações sobre o módulo de componentes
 */
export const COMPONENTS_INFO = {
  version: '1.0.0',
  description: 'Reusable UI components for MVVM architecture',
  basicComponents: [
    'Button',
    'TextField',
    'Chip', 
    'Dialog'
  ],
  domainComponents: [
    'KeyphraseItem',
    'ClusterCard',
    'AdjudicatorClusterChips',
    'AdjudicatorChip',
    'AdjudicatorClusters',
    'AdjudicatorAgreementPanel'
  ],
  totalComponents: 10,
  lastUpdated: new Date().toISOString()
};

// ============================================================================
// VALIDAÇÃO (apenas em desenvolvimento)
// ============================================================================

if (process.env.NODE_ENV === 'development') {
}