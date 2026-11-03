// @model: specs/001-login-component/model/login-classes.puml
// RF: RF-001, RF-005 — Configuração compartilhada

/**
 * config.js - Sistema de configuração para replicar config do ReactPy
 * Centraliza configurações do sistema como no backend ReactPy
 */

/**
 * URL base da API do backend KPC.
 * Em produção o build usa VITE_API_BASE_URL=/api (mesmo endereço do site,
 * repassado ao backend pelo Caddy); no desenvolvimento, o backend local.
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:3132';

/**
 * Endpoints da API
 */
export const ENDPOINTS = {
  LOGIN: '/users/login',
};

/**
 * Configurações principais do sistema (baseadas no backend ReactPy)
 */
export const config = {
  // Configuração de curação de keyphrases (do curated_keyphrases.py)
  curated_keyphrases_length: 20,
  
  // Configurações de clustering
  max_clusters: 10,
  min_cluster_size: 2,
  similarity_threshold: 0.5,
  
  // Configurações de API
  api_base_url: API_BASE_URL,
  api_timeout: 30000,
  
  // Configurações de autenticação
  session_timeout: 3600000, // 1 hora em ms
  cookie_name: 'kpc-session',
  
  // Configurações de UI
  items_per_page: 50,
  auto_save_interval: 30000, // 30 segundos
  
  // Configurações de ordenação padrão
  default_keyphrase_order: 'alphabetical',
  default_cluster_order: 'numerical',
  default_curated_order: 'source_cluster',
  
  // Configurações de validação
  min_username_length: 3,
  min_password_length: 4,
  max_alias_length: 100,
  
  // Configurações de cores para chips (baseadas no ReactPy keyphrase_clusters.py)
  chip_colors: {
    success: '#4caf50',    // Verde - cluster selecionado (CS=1) + keyphrase selecionada
    error: '#f44336',      // Vermelho - cluster não selecionado (CS=0) + keyphrase selecionada
    warning: '#ff9800',    // Amarelo - status especial (CS=-1)
    default: '#9e9e9e',    // Cinza - não selecionada
    info: '#2196f3',       // Azul - informação
    primary: '#3f51b5'     // Roxo - primário
  },
  
  // Configurações de adjudicator (baseadas no chip_test.py)
  adjudicator: {
    enabled: true,
    modes: ['union', 'annotator1', 'annotator2', 'adjudicator'],
    chip_states: ['consented', 'consented_rejected'],
    colors: {
      consented: '#4caf50',
      consented_rejected: '#f44336',
      pending: '#ff9800'
    }
  },
  
  // Configurações de debug
  debug: {
    enabled: process.env.NODE_ENV === 'development',
    log_api_calls: true,
    log_state_changes: true,
    show_performance_metrics: false
  }
};

/**
 * Configurações derivadas (calculadas dinamicamente)
 */
export const getDerivedConfig = () => ({
  // Formatação de contador de curação
  getCurationCounterFormat: (current, total = config.curated_keyphrases_length) => 
    `${current}/${total}`,
  
  // Validação de progresso de curação
  isCurationComplete: (current, total = config.curated_keyphrases_length) => 
    current >= total,
  
  // Porcentagem de conclusão
  getCurationPercentage: (current, total = config.curated_keyphrases_length) => 
    total > 0 ? Math.round((current / total) * 100) : 0,
  
  // Headers padrão para API
  getDefaultApiHeaders: () => ({
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }),
  
  // URL completa da API
  getApiUrl: (endpoint) => `${config.api_base_url}${endpoint}`,
  
  // Configurações de timeout para diferentes tipos de requisição
  getTimeoutForOperation: (operation) => {
    const timeouts = {
      login: 10000,
      save: 15000,
      load: 20000,
      default: config.api_timeout
    };
    return timeouts[operation] || timeouts.default;
  }
});

/**
 * Validadores baseados na configuração
 */
export const validators = {
  username: (username) => ({
    isValid: username && username.length >= config.min_username_length,
    message: `Usuário deve ter pelo menos ${config.min_username_length} caracteres`
  }),
  
  password: (password) => ({
    isValid: password && password.length >= config.min_password_length,
    message: `Senha deve ter pelo menos ${config.min_password_length} caracteres`
  }),
  
  alias: (alias) => ({
    isValid: !alias || alias.length <= config.max_alias_length,
    message: `Alias deve ter no máximo ${config.max_alias_length} caracteres`
  }),
  
  clusterSelection: (value) => ({
    isValid: ['0', '1', '-1'].includes(String(value)),
    message: 'Seleção de cluster deve ser 0, 1 ou -1'
  })
};

/**
 * Utilitários de configuração
 */
export const configUtils = {
  /**
   * Verifica se funcionalidade está habilitada
   */
  isFeatureEnabled: (feature) => {
    const features = {
      adjudicator: config.adjudicator.enabled,
      debug: config.debug.enabled,
      auto_save: config.auto_save_interval > 0
    };
    return features[feature] || false;
  },
  
  /**
   * Obtém cor do chip baseada no estado
   */
  getChipColor: (state) => {
    return config.chip_colors[state] || config.chip_colors.default;
  },
  
  /**
   * Atualiza configuração (para testes)
   */
  updateConfig: (updates) => {
    if (config.debug.enabled) {
      Object.assign(config, updates);
    }
  },
  
  /**
   * Reset configuração para padrões
   */
  resetConfig: () => {
    if (config.debug.enabled) {
      // Implementar reset se necessário
    }
  }
};

/**
 * Constantes do sistema (baseadas no ReactPy)
 */
export const CONSTANTS = {
  // Estados de cluster (CS values)
  CLUSTER_STATES: {
    UNSELECTED: '0',
    SELECTED: '1', 
    SPECIAL: '-1'
  },
  
  // Ordens de keyphrase (do keyphrase_clustering.py)
  KEYPHRASE_ORDERS: [
    'alphabetical',
    'numerical', 
    'cluster_similarity',
    'pairwise_similarity'
  ],
  
  // Ordens de cluster (do keyphrase_clusters.py)
  CLUSTER_ORDERS: [
    'numerical',
    'cluster_cohesion',
    'pairwise_similarity', 
    'centroid_similarity',
    'clues_from_other_annotators'
  ],
  
  // Ordens de curação (do curated_keyphrases.py)
  CURATION_ORDERS: [
    'source_cluster',
    'alphabetical'
  ],
  
  // Códigos de status HTTP
  HTTP_STATUS: {
    OK: 200,
    UNAUTHORIZED: 401,
    ERROR: 501
  }
};

// Export padrão
export default config;