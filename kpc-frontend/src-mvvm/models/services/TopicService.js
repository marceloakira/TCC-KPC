/**
 * TopicService - Serviço responsável por operações relacionadas aos tópicos
 * Distribui as 13 APIs do grupo TOPICS do apiService.js
 */
import { API_BASE_URL } from '../../shared/config.js';
import { apiFetch } from '../../shared/http.js';
import { Topic } from '../entities/Topic.js';

export class TopicService {
  constructor() {
    this.apiBaseUrl = API_BASE_URL;
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
    } else {
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
   * API: GET /topic/{username}/list - Listar tópicos do usuário
   * Backend retorna: {"topics": ["topic1", "topic2", ...]}
   * Converte resposta para array de entidades Topic
   */
  async listTopics(username) {
    const response = await this.makeRequest(`/topic/${encodeURIComponent(username)}/list`);
    
    // Backend retorna {"topics": array}, extrair o array
    let topicsArray = [];
    if (response && response.topics && Array.isArray(response.topics)) {
      topicsArray = response.topics;
    } else if (Array.isArray(response)) {
      topicsArray = response;
    }
    
    // Converter strings para entidades Topic se necessário
    return topicsArray
      .map(topicData => {
        if (typeof topicData === 'string') {
          return Topic.fromApiResponse({ name: topicData, id: topicData });
        }
        return Topic.fromApiResponse(topicData);
      })
      .filter(topic => topic !== null);
  }

  /**
   * API: GET /topic/keyphrase_clustering/{username}/{topic}/{keyphrase_order} - Listar clusters de keyphrases com ordenação
   * @param {string} username - Nome do usuário
   * @param {string} topic - Nome do tópico
   * @param {string} keyphraseOrder - Tipo de ordenação (KeyphraseSorting enum)
   */
  async listKeyphraseClusters(username, topic, keyphraseOrder = 'alphabetical') {
    const url = `/topic/keyphrase_clustering/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(keyphraseOrder)}`;
    try {
      const result = await this.makeRequest(url);
      
      // Novo formato de API: { sorting: string, clusters: array }
      if (result && typeof result === 'object' && result.sorting && Array.isArray(result.clusters)) {
        
        // Validar se a ordenação recebida corresponde à solicitada
        if (result.sorting !== keyphraseOrder) {
          console.warn('⚠️ Ordenação recebida diferente da solicitada:', {
            requested: keyphraseOrder,
            received: result.sorting
          });
        }
        
        // Retornar o array de clusters mantendo índices base-1
        return result.clusters;
      }
      
      // Compatibilidade: se vier array direto (formato antigo)
      if (Array.isArray(result)) {
        // Manter índices base-1 do backend
        return result;
      }
      
      // Compatibilidade: se vier objeto (formato mais antigo)
      if (result && typeof result === 'object') {
        const keyphraseArray = Object.entries(result).map(([index, data]) => ({
          ...data,
          id: parseInt(index), // Manter base-1
          index: parseInt(index) // Manter base-1
        }));
        return keyphraseArray;
      }
      
      // Se vier outro tipo, retorna como está
      console.warn('⚠️ Formato desconhecido recebido:', typeof result);
      return result;
    } catch (error) {
      console.error('❌ TopicService.listKeyphraseClusters erro:', error);
      throw error;
    }
  }

  /**
   * API: GET /topic/clusters/{username}/{topic} - Listar clusters
   */
  async listClusters(username, topic) {
    return this.makeRequest(`/topic/clusters/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * API: GET /topic/cluster_selection/{username}/{topic} - Listar seleção de clusters
   */
  async listClusterSelection(username, topic) {
    return this.makeRequest(`/topic/cluster_selection/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * API: GET /topic/keyphrases_selection/{username}/{topic} - Listar seleção de keyphrases
   */
  async listKeyphrasesSelection(username, topic) {
    return this.makeRequest(`/topic/keyphrases_selection/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * API: GET /topic/keyphrases_aliases/{username}/{topic} - Listar aliases de keyphrases
   */
  async listKeyphrasesAliases(username, topic) {
    return this.makeRequest(`/topic/keyphrases_aliases/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
  }

  /**
   * API: GET /topic/annotation_profile/{username}/{topic} - Obter perfil de anotação
   * Backend retorna: {"annotation_profile": data}
   */
  async getAnnotationProfile(username, topic) {
    const response = await this.makeRequest(`/topic/annotation_profile/${encodeURIComponent(username)}/${encodeURIComponent(topic)}`);
    
    // Backend retorna {"annotation_profile": data}, extrair o perfil
    if (response && response.annotation_profile !== undefined) {
      return response.annotation_profile;
    }
    
    // Se a resposta contém dados de tópico, converter para entidade Topic
    if (response && response.topic_name) {
      return Topic.fromApiResponse(response);
    }
    
    return response;
  }

  /**
   * API: GET /topic/get_annotation_task_options/{username} - Obter opções de tarefa de anotação
   */
  async getAnnotationTaskOptions(username) {
    return this.makeRequest(`/topic/get_annotation_task_options/${encodeURIComponent(username)}`);
  }

  /**
   * API: PUT /topic/move_to_cluster/{username}/{topic}/{keyphrase_id}/{cluster_id} - Mover keyphrase para cluster
   * @param {string} username - Nome do usuário
   * @param {string} topic - Nome do tópico
   * @param {number} keyphraseId - ID da keyphrase (base-1)
   * @param {number} clusterId - ID do cluster
   */
  async moveToCluster(username, topic, keyphraseId, clusterId) {
    
    return this.makeRequest(`/topic/move_to_cluster/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(keyphraseId)}/${encodeURIComponent(clusterId)}`, {
      method: 'PUT'
    });
  }

  /**
   * API: PUT /topic/save_annotation/{username}/{topic}/{task} - Salvar anotação
   */
  async saveAnnotation(username, topic, task) {
    return this.makeRequest(`/topic/save_annotation/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(task)}`, {
      method: 'PUT'
    });
  }

  /**
   * API: PUT /topic/set_alias_and_save_annotation/{username}/{topic}/{cluster_id}/{alias} - Definir alias e salvar
   */
  async setAliasAndSaveAnnotation(username, topic, clusterId, alias) {
    return this.makeRequest(`/topic/set_alias_and_save_annotation/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(clusterId)}/${encodeURIComponent(alias)}`, {
      method: 'PUT'
    });
  }

  /**
   * API: PUT /topic/save_annotation/{username}/{topic}/{task} - Salvar anotação
   */
  async saveAnnotation(username, topic, task) {
    return this.makeRequest(`/topic/save_annotation/${encodeURIComponent(username)}/${encodeURIComponent(topic)}/${encodeURIComponent(task)}`, {
      method: 'PUT'
    });
  }

  /**
   * Métodos de conveniência para operações comuns com tópicos
   */

  /**
   * Busca tópico por ID/nome
   */
  async findTopicById(username, topicId) {
    const topics = await this.listTopics(username);
    return topics.find(topic => topic.id === topicId || topic.name === topicId);
  }

  /**
   * Verifica se usuário pode acessar um tópico específico
   */
  async canUserAccessTopic(username, topicId) {
    try {
      const topic = await this.findTopicById(username, topicId);
      return topic !== null;
    } catch (error) {
      return false;
    }
  }

  /**
   * Obtém todos os dados necessários para exibir um tópico
   */
  async getTopicData(username, topicName) {
    const [
      annotationProfile,
      clusters,
      clusterSelection,
      keyphrasesSelection,
      keyphrasesAliases
    ] = await Promise.all([
      this.getAnnotationProfile(username, topicName),
      this.listClusters(username, topicName),
      this.listClusterSelection(username, topicName),
      this.listKeyphrasesSelection(username, topicName),
      this.listKeyphrasesAliases(username, topicName)
    ]);

    return {
      annotationProfile,
      clusters,
      clusterSelection,
      keyphrasesSelection,
      keyphrasesAliases
    };
  }

  // ============================================================================
  // APIs ESPECÍFICAS PARA MODO ADJUDICADOR
  // ============================================================================

  /**
   * Obtém dados de adjudicação para um tópico (outras anotações)
   * API: GET /topic/adjudicator_data/{username}/{topic}
   */
  async getAdjudicatorData(username, topicName) {
    try {
      
      const response = await apiFetch(`${this.apiBaseUrl}/topic/adjudicator_data/${encodeURIComponent(username)}/${encodeURIComponent(topicName)}`, {
        method: 'GET',
        // NOTA: sem credentials:'include' — o backend usa CORS allow_origins=*,
        // que é rejeitado pelo browser quando credentials estão incluídas.
        // A autenticação é feita via header Bearer.
        headers: {
          'Accept': 'application/json',
          ...(this.getCurrentToken() ? { 'Authorization': `Bearer ${this.getCurrentToken()}` } : {})
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      return data;
    } catch (error) {
      console.error('❌ Error fetching adjudicator data:', error);
      throw error;
    }
  }

  /**
   * Obtém ações do anotador adjudicador
   * API: GET /topic/annotator_actions/{username}/{topic}
   */
  async getAnnotatorActions(username, topicName) {
    try {
      
      const response = await apiFetch(`${this.apiBaseUrl}/topic/annotator_actions/${encodeURIComponent(username)}/${encodeURIComponent(topicName)}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          ...(this.getCurrentToken() ? { 'Authorization': `Bearer ${this.getCurrentToken()}` } : {})
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      return data;
    } catch (error) {
      console.error('❌ Error fetching annotator actions:', error);
      throw error;
    }
  }

  /**
   * Define ação do adjudicador para uma keyphrase
   * API: PUT /topic/adjudicate_and_save/{username}/{topic}/{cluster_id}/{keyphrase_id}/{action}
   * action: 'consent' | 'reject'
   */
  async setAdjudicatorAction(username, topicName, clusterId, keyphraseId, action) {
    try {

      const response = await apiFetch(`${this.apiBaseUrl}/topic/adjudicate_and_save/${encodeURIComponent(username)}/${encodeURIComponent(topicName)}/${clusterId}/${keyphraseId}/${action}`, {
        method: 'PUT',
        headers: {
          'Accept': 'application/json',
          ...(this.getCurrentToken() ? { 'Authorization': `Bearer ${this.getCurrentToken()}` } : {})
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      return data;
    } catch (error) {
      console.error('❌ Error setting adjudicator action:', error);
      throw error;
    }
  }

  /**
   * Salva todo o estado de seleção e aliases de um tópico
   */
  async saveTopicState(username, topicName, taskName) {
    return this.saveAnnotation(username, topicName, taskName);
  }




}

// Instância singleton
export const topicService = new TopicService();