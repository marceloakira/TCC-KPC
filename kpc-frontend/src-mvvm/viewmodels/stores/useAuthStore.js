// @model: specs/001-login-component/model/login-classes.puml
// RF: RF-001, RF-005, RF-006, RF-008, RF-009 — Store de autenticação

/**
 * useAuthStore — Store Zustand com persist para autenticação.
 * Estado e ações limitados ao modelado em login-classes.puml:80-88.
 * CONST-R2: zero over-engineering.
 */
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User } from '../../models/entities/User.js';
import { AuthService } from '../../models/services/AuthService.js';
import { SESSION_EXPIRED_EVENT } from '../../shared/http.js';

const authService = new AuthService();

export const useAuthStore = create(
  persist(
    (set, get) => ({
      // ============================================================================
      // ESTADO MODELADO
      // ============================================================================
      isAuthenticated: false,
      user: null,
      token: null,
      error: null,
      loading: false,

      // ============================================================================
      // AÇÕES MODELADAS
      // ============================================================================

      /**
       * login(username, password) — chama AuthService, trata sucesso/erro, persiste.
       */
      login: async (username, password) => {
        set({ loading: true, error: null });

        try {
          const response = await authService.login(username, password);
          const token = response.access_token;

          const userEntity = User.fromApiResponse(
            response.username || username,
            token
          );

          set({
            isAuthenticated: true,
            user: userEntity,
            token,
            error: null,
            loading: false,
          });
        } catch (err) {
          let errorMsg = 'Credenciais inválidas';

          if (
            err.message?.includes('Network error') ||
            err.message?.includes('Failed to fetch')
          ) {
            errorMsg =
              'Não foi possível conectar ao servidor. Verifique sua conexão.';
          } else if (
            err.message?.includes('401') ||
            err.message?.includes('422')
          ) {
            errorMsg = 'Credenciais inválidas';
          } else if (err.message) {
            errorMsg = err.message;
          }

          set({ loading: false, error: errorMsg });
        }
      },

      /**
       * logout() — limpa estado de autenticação.
       */
      logout: () => {
        set({
          isAuthenticated: false,
          user: null,
          token: null,
          error: null,
          loading: false,
        });
      },

      /**
       * expireSession() — a API recusou o login salvo (HTTP 401): sai e
       * avisa na tela de login. As rotas protegidas redirecionam sozinhas.
       */
      expireSession: () => {
        if (!get().isAuthenticated) return;
        get().logout();
        set({ error: 'Sua sessão expirou. Entre novamente.' });
      },

      /**
       * clearError() — limpa mensagem de erro.
       */
      clearError: () => {
        set({ error: null });
      },

      // ============================================================================
      // AÇÃO INTERNA (mantida para onRehydrateStorage)
      // @note: mantido para onRehydrateStorage — reportar ao Arquiteto se puder ser removido
      // ============================================================================

      /**
       * initialize — verifica dados persistidos ao hidratar.
       */
      initialize: () => {
        const state = get();

        if (state.token && state.user) {
          // Se user foi serializado como plain object, recriar instância User
          if (!(state.user instanceof User)) {
            try {
              const userEntity = new User(
                state.user.username,
                state.user.token
              );
              if (userEntity) {
                set({ user: userEntity });
              } else {
                get().logout();
              }
            } catch (error) {
              console.warn('Erro ao recriar entidade User:', error);
              get().logout();
            }
          }
        }
      },
    }),
    {
      name: 'auth-storage-mvvm',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user
          ? { username: state.user.username, token: state.user.token }
          : null,
        token: state.token,
      }),
      onRehydrateStorage:
        () =>
        (state) => {
          if (state && typeof state.initialize === 'function') {
            try {
              state.initialize();
            } catch (error) {
              console.warn('Erro ao inicializar auth store:', error);
              state.logout();
            }
          }
        },
    }
  )
);

window.addEventListener(SESSION_EXPIRED_EVENT, () => {
  useAuthStore.getState().expireSession();
});
