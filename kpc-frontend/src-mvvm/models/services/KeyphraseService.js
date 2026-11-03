/**
 * KeyphraseService - Serviço responsável por operações relacionadas às keyphrases
 * Distribui as 2 APIs do grupo KEYPHRASES do apiService.js
 */
import { API_BASE_URL } from '../../shared/config.js';
import { Keyphrase } from '../entities/Keyphrase.js';

export class KeyphraseService {
  constructor() {
    this.apiBaseUrl = API_BASE_URL;
  }

  /**
   * Obtém o token atual do localStorage
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

    const response = await fetch(url, config);
    
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
   * API: GET /keyphrases/list - Listar keyphrases
   * Converte resposta para array de entidades Keyphrase
   */
  async listKeyphrases() {
    const response = await this.makeRequest('/keyphrases/list');
    
    if (Array.isArray(response)) {
      return response
        .map(keyphraseData => Keyphrase.fromApiResponse(keyphraseData))
        .filter(keyphrase => keyphrase !== null);
    }
    
    return response;
  }

  /**
   * API: GET /keyphrases/get_keyphrase_sorting_by_value/{username}/{keyphrase_order} - Obter ordenação de keyphrases
   */
  async getKeyphraseSortingByValue(username, keyphraseOrder) {
    return this.makeRequest(`/keyphrases/get_keyphrase_sorting_by_value/${encodeURIComponent(username)}/${encodeURIComponent(keyphraseOrder)}`);
  }

  /**
   * Métodos de conveniência para operações com keyphrases
   */

  /**
   * Busca keyphrase por ID
   */
  async findKeyphraseById(keyphraseId) {
    const keyphrases = await this.listKeyphrases();
    return keyphrases.find(keyphrase => keyphrase.id === keyphraseId);
  }

  /**
   * Busca keyphrases por texto parcial
   */
  async findKeyphrasesByText(searchText) {
    const keyphrases = await this.listKeyphrases();
    const searchLower = searchText.toLowerCase();
    
    return keyphrases.filter(keyphrase => 
      keyphrase.text.toLowerCase().includes(searchLower)
    );
  }

  /**
   * Ordena keyphrases por diferentes critérios
   */
  async sortKeyphrases(keyphrases, sortBy = 'text') {
    switch (sortBy) {
      case 'text':
        return [...keyphrases].sort((a, b) => a.text.localeCompare(b.text));
      
      case 'frequency':
        return [...keyphrases].sort((a, b) => (b.frequency || 0) - (a.frequency || 0));
      
      case 'similarity':
        return [...keyphrases].sort((a, b) => (b.similarity || 0) - (a.similarity || 0));
      
      case 'clusterId':
        return [...keyphrases].sort((a, b) => (a.clusterId || 0) - (b.clusterId || 0));
      
      default:
        return keyphrases;
    }
  }

  /**
   * Calcula similaridade entre duas keyphrases
   */
  calculateSimilarity(keyphrase1, keyphrase2) {
    if (!(keyphrase1 instanceof Keyphrase) || !(keyphrase2 instanceof Keyphrase)) {
      return 0;
    }
    
    return keyphrase1.calculateSimilarityWith(keyphrase2);
  }

  /**
   * Agrupa keyphrases por cluster
   */
  groupKeyphrasesByCluster(keyphrases) {
    const grouped = {};
    
    for (const keyphrase of keyphrases) {
      const clusterId = keyphrase.clusterId || 'unassigned';
      
      if (!grouped[clusterId]) {
        grouped[clusterId] = [];
      }
      
      grouped[clusterId].push(keyphrase);
    }
    
    return grouped;
  }

  /**
   * Filtra keyphrases por critérios específicos
   */
  filterKeyphrases(keyphrases, filters = {}) {
    let filtered = [...keyphrases];
    
    // Filtrar por cluster
    if (filters.clusterId !== undefined) {
      filtered = filtered.filter(kp => kp.clusterId === filters.clusterId);
    }
    
    // Filtrar por seleção
    if (filters.selected !== undefined) {
      filtered = filtered.filter(kp => kp.isSelected() === filters.selected);
    }
    
    // Filtrar por frequência mínima
    if (filters.minFrequency !== undefined) {
      filtered = filtered.filter(kp => (kp.frequency || 0) >= filters.minFrequency);
    }
    
    // Filtrar por similaridade mínima
    if (filters.minSimilarity !== undefined) {
      filtered = filtered.filter(kp => (kp.similarity || 0) >= filters.minSimilarity);
    }
    
    // Filtrar por texto
    if (filters.textContains) {
      const searchLower = filters.textContains.toLowerCase();
      filtered = filtered.filter(kp => 
        kp.text.toLowerCase().includes(searchLower)
      );
    }
    
    return filtered;
  }

  /**
   * Obtém estatísticas das keyphrases
   */
  getKeyphraseStatistics(keyphrases) {
    if (!Array.isArray(keyphrases) || keyphrases.length === 0) {
      return {
        total: 0,
        selected: 0,
        clustered: 0,
        unassigned: 0,
        avgFrequency: 0,
        avgSimilarity: 0
      };
    }
    
    const stats = {
      total: keyphrases.length,
      selected: keyphrases.filter(kp => kp.isSelected()).length,
      clustered: keyphrases.filter(kp => kp.clusterId !== null && kp.clusterId !== undefined).length,
      unassigned: keyphrases.filter(kp => kp.clusterId === null || kp.clusterId === undefined).length,
    };
    
    // Calcular médias
    const totalFrequency = keyphrases.reduce((sum, kp) => sum + (kp.frequency || 0), 0);
    const totalSimilarity = keyphrases.reduce((sum, kp) => sum + (kp.similarity || 0), 0);
    
    stats.avgFrequency = stats.total > 0 ? totalFrequency / stats.total : 0;
    stats.avgSimilarity = stats.total > 0 ? totalSimilarity / stats.total : 0;
    
    return stats;
  }

  /**
   * Encontra keyphrases similares para uma keyphrase específica
   */
  findSimilarKeyphrases(targetKeyphrase, keyphrases, threshold = 0.5, limit = 10) {
    if (!(targetKeyphrase instanceof Keyphrase)) {
      return [];
    }
    
    const similarities = keyphrases
      .filter(kp => kp.id !== targetKeyphrase.id)
      .map(kp => ({
        keyphrase: kp,
        similarity: targetKeyphrase.calculateSimilarityWith(kp)
      }))
      .filter(item => item.similarity >= threshold)
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, limit);
    
    return similarities;
  }

  /**
   * Obtém ordenação personalizada para um usuário
   */
  async getUserKeyphraseOrdering(username, orderType) {
    try {
      return await this.getKeyphraseSortingByValue(username, orderType);
    } catch (error) {
      console.warn('Erro ao obter ordenação personalizada:', error);
      return null;
    }
  }
}

// Instância singleton
export const keyphraseService = new KeyphraseService();