// Wrapper único pra chamar a API interna — nunca chama aplicacoes.mds.gov.br
// direto. Anexa o Bearer token e trata 401 (token ausente/expirado) indo
// pro login; 403 (sem acesso ao recurso) o chamador decide o que fazer.
const Api = (function () {
  function token() {
    return localStorage.getItem("access_token");
  }

  async function chamar(caminho) {
    const resp = await fetch(caminho, {
      headers: { Authorization: `Bearer ${token()}` },
    });

    if (resp.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
      throw new Error("sessão expirada");
    }

    const corpo = await resp.json();
    if (!resp.ok) {
      const erro = new Error(corpo.erro || `erro ${resp.status}`);
      erro.status = resp.status;
      throw erro;
    }

    return corpo;
  }

  return {
    me: () => chamar("/api/me"),
    indicadores: () => chamar("/api/indicadores"),
    dashboard: (municipioId, indicadorCodigo, competencia) =>
      chamar(
        `/api/dashboard/${municipioId}?indicador=${encodeURIComponent(indicadorCodigo)}&competencia=${competencia}`
      ),
  };
})();
