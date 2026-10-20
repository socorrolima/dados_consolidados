// Orquestra o dashboard: bootstrap da sessão, seletor de município, abas
// por categoria de indicador, e os gráficos de cada indicador selecionado.
(function () {
  const MESES_HISTORICO = 6;

  const estado = {
    municipioId: null,
    indicadores: [],
    indicadorAtual: null,
  };

  function competenciasRecentes(quantidade) {
    const hoje = new Date();
    const lista = [];
    for (let i = quantidade - 1; i >= 0; i--) {
      const data = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1);
      const ano = data.getFullYear();
      const mes = String(data.getMonth() + 1).padStart(2, "0");
      lista.push(`${ano}${mes}`);
    }
    return lista;
  }

  function formataCompetencia(aaaamm) {
    const ano = aaaamm.slice(0, 4);
    const mes = aaaamm.slice(4, 6);
    return `${mes}/${ano}`;
  }

  async function montaSeletorMunicipio(municipios) {
    const seletor = document.getElementById("seletor-municipio");
    seletor.innerHTML = "";

    if (municipios.length === 0) {
      const opcao = document.createElement("option");
      opcao.textContent = "Nenhum município vinculado";
      seletor.appendChild(opcao);
      seletor.disabled = true;
      return null;
    }

    municipios.forEach((m) => {
      const opcao = document.createElement("option");
      opcao.value = m.id;
      opcao.textContent = `${m.nome} — ${m.uf}`;
      seletor.appendChild(opcao);
    });

    seletor.addEventListener("change", () => {
      estado.municipioId = Number(seletor.value);
      carregarIndicadorAtual();
    });

    return municipios[0].id;
  }

  function montaAbas(indicadoresPorCategoria) {
    const nav = document.getElementById("abas-categoria");
    nav.innerHTML = "";

    Object.keys(indicadoresPorCategoria).forEach((categoria, i) => {
      const botao = document.createElement("button");
      botao.textContent = categoria;
      botao.className = "aba" + (i === 0 ? " ativa" : "");
      botao.addEventListener("click", () => {
        document.querySelectorAll(".aba").forEach((b) => b.classList.remove("ativa"));
        botao.classList.add("ativa");
        montaSeletorIndicador(indicadoresPorCategoria[categoria]);
      });
      nav.appendChild(botao);
    });

    const primeiraCategoria = Object.keys(indicadoresPorCategoria)[0];
    if (primeiraCategoria) {
      montaSeletorIndicador(indicadoresPorCategoria[primeiraCategoria]);
    }
  }

  function montaSeletorIndicador(indicadoresDaCategoria) {
    const seletor = document.getElementById("seletor-indicador");
    seletor.innerHTML = "";

    indicadoresDaCategoria.forEach((ind) => {
      const opcao = document.createElement("option");
      opcao.value = ind.codigo;
      opcao.textContent = ind.nome_exibicao;
      seletor.appendChild(opcao);
    });

    estado.indicadorAtual = indicadoresDaCategoria[0];
    carregarIndicadorAtual();

    seletor.onchange = () => {
      estado.indicadorAtual = indicadoresDaCategoria.find((i) => i.codigo === seletor.value);
      carregarIndicadorAtual();
    };
  }

  function valorPrincipal(resposta) {
    // municipio_mes tem valor_municipio; estado_mes tem valor_estado.
    return "valor_municipio" in resposta ? resposta.valor_municipio : resposta.valor_estado;
  }

  async function carregarIndicadorAtual() {
    if (!estado.indicadorAtual || !estado.municipioId) return;

    const competencias = competenciasRecentes(MESES_HISTORICO);
    const respostas = await Promise.all(
      competencias.map((c) => Api.dashboard(estado.municipioId, estado.indicadorAtual.codigo, c))
    );

    const labels = competencias.map(formataCompetencia);
    const serieValor = respostas.map(valorPrincipal);
    const seriePiloto = respostas.map((r) => r.media_piloto);

    Charts.linhaComparativa("grafico-linha", labels, [
      { nome: estado.indicadorAtual.granularidade === "estado_mes" ? "Estado" : "Município", valores: serieValor },
      { nome: "Média do piloto (BA+PE+RN)", valores: seriePiloto },
    ]);

    // Pega o mês mais recente que já tem valor — o mês corrente costuma
    // ainda não ter dado publicado pela fonte, e usar sempre o último mês
    // do calendário faria o gráfico de comparação parecer "zerado" sem
    // ser isso que aconteceu.
    const comDado = [...respostas].reverse().find((r) => valorPrincipal(r) !== null);
    const ultima = comDado || respostas[respostas.length - 1];
    const labelsBarras = ["Valor atual", "Média piloto"];
    const valoresBarras = [valorPrincipal(ultima), ultima.media_piloto];
    if ("media_brasil" in ultima) {
      labelsBarras.push("Média Brasil");
      valoresBarras.push(ultima.media_brasil);
    } else {
      labelsBarras.splice(1, 0, "Média da UF");
      valoresBarras.splice(1, 0, ultima.media_uf);
    }

    Charts.barraRanking("grafico-barra", labelsBarras, valoresBarras);
  }

  async function iniciar() {
    let usuario;
    try {
      usuario = await Api.me();
    } catch (erro) {
      return; // Api.chamar já redirecionou pro /login em caso de 401
    }

    document.getElementById("nome-usuario").textContent = usuario.nome;

    const primeiroMunicipioId = await montaSeletorMunicipio(usuario.municipios);
    if (primeiroMunicipioId === null) return;
    estado.municipioId = primeiroMunicipioId;

    const indicadores = await Api.indicadores();
    const porCategoria = {};
    indicadores.forEach((ind) => {
      (porCategoria[ind.categoria] = porCategoria[ind.categoria] || []).push(ind);
    });

    montaAbas(porCategoria);
  }

  document.getElementById("botao-sair").addEventListener("click", () => {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  });

  iniciar();
})();
