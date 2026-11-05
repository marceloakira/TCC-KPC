/**
 * AnnotationService - Serviço responsável por operações relacionadas aos arquivos de anotação
 * Distribui 1 API do grupo ANNOTATION FILES + 2 APIs do grupo SYSTEM do apiService.js
 */
import { API_BASE_URL } from '../../shared/config.js';
import { apiFetch } from '../../shared/http.js';

export class AnnotationService {
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
   * API: GET /annotation_files/{username}/list - Listar arquivos de anotação
   */
  async listAnnotationFiles(username) {
    return this.makeRequest(`/annotation_files/${encodeURIComponent(username)}/list`);
  }

  /**
   * API: GET /openapi.json - Obter especificação OpenAPI
   */
  async getOpenApiSpec() {
    return this.makeRequest('/openapi.json');
  }

  /**
   * API: GET /api/docs - Obter documentação da API
   */
  async getApiDocs() {
    return this.makeRequest('/api/docs');
  }

  /**
   * Métodos de conveniência para operações com arquivos de anotação
   */

  /**
   * Busca arquivo de anotação por ID/nome
   */
  async findAnnotationFileById(username, fileId) {
    const files = await this.listAnnotationFiles(username);
    
    if (Array.isArray(files)) {
      return files.find(file => 
        file.id === fileId || 
        file.filename === fileId || 
        file.name === fileId
      );
    }
    
    return null;
  }

  /**
   * Filtra arquivos de anotação por critérios
   */
  filterAnnotationFiles(files, filters = {}) {
    if (!Array.isArray(files)) {
      return [];
    }
    
    let filtered = [...files];
    
    // Filtrar por tipo de arquivo
    if (filters.fileType) {
      filtered = filtered.filter(file => 
        file.type === filters.fileType ||
        file.extension === filters.fileType ||
        (file.filename && file.filename.endsWith(`.${filters.fileType}`))
      );
    }
    
    // Filtrar por nome parcial
    if (filters.nameContains) {
      const searchLower = filters.nameContains.toLowerCase();
      filtered = filtered.filter(file => 
        (file.filename || '').toLowerCase().includes(searchLower) ||
        (file.name || '').toLowerCase().includes(searchLower)
      );
    }
    
    // Filtrar por data de criação
    if (filters.createdAfter) {
      const afterDate = new Date(filters.createdAfter);
      filtered = filtered.filter(file => {
        const fileDate = new Date(file.created_at || file.createdAt || 0);
        return fileDate >= afterDate;
      });
    }
    
    if (filters.createdBefore) {
      const beforeDate = new Date(filters.createdBefore);
      filtered = filtered.filter(file => {
        const fileDate = new Date(file.created_at || file.createdAt || 0);
        return fileDate <= beforeDate;
      });
    }
    
    // Filtrar por tamanho
    if (filters.minSize !== undefined) {
      filtered = filtered.filter(file => (file.size || 0) >= filters.minSize);
    }
    
    if (filters.maxSize !== undefined) {
      filtered = filtered.filter(file => (file.size || 0) <= filters.maxSize);
    }
    
    return filtered;
  }

  /**
   * Ordena arquivos de anotação por diferentes critérios
   */
  sortAnnotationFiles(files, sortBy = 'name') {
    if (!Array.isArray(files)) {
      return [];
    }
    
    switch (sortBy) {
      case 'name':
        return [...files].sort((a, b) => 
          (a.filename || a.name || '').localeCompare(b.filename || b.name || '')
        );
      
      case 'created':
        return [...files].sort((a, b) => {
          const dateA = new Date(a.created_at || a.createdAt || 0);
          const dateB = new Date(b.created_at || b.createdAt || 0);
          return dateB - dateA; // Mais recente primeiro
        });
      
      case 'size':
        return [...files].sort((a, b) => (b.size || 0) - (a.size || 0));
      
      case 'type':
        return [...files].sort((a, b) => {
          const typeA = a.type || a.extension || '';
          const typeB = b.type || b.extension || '';
          return typeA.localeCompare(typeB);
        });
      
      default:
        return files;
    }
  }

  /**
   * Obtém estatísticas dos arquivos de anotação
   */
  getAnnotationFileStatistics(files) {
    if (!Array.isArray(files) || files.length === 0) {
      return {
        total: 0,
        totalSize: 0,
        avgSize: 0,
        fileTypes: {},
        oldestFile: null,
        newestFile: null
      };
    }
    
    const stats = {
      total: files.length,
      totalSize: files.reduce((sum, file) => sum + (file.size || 0), 0),
      fileTypes: {}
    };
    
    stats.avgSize = stats.totalSize / stats.total;
    
    // Contar tipos de arquivo
    for (const file of files) {
      const type = file.type || file.extension || 'unknown';
      stats.fileTypes[type] = (stats.fileTypes[type] || 0) + 1;
    }
    
    // Encontrar arquivos mais antigo e mais novo
    const sortedByDate = files
      .filter(file => file.created_at || file.createdAt)
      .sort((a, b) => {
        const dateA = new Date(a.created_at || a.createdAt);
        const dateB = new Date(b.created_at || b.createdAt);
        return dateA - dateB;
      });
    
    if (sortedByDate.length > 0) {
      stats.oldestFile = sortedByDate[0];
      stats.newestFile = sortedByDate[sortedByDate.length - 1];
    }
    
    return stats;
  }

  /**
   * Valida formato de arquivo de anotação
   */
  validateAnnotationFile(fileData) {
    const errors = [];
    
    // Verificações básicas
    if (!fileData.filename && !fileData.name) {
      errors.push('Nome do arquivo é obrigatório');
    }
    
    if (!fileData.content && !fileData.path) {
      errors.push('Conteúdo ou caminho do arquivo é obrigatório');
    }
    
    // Verificar extensão
    const filename = fileData.filename || fileData.name || '';
    const supportedExtensions = ['.json', '.xml', '.txt', '.csv', '.tsv'];
    const hasValidExtension = supportedExtensions.some(ext => 
      filename.toLowerCase().endsWith(ext)
    );
    
    if (!hasValidExtension) {
      errors.push(`Extensão de arquivo não suportada. Suportadas: ${supportedExtensions.join(', ')}`);
    }
    
    // Verificar tamanho
    if (fileData.size && fileData.size > 10 * 1024 * 1024) { // 10MB
      errors.push('Arquivo muito grande (máximo 10MB)');
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Converte arquivo de anotação para formato padrão
   */
  normalizeAnnotationFile(fileData) {
    return {
      id: fileData.id || null,
      filename: fileData.filename || fileData.name || 'untitled',
      size: fileData.size || 0,
      type: fileData.type || fileData.extension || 'unknown',
      createdAt: fileData.created_at || fileData.createdAt || new Date().toISOString(),
      updatedAt: fileData.updated_at || fileData.updatedAt || new Date().toISOString(),
      content: fileData.content || null,
      path: fileData.path || null,
      metadata: fileData.metadata || {}
    };
  }

  /**
   * Obtém informações da API (OpenAPI spec + docs)
   */
  async getApiInformation() {
    try {
      const [spec, docs] = await Promise.all([
        this.getOpenApiSpec().catch(() => null),
        this.getApiDocs().catch(() => null)
      ]);
      
      return {
        openApiSpec: spec,
        documentation: docs,
        hasSpec: spec !== null,
        hasDocs: docs !== null
      };
    } catch (error) {
      console.warn('Erro ao obter informações da API:', error);
      return {
        openApiSpec: null,
        documentation: null,
        hasSpec: false,
        hasDocs: false,
        error: error.message
      };
    }
  }

  /**
   * Extrai endpoints da especificação OpenAPI
   */
  extractEndpointsFromSpec(openApiSpec) {
    if (!openApiSpec || !openApiSpec.paths) {
      return [];
    }
    
    const endpoints = [];
    
    for (const [path, methods] of Object.entries(openApiSpec.paths)) {
      for (const [method, details] of Object.entries(methods)) {
        if (typeof details === 'object' && details.summary) {
          endpoints.push({
            path,
            method: method.toUpperCase(),
            summary: details.summary,
            description: details.description || '',
            tags: details.tags || [],
            parameters: details.parameters || [],
            responses: details.responses || {}
          });
        }
      }
    }
    
    return endpoints;
  }

  /**
   * Agrupa endpoints por tags
   */
  groupEndpointsByTags(endpoints) {
    const grouped = {};
    
    for (const endpoint of endpoints) {
      const tags = endpoint.tags.length > 0 ? endpoint.tags : ['untagged'];
      
      for (const tag of tags) {
        if (!grouped[tag]) {
          grouped[tag] = [];
        }
        grouped[tag].push(endpoint);
      }
    }
    
    return grouped;
  }
}

// Instância singleton
export const annotationService = new AnnotationService();