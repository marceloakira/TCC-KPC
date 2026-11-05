// @model: specs/001-login-component/model/login-classes.puml
// RF: RF-001, RF-005, RF-006 — Serviço de autenticação

/**
 * AuthService — Serviço HTTP de autenticação.
 * API pública: apenas login() — CONST-R2: zero over-engineering.
 * Privados: getCurrentToken(), makeRequest() (uso interno).
 */
import { User } from '../entities/User.js';
import { API_BASE_URL, ENDPOINTS } from '../../shared/config.js';
import { apiFetch } from '../../shared/http.js';

export class AuthService {
  constructor() {
    this.apiBaseUrl = API_BASE_URL;
  }

  /**
   * (privado) Obtém token de autenticação atual do localStorage
   */
  getCurrentToken() {
    try {
      const token = localStorage.getItem('auth_token');
      if (token) return token;
    } catch (error) {
      console.warn('Erro ao obter token do localStorage:', error);
    }
    return null;
  }

  /**
   * (privado) Método base para requisições com autenticação
   */
  async makeRequest(endpoint, options = {}) {
    const url = `${this.apiBaseUrl}${endpoint}`;
    const token = this.getCurrentToken();

    const defaultHeaders = { 'Content-Type': 'application/json' };
    if (token) defaultHeaders['Authorization'] = `Bearer ${token}`;

    const config = { headers: { ...defaultHeaders, ...options.headers }, ...options };
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
   * POST /users/login — autentica usuário e retorna token.
   * Content-Type: application/x-www-form-urlencoded
   * @param {string} username
   * @param {string} password
   * @returns {Promise<{access_token: string, token_type: string, username: string}>}
   */
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const url = `${this.apiBaseUrl}${ENDPOINTS.LOGIN}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Login failed: ${response.status} - ${errorText}`);
    }

    const data = await response.json();

    // Persistir token no localStorage (para getCurrentToken)
    if (data.access_token) {
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('username', data.username);
    }

    return data;
  }
}