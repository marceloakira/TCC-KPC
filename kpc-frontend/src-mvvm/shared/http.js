/**
 * http.js - fetch das chamadas autenticadas à API do backend.
 *
 * O backend responde 401 quando o login falta, é inválido ou expirou.
 * Nesse caso, apiFetch dispara SESSION_EXPIRED_EVENT, e o useAuthStore
 * encerra a sessão: as rotas protegidas voltam para a tela de login.
 * O próprio login (AuthService.login) usa fetch direto, porque lá o 401
 * significa senha errada.
 */
export const SESSION_EXPIRED_EVENT = 'kpc:session-expired';

export async function apiFetch(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
  return response;
}
