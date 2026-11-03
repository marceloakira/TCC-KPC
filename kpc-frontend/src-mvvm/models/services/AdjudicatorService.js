/**
 * AdjudicatorService - Serviço para operações de adjudicação
 * 
 * Endpoints do backend:
 *   GET  /topic/adjudicator_data/{username}/{topic}
 *   PUT  /topic/adjudicate/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}
 *   PUT  /topic/adjudicate_and_save/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}
 */
import { API_BASE_URL } from '../../shared/config.js';

export class AdjudicatorService {
  constructor() {
    this.apiBaseUrl = API_BASE_URL;
  }

  getCurrentToken() {
    try {
      let authStorage = localStorage.getItem('auth-storage-mvvm');
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

  async makeRequest(endpoint, options = {}) {
    const url = `${this.apiBaseUrl}${endpoint}`;
    const token = this.getCurrentToken();
    const defaultHeaders = { 'Content-Type': 'application/json' };
    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`;
    }
    const config = {
      headers: { ...defaultHeaders, ...options.headers },
      ...options,
    };
    const response = await fetch(url, config);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        `HTTP ${response.status}: ${response.statusText} - ${JSON.stringify(errorData)}`
      );
    }
    try {
      return await response.json();
    } catch {
      return response;
    }
  }

  /**
   * GET /topic/adjudicator_data/{username}/{topic}
   * Retorna dados de adjudicação: adjudicator, annotator1, annotator2, union
   */
  async getAdjudicatorData(username, topic) {
    return this.makeRequest(
      `/topic/adjudicator_data/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`
    );
  }

  /**
   * PUT /topic/adjudicate/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}
   * action: "consent" | "reject"
   */
  async adjudicate(username, topic, clusterId, keyphraseId, action) {
    return this.makeRequest(
      `/topic/adjudicate/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${clusterId}/${keyphraseId}/${action}`,
      { method: 'PUT' }
    );
  }

  /**
   * PUT /topic/adjudicate_and_save/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}
   * action: "consent" | "reject"
   */
  async adjudicateAndSave(username, topic, clusterId, keyphraseId, action) {
    return this.makeRequest(
      `/topic/adjudicate_and_save/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${clusterId}/${keyphraseId}/${action}`,
      { method: 'PUT' }
    );
  }
}

export const adjudicatorService = new AdjudicatorService();