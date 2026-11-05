/**
 * ClusterService - Serviço responsável por operações relacionadas aos clusters
 * Distribui as 2 APIs do grupo CLUSTERS do apiService.js
 */
import { API_BASE_URL } from '../../shared/config.js';
import { apiFetch } from '../../shared/http.js';
import { Cluster } from '../entities/Cluster.js';
import { Keyphrase } from '../entities/Keyphrase.js';

export class ClusterService {
  constructor() {
    this.apiBaseUrl = API_BASE_URL;
  }

  /**
   * API: GET /topic/clusters/{username}/{topic} - Obter clusters
   */
  async getClusters(username, topic) {
    return this.makeRequest(`/topic/clusters/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * API: GET /topic/cluster_selections/{username}/{topic} - Obter seleções de clusters
   */
  async getClusterSelections(username, topic) {
    return this.makeRequest(`/topic/cluster_selections/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * API: GET /topic/selected_keyphrases/{username}/{topic} - Obter keyphrases selecionadas
   */
  async getSelectedKeyphrases(username, topic) {
    return this.makeRequest(`/topic/selected_keyphrases/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * Obtém o token atual do localStorage (usando chave MVVM)
   */
  getCurrentToken() {
    try {
      // Tentar primeiro a chave MVVM
      let authStorage = localStorage.getItem('auth-storage-mvvm');
      
      // Fallback para chave original
      if (!authStorage) {
        authStorage = localStorage.getItem('auth-storage');
      }
      
      if (authStorage) {
        const parsed = JSON.parse(authStorage);
        return parsed.state?.token || null;
      }
    } catch (error) {
      console.warn('Erro ao obter token do localStorage:', error);
    }
    return null;
  }

  /**
   * Método base para requisições com autenticação
   */
  async makeRequest(endpoint, options = {}) {
    const url = `${this.apiBaseUrl}${endpoint}`;
    const token = this.getCurrentToken();
    
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config = {
      headers: { ...defaultHeaders, ...options.headers },
      ...options
    };

    const response = await apiFetch(url, config);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    try {
      return await response.json();
    } catch {
      return response;
    }
  }

  /**
   * API: GET /clusters/cluster_sorting_options/{username} - Obter opções de ordenação de clusters
   */
  async getClusterSortingOptions(username) {
    return this.makeRequest(`/clusters/cluster_sorting_options/${encodeURIComponent(username)}`);
  }

  /**
   * API: GET /clusters/get_cluster_sorting_by_value/{username}/{cluster_order} - Obter ordenação de clusters
   */
  async getClusterSortingByValue(username, clusterOrder) {
    return this.makeRequest(`/clusters/get_cluster_sorting_by_value/${encodeURIComponent(username)}/${encodeURIComponent(clusterOrder)}`);
  }

  // ============================================================================
  // APIS DE CLUSTER MOVIDAS DO TOPICSERVICE (CRÍTICO)
  // ============================================================================

  /**
   * API: PUT /topic/move_to_cluster/{username}/{topic}/{keyphrase_id}/{cluster_id} - Mover keyphrase para cluster
   * Movida do TopicService para centralizar operações de cluster
   */
  async moveToCluster(username, topic, keyphraseId, clusterId) {
    
    return this.makeRequest(`/topic/move_to_cluster/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(keyphraseId)}/${encodeURIComponent(clusterId)}`, {
      method: 'PUT'
    });
  }

  /**
   * API: PUT /topic/move_to_cluster_and_save_annotation/{username}/{topic}/{keyphrase_id}/{cluster_id} - Mover keyphrase e salvar em uma operação
   * Nova API que combina move_to_cluster + save_annotation para resolver problemas de persistência
   */
  async moveToClusterAndSave(username, topic, keyphraseId, clusterId) {
    
    return this.makeRequest(`/topic/move_to_cluster_and_save_annotation/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(keyphraseId)}/${encodeURIComponent(clusterId)}`, {
      method: 'PUT'
    });
  }

  /**
   * API: PUT /topic/select_cluster_and_save_annotation/{username}/{topic}/{cluster_id}/{selected} - Selecionar cluster e salvar
   * Movida do TopicService para centralizar operações de cluster
   */
  async selectClusterAndSaveAnnotation(username, topic, clusterId, selected) {
    
    return this.makeRequest(`/topic/select_cluster_and_save_annotation/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(clusterId)}/${encodeURIComponent(selected)}`, {
      method: 'PUT'
    });
  }

  /**
   * API: PUT /topic/select_keyphrase_and_save_annotation/{username}/{topic}/{cluster_id}/{order}/{keyphrase_id} - Selecionar keyphrase e salvar
   * Movida do TopicService para centralizar operações de cluster
   */
  async selectKeyphraseAndSaveAnnotation(username, topic, clusterId, order, keyphraseId) {
    
    return this.makeRequest(`/topic/select_keyphrase_and_save_annotation/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(clusterId)}/${encodeURIComponent(order)}/${encodeURIComponent(keyphraseId)}`, {
      method: 'PUT'
    });
  }

  // ============================================================================
  // MÉTODOS UTILITÁRIOS PARA REPLICAR LÓGICA REACTPY
  // ============================================================================

  /**
   * Extrai ID da keyphrase usando regex (replicando get_kp_id do ReactPy)
   */
  extractKeyphraseId(keyphraseStr) {
    if (!keyphraseStr || typeof keyphraseStr !== 'string') {
      return null;
    }
    
    // Regex: \((\d+)\) - busca por números entre parênteses no final
    const match = keyphraseStr.match(/\((\d+)\)$/);
    return match ? match[1] : null;
  }

  /**
   * Verifica se cluster é o último (cluster lixeira - desabilitado)
   */
  isTrashCluster(clusterId, totalClusters) {
    return parseInt(clusterId) === (totalClusters - 1);
  }

  /**
   * Calcula cor do chip baseado no estado de seleção (replicando lógica ReactPy)
   */
  getChipColor(keyphraseStr, clusterId, selectedClusters, selectedKeyphrases) {
    const keyphraseId = this.extractKeyphraseId(keyphraseStr);
    if (!keyphraseId) return 'default';

    const clusterSelection = selectedClusters[clusterId] || '0';
    const clusterKeyphrases = selectedKeyphrases[clusterId] || {};
    
    const isSelected = keyphraseId === String(clusterKeyphrases.selected1) || 
                      keyphraseId === String(clusterKeyphrases.selected2);

    if (isSelected) {
      if (clusterSelection === '1') return 'success';      // Verde - selecionado e ativo
      if (clusterSelection === '0') return 'error';        // Vermelho - selecionado mas inativo  
      if (clusterSelection === '-1') return 'warning';     // Amarelo - status especial
    }
    
    return 'default'; // Cinza - não selecionado
  }

  /**
   * Processa seleção de cluster seguindo padrão ReactPy (value = "clusterId,selectedValue")
   */
  async processClusterSelection(username, topicName, value) {
    
    const [clusterId, selectedValue] = value.split(',');
    
    if (!clusterId || selectedValue === undefined) {
      throw new Error('Invalid cluster selection format. Expected "clusterId,selectedValue"');
    }
    
    return this.selectClusterAndSaveAnnotation(username, topicName, parseInt(clusterId), parseInt(selectedValue));
  }

  /**
   * Processa seleção de keyphrase seguindo padrão ReactPy (value = "clusterId,keyphraseId")
   */
  async processKeyphraseSelection(username, topicName, value, order) {
    
    const [clusterId, keyphraseId] = value.split(',');
    
    if (!clusterId || keyphraseId === undefined) {
      throw new Error('Invalid keyphrase selection format. Expected "clusterId,keyphraseId"');
    }
    
    return this.selectKeyphraseAndSaveAnnotation(username, topicName, parseInt(clusterId), order, parseInt(keyphraseId));
  }

  /**
   * Métodos de conveniência para operações com clusters
   */

  /**
   * Cria cluster a partir de dados de API
   */
  createClusterFromApiData(clusterData, keyphrases = []) {
    const cluster = new Cluster(clusterData.id || clusterData.cluster_id);
    
    // Adicionar keyphrases se fornecidas
    if (Array.isArray(keyphrases)) {
      for (const keyphraseData of keyphrases) {
        const keyphrase = keyphraseData instanceof Keyphrase 
          ? keyphraseData 
          : Keyphrase.fromApiResponse(keyphraseData);
        
        if (keyphrase) {
          cluster.addKeyphrase(keyphrase);
        }
      }
    }
    
    // Aplicar outras propriedades do cluster
    if (clusterData.selected !== undefined) {
      cluster.setSelected(clusterData.selected);
    }
    
    if (clusterData.alias) {
      cluster.setAlias(clusterData.alias);
    }
    
    if (clusterData.cohesion !== undefined) {
      cluster.cohesion = clusterData.cohesion;
    }
    
    return cluster;
  }

  /**
   * Ordena clusters por diferentes critérios
   */
  async sortClusters(clusters, sortBy = 'id') {
    switch (sortBy) {
      case 'id':
        return [...clusters].sort((a, b) => a.id - b.id);
      
      case 'size':
        return [...clusters].sort((a, b) => b.getKeyphraseCount() - a.getKeyphraseCount());
      
      case 'cohesion':
        return [...clusters].sort((a, b) => b.cohesion - a.cohesion);
      
      case 'selected':
        return [...clusters].sort((a, b) => {
          if (a.isSelected() && !b.isSelected()) return -1;
          if (!a.isSelected() && b.isSelected()) return 1;
          return a.id - b.id;
        });
      
      case 'alias':
        return [...clusters].sort((a, b) => {
          const aliasA = a.getAlias() || '';
          const aliasB = b.getAlias() || '';
          return aliasA.localeCompare(aliasB) || a.id - b.id;
        });
      
      default:
        return clusters;
    }
  }

  /**
   * Filtra clusters por critérios específicos
   */
  filterClusters(clusters, filters = {}) {
    let filtered = [...clusters];
    
    // Filtrar por seleção
    if (filters.selected !== undefined) {
      filtered = filtered.filter(cluster => cluster.isSelected() === filters.selected);
    }
    
    // Filtrar por tamanho mínimo
    if (filters.minSize !== undefined) {
      filtered = filtered.filter(cluster => cluster.getKeyphraseCount() >= filters.minSize);
    }
    
    // Filtrar por coesão mínima
    if (filters.minCohesion !== undefined) {
      filtered = filtered.filter(cluster => cluster.cohesion >= filters.minCohesion);
    }
    
    // Filtrar por presença de alias
    if (filters.hasAlias !== undefined) {
      filtered = filtered.filter(cluster => cluster.hasAlias() === filters.hasAlias);
    }
    
    // Filtrar por keyphrases específicas
    if (filters.containsKeyphrase) {
      filtered = filtered.filter(cluster => 
        cluster.hasKeyphrase(filters.containsKeyphrase)
      );
    }
    
    // Filtrar clusters vazios
    if (filters.excludeEmpty) {
      filtered = filtered.filter(cluster => !cluster.isEmpty());
    }
    
    return filtered;
  }

  /**
   * Obtém estatísticas dos clusters
   */
  getClusterStatistics(clusters) {
    if (!Array.isArray(clusters) || clusters.length === 0) {
      return {
        total: 0,
        selected: 0,
        empty: 0,
        withAlias: 0,
        avgSize: 0,
        avgCohesion: 0,
        totalKeyphrases: 0
      };
    }
    
    const stats = {
      total: clusters.length,
      selected: clusters.filter(c => c.isSelected()).length,
      empty: clusters.filter(c => c.isEmpty()).length,
      withAlias: clusters.filter(c => c.hasAlias()).length,
    };
    
    // Calcular médias
    const totalKeyphrases = clusters.reduce((sum, c) => sum + c.getKeyphraseCount(), 0);
    const totalCohesion = clusters.reduce((sum, c) => sum + c.cohesion, 0);
    
    stats.totalKeyphrases = totalKeyphrases;
    stats.avgSize = stats.total > 0 ? totalKeyphrases / stats.total : 0;
    stats.avgCohesion = stats.total > 0 ? totalCohesion / stats.total : 0;
    
    return stats;
  }

  /**
   * Encontra cluster por ID
   */
  findClusterById(clusters, clusterId) {
    return clusters.find(cluster => cluster.id === clusterId);
  }

  /**
   * Agrupa keyphrases em clusters baseado em critérios
   */
  groupKeyphrasesIntoClusters(keyphrases, clusteringOptions = {}) {
    const {
      maxClusters = 10,
      minSimilarity = 0.5,
      maxClusterSize = 20
    } = clusteringOptions;
    
    const clusters = [];
    const unassigned = [...keyphrases];
    let clusterId = 1;
    
    while (unassigned.length > 0 && clusters.length < maxClusters) {
      const seed = unassigned.shift();
      const cluster = new Cluster(clusterId++);
      cluster.addKeyphrase(seed);
      
      // Encontrar keyphrases similares para adicionar ao cluster
      const toRemove = [];
      for (let i = 0; i < unassigned.length && cluster.getKeyphraseCount() < maxClusterSize; i++) {
        const candidate = unassigned[i];
        
        // Calcular similaridade média com keyphrases do cluster
        let avgSimilarity = 0;
        for (const clusterKeyphrase of cluster.keyphrases) {
          avgSimilarity += candidate.calculateSimilarityWith(clusterKeyphrase);
        }
        avgSimilarity /= cluster.keyphrases.length;
        
        if (avgSimilarity >= minSimilarity) {
          cluster.addKeyphrase(candidate);
          toRemove.push(i);
        }
      }
      
      // Remover keyphrases atribuídas
      for (let i = toRemove.length - 1; i >= 0; i--) {
        unassigned.splice(toRemove[i], 1);
      }
      
      clusters.push(cluster);
    }
    
    // Criar cluster para keyphrases não atribuídas
    if (unassigned.length > 0) {
      const remainingCluster = new Cluster(clusterId);
      for (const keyphrase of unassigned) {
        remainingCluster.addKeyphrase(keyphrase);
      }
      clusters.push(remainingCluster);
    }
    
    return clusters;
  }

  /**
   * Calcula qualidade do clustering
   */
  calculateClusteringQuality(clusters) {
    if (!Array.isArray(clusters) || clusters.length === 0) {
      return 0;
    }
    
    // Métrica baseada na coesão média ponderada pelo tamanho
    let weightedCohesion = 0;
    let totalWeight = 0;
    
    for (const cluster of clusters) {
      const size = cluster.getKeyphraseCount();
      if (size > 1) {
        weightedCohesion += cluster.cohesion * size;
        totalWeight += size;
      }
    }
    
    return totalWeight > 0 ? weightedCohesion / totalWeight : 0;
  }

  /**
   * Mescla dois clusters
   */
  mergeClusters(cluster1, cluster2) {
    if (!(cluster1 instanceof Cluster) || !(cluster2 instanceof Cluster)) {
      throw new Error('Argumentos devem ser instâncias de Cluster');
    }
    
    const mergedCluster = new Cluster(cluster1.id);
    
    // Adicionar keyphrases do primeiro cluster
    for (const keyphrase of cluster1.keyphrases) {
      mergedCluster.addKeyphrase(keyphrase);
    }
    
    // Adicionar keyphrases do segundo cluster
    for (const keyphrase of cluster2.keyphrases) {
      mergedCluster.addKeyphrase(keyphrase);
    }
    
    // Herdar seleções se ambos estiverem selecionados
    if (cluster1.isSelected() && cluster2.isSelected()) {
      mergedCluster.setSelected(true);
    }
    
    // Usar alias do primeiro cluster ou combinar
    const alias1 = cluster1.getAlias();
    const alias2 = cluster2.getAlias();
    
    if (alias1 && alias2) {
      mergedCluster.setAlias(`${alias1} / ${alias2}`);
    } else if (alias1) {
      mergedCluster.setAlias(alias1);
    } else if (alias2) {
      mergedCluster.setAlias(alias2);
    }
    
    return mergedCluster;
  }

  /**
   * Obtém ordenação personalizada para um usuário
   */
  async getUserClusterOrdering(username, orderType) {
    try {
      return await this.getClusterSortingByValue(username, orderType);
    } catch (error) {
      console.warn('Erro ao obter ordenação personalizada:', error);
      return null;
    }
  }

  /**
   * Obtém opções de ordenação disponíveis para um usuário
   */
  async getUserSortingOptions(username) {
    try {
      return await this.getClusterSortingOptions(username);
    } catch (error) {
      console.warn('Erro ao obter opções de ordenação:', error);
      return [];
    }
  }
}

// Instância singleton
export const clusterService = new ClusterService();