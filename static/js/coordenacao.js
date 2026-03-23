const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    Authorization: `Bearer ${token}`
};

const headersJson = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json"
};

let abaCoordAtiva = "ocorrencias";
let ocorrenciaEmEdicaoId = null;
let ocorrenciaSelecionadaId = null;
let estudanteEmEdicao = null;
let regimentoItemEmEdicao = null;
let ocorrenciasCache = [];
let estudantesCache = [];
let regimentoItensCache = [];
let relatorioOcorrenciasCache = [];
let relatorioOcorrenciasCarregado = false;
let opcoesOcorrencias = {
    turmas: [],
    professores: [],
    disciplinas: [],
    status: [],
    acoes_aplicadas: [],
    regimento_itens: [],
    status_padrao: "registrado"
};
const MAX_AULAS_EXIBICAO = 5;
const TURNO_OFFSET_FAIXA = {
    MATUTINO: 0,
    INTEGRAL: 0,
    VESPERTINO: 5,
    VESPERTINO_EM: 5
};

const rotulosAcao = new Map();
const rotulosStatus = new Map();
const mapaBuscaEstudantes = new Map();
const mapaBuscaProfessores = new Map();
const mapaBuscaDisciplinas = new Map();
const mapaBuscaRegimento = new Map();
let timerBuscaEstudantes = null;
const MODELO_CSV_ESTUDANTES = [
    "nome,turma,ativo",
    "Ana Maria Souza,8 B,ativo",
    "Bruno Henrique Lima,9 A,1"
].join("\n");
const MODELO_CSV_BASE_LEGAL = [
    "artigo,descricao,ativo",
    "\"Art. 76 - VII\",\"Integrar-se ao processo pedagogico desenvolvido pela unidade escolar.\",ativo",
    "\"Art. 53 - ECA\",\"A crianca e o adolescente tem direito a educacao e respeito.\",ativo"
].join("\n");
const OBSERVACOES_ACAO_PREVIEW = {
    orientacao_verbal: "OBS.: O registro fica arquivado para acompanhamento pedagogico e orientacao verbal junto ao estudante.",
    advertencia: "OBS.: Pela falta de integracao e compromisso e por nao acatar as solicitacoes da docente, recebe esta acao pedagogico-disciplinar de advertencia.",
    chamada_responsavel: "OBS.: Solicitado o comparecimento do responsavel para alinhamento e acompanhamento conjunto do caso.",
    encaminhamento_direcao: "OBS.: O registro segue encaminhado a Direcao para providencias e acompanhamento institucional.",
    registro_informativo: "OBS.: Documento emitido para registro informativo e acompanhamento pedagogico interno."
};

function el(id) {
    return document.getElementById(id);
}

function normalizarCargoUsuario(usuario = {}) {
    const cargo = String(usuario.cargo || "").trim().toUpperCase();
    if (cargo) return cargo;

    const perfil = String(usuario.perfil || "").trim().toLowerCase();
    if (perfil === "admin") return "ADMIN";
    if (perfil === "coordenador") return "COORDENADOR";
    return "PROFESSOR";
}

function setMensagemOcorrencias(texto, erro = false) {
    const target = el("msgOcorrencias");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function setMensagemEstudantes(texto, erro = false) {
    const target = el("msgEstudantes");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function setMensagemRelatorios(texto, erro = false) {
    const target = el("msgRelatorios");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function setMensagemRegimento(texto, erro = false) {
    const target = el("msgRegimento");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function houveFalhaImportacao(resultado) {
    return Number(resultado?.importados || 0) <= 0 && Number(resultado?.erros || 0) > 0;
}

function comporMensagemImportacaoCsv(resultado) {
    const mensagemBase = String(resultado?.mensagem || "Importacao concluida.").trim();
    const detalhes = Array.isArray(resultado?.detalhes_erros) ? resultado.detalhes_erros : [];
    if (detalhes.length === 0) return mensagemBase;

    const amostra = detalhes.slice(0, 3);
    const restante = detalhes.length - amostra.length;
    let mensagem = `${mensagemBase} ${amostra.join(" | ")}`;
    if (restante > 0) {
        mensagem += ` | +${restante} erro(s) adicional(is).`;
    }
    return mensagem;
}

function baixarArquivoTexto(nomeArquivo, conteudo, tipo = "text/csv;charset=utf-8") {
    const blob = new Blob(["\uFEFF", conteudo], { type: tipo });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = nomeArquivo;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
}

function normalizarErro(res, body) {
    if (body && body.detail) return body.detail;
    return `Erro ${res.status}`;
}

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    let body = null;
    try {
        body = await res.json();
    } catch (_err) {
        body = null;
    }

    if (res.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
        throw new Error("Sessao expirada.");
    }

    if (!res.ok) {
        const erro = new Error(normalizarErro(res, body));
        erro.status = res.status;
        throw erro;
    }
    return body;
}

async function fetchResposta(url, options = {}) {
    const res = await fetch(url, options);

    if (res.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
        throw new Error("Sessao expirada.");
    }

    if (!res.ok) {
        let detalhe = `Erro ${res.status}`;
        const tipoConteudo = String(res.headers.get("content-type") || "").toLowerCase();
        if (tipoConteudo.includes("application/json")) {
            try {
                const body = await res.json();
                detalhe = normalizarErro(res, body);
            } catch (_err) {
                detalhe = `Erro ${res.status}`;
            }
        } else {
            try {
                const texto = (await res.text()).trim();
                if (texto) detalhe = texto;
            } catch (_err) {
                detalhe = `Erro ${res.status}`;
            }
        }

        const erro = new Error(detalhe);
        erro.status = res.status;
        throw erro;
    }

    return res;
}

async function requisitarExclusao(urlDelete, urlFallback) {
    try {
        return await fetchJson(urlDelete, {
            method: "DELETE",
            headers
        });
    } catch (err) {
        if (err?.status !== 405) {
            throw err;
        }

        return fetchJson(urlFallback, {
            method: "POST",
            headers
        });
    }
}

function formatarDataBr(dataIso) {
    if (!dataIso) return "Nao informada";
    const data = new Date(`${dataIso}T00:00:00`);
    if (Number.isNaN(data.getTime())) return dataIso;
    return data.toLocaleDateString("pt-BR");
}

function formatarDataHora(dataHoraSql) {
    if (!dataHoraSql) return "Nao informado";
    const data = new Date(String(dataHoraSql).replace(" ", "T"));
    if (Number.isNaN(data.getTime())) return String(dataHoraSql);
    return data.toLocaleString("pt-BR");
}

function rotuloAcao(acao) {
    return rotulosAcao.get(acao) || acao || "Nao informado";
}

function rotuloStatus(status) {
    return rotulosStatus.get(status) || status || "Nao informado";
}

function classeStatus(status) {
    const texto = String(status || "").trim().toLowerCase();
    if (!texto) return "status-registrado";
    return `status-${texto.replace(/[^a-z0-9_]/g, "-")}`;
}

function classeStatusEstudante(ativo) {
    return ativo ? "status-resolvido" : "status-aguardando_responsavel";
}

function listarBotoesAbasCoord() {
    return Array.from(document.querySelectorAll("[data-coord-tab-trigger]"));
}

function listarPaineisAbasCoord() {
    return Array.from(document.querySelectorAll("[data-coord-tab-panel]"));
}

function ativarAbaCoordenacao(abaId) {
    abaCoordAtiva = abaId;
    listarBotoesAbasCoord().forEach((botao) => {
        const ativa = botao.dataset.coordTabTrigger === abaId;
        botao.classList.toggle("is-active", ativa);
        botao.setAttribute("aria-selected", ativa ? "true" : "false");
    });
    listarPaineisAbasCoord().forEach((painel) => {
        const ativo = painel.dataset.coordTabPanel === abaId;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
    if (abaId === "relatorios" && !relatorioOcorrenciasCarregado) {
        carregarRelatorioOcorrencias().catch((err) => {
            setMensagemRelatorios(err.message, true);
        });
    }
}

function painelFormularioOcorrenciaAberto() {
    const painel = el("painelFormOcorrencia");
    return Boolean(painel) && !painel.hidden;
}

function atualizarBotaoNovaOcorrencia() {
    const botao = el("btnNovaOcorrencia");
    if (!botao) return;

    const painelAberto = painelFormularioOcorrenciaAberto();
    if (!painelAberto) {
        botao.innerText = "Registrar ocorrencia";
    } else if (ocorrenciaEmEdicaoId) {
        botao.innerText = "Nova ocorrencia";
    } else {
        botao.innerText = "Ocultar formulario";
    }

    botao.setAttribute("aria-expanded", painelAberto ? "true" : "false");
}

function mostrarPainelFormularioOcorrencia({ scroll = false } = {}) {
    const painel = el("painelFormOcorrencia");
    if (!painel) return;
    painel.hidden = false;
    atualizarBotaoNovaOcorrencia();
    if (scroll) {
        painel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function ocultarPainelFormularioOcorrencia() {
    const painel = el("painelFormOcorrencia");
    if (!painel) return;
    painel.hidden = true;
    atualizarBotaoNovaOcorrencia();
}

function preencherSelect(selectId, opcoes, {
    incluirTodos = false,
    placeholder = "",
    valorPadrao = "",
    obterRotulo = null
} = {}) {
    const select = el(selectId);
    if (!select) return;

    select.innerHTML = "";

    if (incluirTodos) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Todos";
        select.appendChild(option);
    } else if (placeholder) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = placeholder;
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
    }

    (opcoes || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item.id);
        option.innerText = typeof obterRotulo === "function"
            ? obterRotulo(item)
            : (item.nome || item.id);
        select.appendChild(option);
    });

    if (valorPadrao !== "") {
        select.value = String(valorPadrao);
    }
}

function limparMapaSugestoes(mapa) {
    if (mapa && typeof mapa.clear === "function") {
        mapa.clear();
    }
}

function registrarMapaSugestoes(mapa, item) {
    if (!mapa || typeof mapa.set !== "function" || !item) return;

    const chaves = new Set(
        [
            item.label,
            item.nome,
            item.artigo,
        ]
            .map((valor) => String(valor || "").trim())
            .filter(Boolean)
    );
    chaves.forEach((chave) => mapa.set(chave, item));
}

function obterDescricaoSugestao(item) {
    if (!item) return "";
    if (item.turma_nome) return `Turma: ${item.turma_nome}`;
    if (item.email) return item.email;
    if (item.descricao) {
        return String(item.descricao).trim();
    }
    return "";
}

function obterTituloSugestao(item) {
    return String(item?.nome || item?.artigo || item?.label || "").trim();
}

function obterItemSugestaoPorTexto(mapa, texto, itensFallback = []) {
    const termo = String(texto || "").trim();
    if (!termo) return null;
    if (mapa && mapa.has(termo)) return mapa.get(termo);

    const termoLower = termo.toLowerCase();
    const candidatos = [];
    if (mapa && typeof mapa.values === "function") {
        candidatos.push(...mapa.values());
    }
    if (Array.isArray(itensFallback)) {
        candidatos.push(...itensFallback);
    }

    const vistos = new Set();
    for (const item of candidatos) {
        if (!item || vistos.has(item)) continue;
        vistos.add(item);

        const textos = [
            item.label,
            item.nome,
            item.artigo,
        ]
            .map((valor) => String(valor || "").trim().toLowerCase())
            .filter(Boolean);
        if (textos.includes(termoLower)) {
            return item;
        }
    }
    return null;
}

function ocultarSugestoes(autocompleteId) {
    const lista = el(autocompleteId);
    if (!lista) return;
    lista.innerHTML = "";
    lista.hidden = true;
}

function ocultarTodasSugestoes() {
    ["listaEstudantesBusca", "listaProfessoresBusca", "listaDisciplinasBusca", "listaRegimentoBusca"].forEach(ocultarSugestoes);
}

function preencherDatalist(datalistId, mapa, itens, { onSelect = null, textoVazio = "" } = {}) {
    const datalist = el(datalistId);
    if (!datalist) return;
    datalist.innerHTML = "";
    limparMapaSugestoes(mapa);

    const itensValidos = Array.isArray(itens) ? itens.filter(Boolean) : [];
    itensValidos.forEach((item) => registrarMapaSugestoes(mapa, item));

    if (itensValidos.length === 0) {
        if (textoVazio) {
            const vazio = document.createElement("div");
            vazio.className = "coordenacao-autocomplete-empty";
            vazio.innerText = textoVazio;
            datalist.appendChild(vazio);
            datalist.hidden = false;
            return;
        }
        datalist.hidden = true;
        return;
    }

    itensValidos.forEach((item) => {
        const tituloTexto = obterTituloSugestao(item);
        if (!tituloTexto) return;

        const option = document.createElement("button");
        option.type = "button";
        option.className = "coordenacao-autocomplete-item";

        const titulo = document.createElement("strong");
        titulo.innerText = tituloTexto;
        option.appendChild(titulo);

        const descricaoTexto = obterDescricaoSugestao(item);
        if (descricaoTexto) {
            const descricao = document.createElement("span");
            descricao.innerText = descricaoTexto;
            option.appendChild(descricao);
        }

        option.addEventListener("pointerdown", (event) => {
            event.preventDefault();
            if (typeof onSelect === "function") {
                onSelect(item);
            }
            ocultarSugestoes(datalistId);
        });
        datalist.appendChild(option);
    });
    datalist.hidden = false;
}

function normalizarIdsRegimento(valores) {
    const vistos = new Set();
    return (valores || []).map((valor) => Number(valor || 0))
        .filter((valor) => Number.isInteger(valor) && valor > 0)
        .filter((valor) => {
            if (vistos.has(valor)) return false;
            vistos.add(valor);
            return true;
        });
}

function obterIdsRegimentoSelecionadosFormulario() {
    return normalizarIdsRegimento(
        Array.from(document.querySelectorAll("#ocorrenciaRegimentoSelecionados [data-regimento-item-id]"))
            .map((item) => item.dataset.regimentoItemId)
    );
}

function obterIdsRegimentoSelecionadosOcorrencia(ocorrencia) {
    return normalizarIdsRegimento(
        Array.isArray(ocorrencia?.regimento_itens)
            ? ocorrencia.regimento_itens.map((item) => item.regimento_item_id)
            : []
    );
}

function renderSelecionadorRegimento(idsSelecionados = null) {
    const container = el("ocorrenciaRegimentoSelecionados");
    if (!container) {
        atualizarPreviewOcorrencia();
        return;
    }

    const idsAtivos = new Set(
        idsSelecionados === null
            ? obterIdsRegimentoSelecionadosFormulario()
            : normalizarIdsRegimento(idsSelecionados)
    );
    container.innerHTML = "";

    const itens = Array.isArray(opcoesOcorrencias.regimento_itens)
        ? opcoesOcorrencias.regimento_itens
        : [];
    if (itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = "Cadastre itens da base legal para anexa-los na ocorrencia.";
        container.appendChild(vazio);
        atualizarPreviewOcorrencia();
        return;
    }

    const itensSelecionados = itens.filter((item) => idsAtivos.has(Number(item.id || 0)));
    if (itensSelecionados.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = "Nenhuma base legal anexada ainda.";
        container.appendChild(vazio);
        atualizarPreviewOcorrencia();
        return;
    }

    itensSelecionados.forEach((item) => {
        const id = Number(item.id || 0);
        if (!id) return;

        const card = document.createElement("article");
        card.className = "coordenacao-regimento-card";
        card.dataset.regimentoItemId = String(id);
        if (!Boolean(item.ativo)) {
            card.classList.add("is-inactive");
        }

        const corpo = document.createElement("div");
        corpo.className = "coordenacao-regimento-card-body";

        const artigo = document.createElement("strong");
        artigo.innerText = String(item.artigo || "Sem artigo");

        const descricao = document.createElement("span");
        descricao.innerText = String(item.descricao || "").trim() || "Sem descricao.";

        corpo.appendChild(artigo);
        corpo.appendChild(descricao);

        if (!Boolean(item.ativo)) {
            const meta = document.createElement("small");
            meta.className = "coordenacao-regimento-option-meta";
            meta.innerText = "Item inativo no cadastro.";
            corpo.appendChild(meta);
        }

        const btnRemover = document.createElement("button");
        btnRemover.type = "button";
        btnRemover.className = "coordenacao-regimento-remove";
        btnRemover.innerText = "Remover";
        btnRemover.addEventListener("click", () => {
            const proximosIds = obterIdsRegimentoSelecionadosFormulario().filter((valor) => Number(valor) !== id);
            renderSelecionadorRegimento(proximosIds);
        });

        card.appendChild(corpo);
        card.appendChild(btnRemover);
        container.appendChild(card);
    });
    atualizarPreviewOcorrencia();
}

function normalizarTurnoId(turnoId) {
    return String(turnoId || "").trim().toUpperCase();
}

function aulaLabel(aula) {
    return `${aula}ª aula`;
}

function faixaGlobalPorTurnoEAula(turnoId, aulaTurno) {
    const turno = normalizarTurnoId(turnoId);
    const aula = Number(aulaTurno || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    if (!Number.isFinite(aula) || aula <= 0) return 0;

    let faixaGlobal = aula + offset;
    if (turno === "INTEGRAL" && aula > 5) {
        faixaGlobal += 1;
    }
    return faixaGlobal;
}

function aulaTurnoPorFaixa(turnoId, faixaGlobal) {
    const turno = normalizarTurnoId(turnoId);
    const faixa = Number(faixaGlobal || 0);
    const offset = TURNO_OFFSET_FAIXA[turno] ?? 0;
    if (!Number.isFinite(faixa) || faixa <= 0) return 0;

    if (turno === "INTEGRAL") {
        if (faixa >= 1 && faixa <= 5) return faixa;
        if (faixa >= 7) return faixa - 1;
        return 0;
    }

    return faixa - offset;
}

function obterTurmaOpcaoPorId(turmaId) {
    const turmaIdNumero = Number(turmaId || 0);
    return (opcoesOcorrencias.turmas || []).find((item) => Number(item.id) === turmaIdNumero) || null;
}

function obterProfessorOpcaoPorId(professorId) {
    const professorIdNumero = Number(professorId || 0);
    return (opcoesOcorrencias.professores || []).find((item) => Number(item.id) === professorIdNumero) || null;
}

function popularSugestoesProfessores() {
    limparMapaSugestoes(mapaBuscaProfessores);
    (opcoesOcorrencias.professores || []).forEach((item) => registrarMapaSugestoes(mapaBuscaProfessores, item));
    ocultarSugestoes("listaProfessoresBusca");
}

function popularSugestoesDisciplinas() {
    limparMapaSugestoes(mapaBuscaDisciplinas);
    (opcoesOcorrencias.disciplinas || []).forEach((item) => registrarMapaSugestoes(mapaBuscaDisciplinas, item));
    ocultarSugestoes("listaDisciplinasBusca");
}

function popularSugestoesRegimento() {
    limparMapaSugestoes(mapaBuscaRegimento);
    (opcoesOcorrencias.regimento_itens || []).forEach((item) => registrarMapaSugestoes(mapaBuscaRegimento, item));
    ocultarSugestoes("listaRegimentoBusca");
}

function obterItensDisponiveisRegimento() {
    const idsSelecionados = new Set(obterIdsRegimentoSelecionadosFormulario());
    return (opcoesOcorrencias.regimento_itens || []).filter((item) => {
        const id = Number(item?.id || 0);
        if (id <= 0 || idsSelecionados.has(id)) {
            return false;
        }
        return Boolean(item.ativo);
    });
}

function correspondeTextoRegimento(item, termo) {
    const termoNormalizado = String(termo || "").trim().toLowerCase();
    if (!termoNormalizado) return false;

    return [
        item?.artigo,
        item?.label,
        item?.descricao
    ].some((valor) => String(valor || "").trim().toLowerCase() === termoNormalizado);
}

function selecionarSugestaoRegimento(item) {
    const id = Number(item?.id || 0);
    if (id <= 0) return;

    const proximosIds = normalizarIdsRegimento([
        ...obterIdsRegimentoSelecionadosFormulario(),
        id
    ]);
    renderSelecionadorRegimento(proximosIds);
    el("ocorrenciaBuscaRegimento").value = "";
    ocultarSugestoes("listaRegimentoBusca");
}

function aplicarSelecaoRegimentoPorTexto() {
    const input = el("ocorrenciaBuscaRegimento");
    const texto = input.value.trim();
    if (!texto) {
        ocultarSugestoes("listaRegimentoBusca");
        return;
    }

    const item = obterItensDisponiveisRegimento().find((candidato) => correspondeTextoRegimento(candidato, texto));
    if (item) {
        selecionarSugestaoRegimento(item);
        return;
    }

    input.value = "";
    ocultarSugestoes("listaRegimentoBusca");
}

function atualizarSugestoesRegimentoBusca(forcar = false) {
    const termo = el("ocorrenciaBuscaRegimento").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaRegimentoBusca");
        return;
    }

    const itensDisponiveis = obterItensDisponiveisRegimento();
    const itens = filtrarSugestoesLocais(itensDisponiveis, termo, {
        limite: 12,
        campos: ["artigo", "descricao", "label"]
    });

    const totalAtivos = (opcoesOcorrencias.regimento_itens || []).filter((item) => Boolean(item?.ativo)).length;
    const textoVazio = totalAtivos === 0
        ? "Cadastre bases legais ativas para pesquisar."
        : itensDisponiveis.length === 0
            ? "Todas as bases legais ativas ja foram anexadas."
        : "Nenhuma base legal encontrada.";
    preencherDatalist("listaRegimentoBusca", mapaBuscaRegimento, itens, {
        onSelect: selecionarSugestaoRegimento,
        textoVazio
    });
}

function faixasDisponiveisTurma(turma) {
    if (!turma || !turma.turno_valido) return [];

    const faixasApi = Array.isArray(turma.faixas_disponiveis)
        ? turma.faixas_disponiveis.map((valor) => Number(valor)).filter((valor) => Number.isInteger(valor) && valor > 0)
        : [];
    if (faixasApi.length > 0) {
        return faixasApi;
    }

    const totalAulas = Number(turma.aulas || 0);
    const faixasCalculadas = [];
    for (let aula = 1; aula <= totalAulas; aula++) {
        const faixa = faixaGlobalPorTurnoEAula(turma.turno, aula);
        if (faixa > 0) {
            faixasCalculadas.push(faixa);
        }
    }
    return faixasCalculadas;
}

function resolverFaixaOcorrenciaParaTurma(turma, aulaValor) {
    const texto = String(aulaValor || "").trim();
    if (!texto) return 0;

    const numero = Number.parseInt(texto, 10);
    if (!Number.isInteger(numero) || numero <= 0) return 0;

    const faixasTurma = faixasDisponiveisTurma(turma);
    if (faixasTurma.includes(numero)) {
        return numero;
    }

    const totalAulas = Number(turma?.aulas || 0);
    if (Number.isInteger(totalAulas) && numero <= totalAulas) {
        const faixaCalculada = faixaGlobalPorTurnoEAula(turma.turno, numero);
        if (faixaCalculada > 0 && faixasTurma.includes(faixaCalculada)) {
            return faixaCalculada;
        }
    }

    return 0;
}

function formatarAulaOcorrencia(ocorrencia) {
    const turma = obterTurmaOpcaoPorId(ocorrencia?.turma_id);
    const faixa = resolverFaixaOcorrenciaParaTurma(turma, ocorrencia?.aula);
    if (faixa <= 0 || !turma) {
        return ocorrencia?.aula || "Nao informada";
    }

    const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixa);
    if (aulaTurno <= 0) {
        return `Faixa ${faixa}`;
    }
    return `${aulaLabel(aulaTurno)} (faixa ${faixa})`;
}

function obterOcorrenciaEmEdicaoAtual() {
    if (!ocorrenciaEmEdicaoId) return null;
    return (ocorrenciasCache || []).find((ocorrencia) => Number(ocorrencia.id) === Number(ocorrenciaEmEdicaoId)) || null;
}

function obterTextoOuPadrao(valor, padrao = "Nao informado") {
    const texto = String(valor || "").trim();
    return texto || padrao;
}

function obterTurmaPreviewFormulario() {
    const turmaId = el("ocorrenciaTurmaId")?.value;
    const turma = obterTurmaOpcaoPorId(turmaId);
    if (turma?.nome) return turma.nome;

    const select = el("ocorrenciaTurmaId");
    const opcao = select?.selectedOptions?.[0];
    return obterTextoOuPadrao(opcao?.textContent, "Nao informada");
}

function obterAulaPreviewFormulario() {
    const select = el("ocorrenciaAula");
    const opcao = select?.selectedOptions?.[0];
    const textoOpcao = String(opcao?.textContent || "").trim();
    if (textoOpcao && !opcao?.disabled) {
        return textoOpcao;
    }

    const valor = String(select?.value || "").trim();
    return valor || "Nao informada";
}

function obterHorarioPreviewFormulario() {
    const horario = String(el("ocorrenciaHorario")?.value || "").trim();
    return horario ? `As ${horario} h` : "Nao informado";
}

function obterObservacaoFinalPreview(acaoAplicada) {
    const acao = String(acaoAplicada || "").trim();
    return OBSERVACOES_ACAO_PREVIEW[acao] || `OBS.: Documento emitido para registro e acompanhamento da acao aplicada: ${rotuloAcao(acao)}.`;
}

function obterItensRegimentoSelecionadosPreview() {
    const idsSelecionados = new Set(obterIdsRegimentoSelecionadosFormulario());
    return (opcoesOcorrencias.regimento_itens || []).filter((item) => idsSelecionados.has(Number(item?.id || 0)));
}

function definirTextoPreview(id, valor, padrao = "Nao informado") {
    const target = el(id);
    if (!target) return;
    target.innerText = obterTextoOuPadrao(valor, padrao);
}

function renderizarBaseLegalPreview(itens) {
    const container = el("previewBaseLegal");
    if (!container) return;

    container.innerHTML = "";
    if (!Array.isArray(itens) || itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-preview-empty";
        vazio.innerText = "Nenhuma base legal anexada ainda.";
        container.appendChild(vazio);
        return;
    }

    itens.forEach((item) => {
        const artigo = document.createElement("div");
        artigo.className = "coordenacao-preview-legal-item";

        const titulo = document.createElement("strong");
        titulo.innerText = obterTextoOuPadrao(item?.artigo, "Sem artigo");

        const descricao = document.createElement("span");
        descricao.innerText = obterTextoOuPadrao(item?.descricao, "Sem descricao.");

        artigo.appendChild(titulo);
        artigo.appendChild(descricao);
        container.appendChild(artigo);
    });
}

function atualizarPreviewOcorrencia() {
    if (!el("ocorrenciaPreviewPdf")) return;

    const ocorrenciaAtual = obterOcorrenciaEmEdicaoAtual();
    const estudante = el("ocorrenciaBuscaEstudante")?.value;
    const professor = el("ocorrenciaBuscaProfessor")?.value;
    const disciplina = el("ocorrenciaDisciplina")?.value;
    const descricao = el("ocorrenciaDescricao")?.value;
    const dataOcorrencia = el("ocorrenciaData")?.value;
    const acaoAplicada = el("ocorrenciaAcaoAplicada")?.value;
    const status = el("ocorrenciaStatus")?.value;

    definirTextoPreview("previewNomeEstudante", estudante);
    definirTextoPreview("previewTurma", obterTurmaPreviewFormulario(), "Nao informada");
    definirTextoPreview("previewProfessor", professor);
    definirTextoPreview("previewDisciplina", disciplina, "Nao informada");
    definirTextoPreview("previewData", formatarDataBr(dataOcorrencia), "Nao informada");
    definirTextoPreview("previewAula", obterAulaPreviewFormulario(), "Nao informada");
    definirTextoPreview("previewHorario", obterHorarioPreviewFormulario(), "Nao informado");
    definirTextoPreview("previewAcao", rotuloAcao(acaoAplicada), "Nao informada");
    definirTextoPreview("previewStatus", rotuloStatus(status), "Nao informado");

    const descricaoPreview = el("previewDescricao");
    if (descricaoPreview) {
        descricaoPreview.innerText = obterTextoOuPadrao(
            descricao,
            "A descricao digitada no formulario aparecera aqui automaticamente."
        );
    }

    renderizarBaseLegalPreview(obterItensRegimentoSelecionadosPreview());

    const observacaoPreview = el("previewObservacao");
    if (observacaoPreview) {
        observacaoPreview.innerText = obterObservacaoFinalPreview(acaoAplicada);
    }

    const emitidoEm = ocorrenciaAtual?.criado_em
        ? `Emitido em ${formatarDataHora(ocorrenciaAtual.criado_em)}`
        : `Emitido em ${new Date().toLocaleString("pt-BR")}`;
    definirTextoPreview("previewEmitidoEm", emitidoEm, "Emitido automaticamente no momento do registro.");
}

function atualizarSelectAulasPorTurma(turmaId, faixaSelecionada = null) {
    const select = el("ocorrenciaAula");
    const turma = obterTurmaOpcaoPorId(turmaId);

    select.innerHTML = "";
    if (!turma || !turma.turno_valido || Number(turma.aulas || 0) <= 0) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = "Configure o turno da turma no painel admin";
        option.disabled = true;
        option.selected = true;
        select.appendChild(option);
        select.disabled = true;
        return;
    }

    const faixasTurma = faixasDisponiveisTurma(turma);
    const faixasManha = faixasTurma.filter((faixa) => faixa <= MAX_AULAS_EXIBICAO);
    const faixasTarde = faixasTurma.filter((faixa) => faixa > MAX_AULAS_EXIBICAO);

    const adicionarSeparadorTurno = (rotulo) => {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = `----- ${rotulo} -----`;
        option.disabled = true;
        select.appendChild(option);
    };

    const adicionarOpcaoFaixa = (faixa) => {
        const aulaTurno = aulaTurnoPorFaixa(turma.turno, faixa);
        const option = document.createElement("option");
        option.value = String(faixa);
        option.innerText = aulaTurno > 0
            ? `${aulaLabel(aulaTurno)}`
            : `Faixa ${faixa}`;
        select.appendChild(option);
    };

    if (faixasManha.length > 0) {
        adicionarSeparadorTurno("Matutino");
        faixasManha.forEach(adicionarOpcaoFaixa);
    }
    if (faixasTarde.length > 0) {
        adicionarSeparadorTurno("Vespertino");
        faixasTarde.forEach(adicionarOpcaoFaixa);
    }

    select.disabled = false;
    const faixaPreferida = Number(faixaSelecionada || 0);
    if (faixaPreferida > 0 && faixasTurma.includes(faixaPreferida)) {
        select.value = String(faixaPreferida);
    } else {
        select.value = faixasTurma.length > 0 ? String(faixasTurma[0]) : "";
    }
}

function limparFormularioOcorrencia({ manterAberto = false } = {}) {
    el("formOcorrencia").reset();
    ocorrenciaEmEdicaoId = null;
    el("ocorrenciaEstudanteId").value = "";
    el("ocorrenciaProfessorRequerenteId").value = "";
    ocultarTodasSugestoes();

    const turmaSelect = el("ocorrenciaTurmaId");
    if (opcoesOcorrencias.turmas.length > 0) {
        turmaSelect.value = String(opcoesOcorrencias.turmas[0].id);
    }
    atualizarSelectAulasPorTurma(turmaSelect.value);

    const hoje = new Date();
    el("ocorrenciaData").value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
    if (opcoesOcorrencias.status_padrao) {
        el("ocorrenciaStatus").value = opcoesOcorrencias.status_padrao;
    }
    renderSelecionadorRegimento([]);
    el("tituloFormOcorrencia").innerText = "Nova ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "none";
    if (manterAberto) {
        mostrarPainelFormularioOcorrencia();
    } else {
        ocultarPainelFormularioOcorrencia();
    }
    atualizarPreviewOcorrencia();
}

function preencherFormularioOcorrencia(ocorrencia) {
    ocorrenciaEmEdicaoId = Number(ocorrencia.id);
    el("ocorrenciaBuscaEstudante").value = ocorrencia.nome_estudante || "";
    el("ocorrenciaEstudanteId").value = ocorrencia.estudante_id || "";
    el("ocorrenciaBuscaRegimento").value = "";

    const turmaId = String(ocorrencia.turma_id || "");
    el("ocorrenciaTurmaId").value = turmaId;

    const turmaAtual = obterTurmaOpcaoPorId(turmaId);
    const faixaAula = resolverFaixaOcorrenciaParaTurma(turmaAtual, ocorrencia.aula);
    atualizarSelectAulasPorTurma(turmaId, faixaAula);

    const professorPorId = obterProfessorOpcaoPorId(ocorrencia.professor_requerente_id);
    if (professorPorId) {
        el("ocorrenciaBuscaProfessor").value = professorPorId.label || professorPorId.nome || "";
        el("ocorrenciaProfessorRequerenteId").value = String(professorPorId.id);
    } else {
        const professorPorNome = (opcoesOcorrencias.professores || []).find(
            (professor) => String(professor.nome || "").trim().toLowerCase() === String(ocorrencia.professor_requerente || "").trim().toLowerCase()
        );
        el("ocorrenciaBuscaProfessor").value = professorPorNome
            ? (professorPorNome.label || professorPorNome.nome || "")
            : (ocorrencia.professor_requerente || "");
        el("ocorrenciaProfessorRequerenteId").value = professorPorNome ? String(professorPorNome.id) : "";
    }

    el("ocorrenciaDisciplina").value = ocorrencia.disciplina || "";
    el("ocorrenciaData").value = ocorrencia.data_ocorrencia || "";
    el("ocorrenciaHorario").value = ocorrencia.horario_ocorrencia || "";
    el("ocorrenciaDescricao").value = ocorrencia.descricao || "";
    renderSelecionadorRegimento(obterIdsRegimentoSelecionadosOcorrencia(ocorrencia));
    el("ocorrenciaAcaoAplicada").value = ocorrencia.acao_aplicada || "";
    el("ocorrenciaStatus").value = ocorrencia.status || opcoesOcorrencias.status_padrao || "registrado";
    el("tituloFormOcorrencia").innerText = "Editar ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "inline-block";
    ativarAbaCoordenacao("ocorrencias");
    mostrarPainelFormularioOcorrencia({ scroll: true });
    atualizarPreviewOcorrencia();
}

function selecionarOcorrencia(ocorrencia) {
    ocorrenciaSelecionadaId = ocorrencia ? Number(ocorrencia.id || 0) || null : null;
    renderDetalhesOcorrencia(ocorrencia || null);
    renderTabelaOcorrencias();
}

function obterNomeArquivoContentDisposition(contentDisposition, ocorrencia) {
    const header = String(contentDisposition || "");
    const match = header.match(/filename="?([^";]+)"?/i);
    if (match && match[1]) {
        return match[1];
    }

    const nomeBase = String(ocorrencia?.nome_estudante || "ocorrencia")
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "") || "ocorrencia";
    return `registro_ocorrencia_${nomeBase}.pdf`;
}

async function abrirPdfOcorrencia(ocorrencia) {
    if (!ocorrencia?.id) {
        setMensagemOcorrencias("Selecione uma ocorrencia valida para gerar o PDF.", true);
        return;
    }

    let blobUrl = "";
    setMensagemOcorrencias("Gerando PDF da ocorrencia...");

    try {
        const resposta = await fetchResposta(`/ocorrencias/${ocorrencia.id}/pdf`, { headers });
        const blob = await resposta.blob();
        const nomeArquivo = obterNomeArquivoContentDisposition(
            resposta.headers.get("content-disposition"),
            ocorrencia
        );

        blobUrl = URL.createObjectURL(blob);
        const novaGuia = window.open(blobUrl, "_blank", "noopener");

        if (!novaGuia) {
            const link = document.createElement("a");
            link.href = blobUrl;
            link.download = nomeArquivo;
            document.body.appendChild(link);
            link.click();
            link.remove();
            setMensagemOcorrencias("PDF gerado e baixado para impressao.");
        } else {
            novaGuia.focus();
            setMensagemOcorrencias("PDF gerado e aberto em nova guia.");
        }

        window.setTimeout(() => {
            URL.revokeObjectURL(blobUrl);
        }, 60000);
    } catch (err) {
        if (blobUrl) {
            URL.revokeObjectURL(blobUrl);
        }
        setMensagemOcorrencias(
            err?.message || "Nao foi possivel gerar o PDF da ocorrencia.",
            true
        );
    }
}

function criarBlocoDetalhesRegimento(ocorrencia) {
    const wrapper = document.createElement("div");
    wrapper.className = "coordenacao-detail-block";

    const titulo = document.createElement("strong");
    titulo.className = "coordenacao-detail-block-title";
    titulo.innerText = "Base legal vinculada";
    wrapper.appendChild(titulo);

    const itens = Array.isArray(ocorrencia?.regimento_itens) ? ocorrencia.regimento_itens : [];
    if (itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-detail-hint";
        vazio.innerText = "Nenhum item de base legal vinculado a esta ocorrencia.";
        wrapper.appendChild(vazio);
        return wrapper;
    }

    const lista = document.createElement("div");
    lista.className = "coordenacao-detail-list";

    itens.forEach((item) => {
        const artigo = document.createElement("div");
        artigo.className = "coordenacao-detail-list-item";

        const artigoTitulo = document.createElement("strong");
        artigoTitulo.innerText = item.artigo || "Sem artigo";

        const descricao = document.createElement("span");
        descricao.innerText = item.descricao || "Sem descricao.";

        artigo.appendChild(artigoTitulo);
        artigo.appendChild(descricao);
        lista.appendChild(artigo);
    });

    wrapper.appendChild(lista);
    return wrapper;
}

function renderDetalhesOcorrencia(ocorrencia) {
    const container = el("detalhesOcorrencia");
    if (!container) return;
    if (!ocorrencia) {
        container.innerText = "Selecione uma ocorrencia para visualizar os detalhes.";
        return;
    }

    container.innerHTML = "";
    const actions = document.createElement("div");
    actions.className = "coordenacao-detail-actions";

    const btnPdf = document.createElement("button");
    btnPdf.type = "button";
    btnPdf.className = "btn-destaque";
    btnPdf.innerText = "Gerar PDF para impressao";
    btnPdf.addEventListener("click", () => {
        abrirPdfOcorrencia(ocorrencia);
    });
    actions.appendChild(btnPdf);
    container.appendChild(actions);

    const hint = document.createElement("p");
    hint.className = "coordenacao-detail-hint";
    hint.innerText = "Use este documento para impressao e anexo fisico no livro de registro.";
    container.appendChild(hint);

    const campos = [
        ["Estudante", ocorrencia.nome_estudante],
        ["Turma", ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`],
        ["Professor requerente", ocorrencia.professor_requerente],
        ["Disciplina", ocorrencia.disciplina],
        ["Data", formatarDataBr(ocorrencia.data_ocorrencia)],
        ["Aula", formatarAulaOcorrencia(ocorrencia)],
        ["Horario", ocorrencia.horario_ocorrencia],
        ["Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)],
        ["Status", rotuloStatus(ocorrencia.status)],
        ["Descricao", ocorrencia.descricao],
        ["Criado em", formatarDataHora(ocorrencia.criado_em)],
        ["Atualizado em", formatarDataHora(ocorrencia.atualizado_em)]
    ];

    campos.forEach(([rotulo, valor]) => {
        const linha = document.createElement("p");
        linha.className = "coordenacao-detail-line";
        const strong = document.createElement("strong");
        strong.innerText = `${rotulo}: `;
        const span = document.createElement("span");
        span.innerText = valor || "Nao informado";
        linha.appendChild(strong);
        linha.appendChild(span);
        container.appendChild(linha);
    });

    container.appendChild(criarBlocoDetalhesRegimento(ocorrencia));
}

function valorCampo(id) {
    return String(el(id)?.value || "").trim();
}

function montarQueryOcorrencias({
    nomeEstudanteId,
    turmaIdId,
    statusId,
    dataInicialId,
    dataFinalId
}) {
    const params = new URLSearchParams();
    const nomeEstudante = valorCampo(nomeEstudanteId);
    const turmaId = valorCampo(turmaIdId);
    const status = valorCampo(statusId);
    const dataInicial = valorCampo(dataInicialId);
    const dataFinal = valorCampo(dataFinalId);

    if (nomeEstudante) params.set("nome_estudante", nomeEstudante);
    if (turmaId) params.set("turma_id", turmaId);
    if (status) params.set("status", status);
    if (dataInicial) params.set("data_inicial", dataInicial);
    if (dataFinal) params.set("data_final", dataFinal);

    return params.toString() ? `?${params.toString()}` : "";
}

function descreverFiltrosOcorrencias(configuracao) {
    const partes = [];
    const nomeEstudante = valorCampo(configuracao.nomeEstudanteId);
    const turmaId = valorCampo(configuracao.turmaIdId);
    const status = valorCampo(configuracao.statusId);
    const dataInicial = valorCampo(configuracao.dataInicialId);
    const dataFinal = valorCampo(configuracao.dataFinalId);

    if (nomeEstudante) {
        partes.push(`Estudante: ${nomeEstudante}`);
    }
    if (turmaId) {
        const turma = obterTurmaOpcaoPorId(turmaId);
        partes.push(`Turma: ${turma?.nome || `ID ${turmaId}`}`);
    }
    if (status) {
        partes.push(`Status: ${rotuloStatus(status)}`);
    }
    if (dataInicial && dataFinal) {
        partes.push(`Periodo: ${formatarDataBr(dataInicial)} ate ${formatarDataBr(dataFinal)}`);
    } else if (dataInicial) {
        partes.push(`A partir de: ${formatarDataBr(dataInicial)}`);
    } else if (dataFinal) {
        partes.push(`Ate: ${formatarDataBr(dataFinal)}`);
    }

    return partes.length > 0 ? partes.join(" | ") : "Sem filtro aplicado.";
}

function totalOcorrenciasPorStatus(lista, status) {
    return (lista || []).filter((ocorrencia) => String(ocorrencia.status || "").trim() === status).length;
}

function atualizarResumoOcorrencias() {
    const total = ocorrenciasCache.length;
    const acompanhamento = totalOcorrenciasPorStatus(ocorrenciasCache, "em_acompanhamento");
    const aguardando = totalOcorrenciasPorStatus(ocorrenciasCache, "aguardando_responsavel");
    const resolvido = totalOcorrenciasPorStatus(ocorrenciasCache, "resolvido");

    if (el("resumoOcorrenciasTotal")) {
        el("resumoOcorrenciasTotal").innerText = String(total);
    }
    if (el("resumoOcorrenciasAcompanhamento")) {
        el("resumoOcorrenciasAcompanhamento").innerText = String(acompanhamento);
    }
    if (el("resumoOcorrenciasAguardando")) {
        el("resumoOcorrenciasAguardando").innerText = String(aguardando);
    }
    if (el("resumoOcorrenciasResolvido")) {
        el("resumoOcorrenciasResolvido").innerText = String(resolvido);
    }
    if (el("resumoOcorrenciasPeriodo")) {
        el("resumoOcorrenciasPeriodo").innerText = descreverFiltrosOcorrencias({
            nomeEstudanteId: "filtroNomeEstudante",
            turmaIdId: "filtroTurmaId",
            statusId: "filtroStatus",
            dataInicialId: "filtroDataInicial",
            dataFinalId: "filtroDataFinal"
        });
    }
}

function agruparOcorrencias(lista, obterChave, obterRotulo) {
    const mapa = new Map();

    (lista || []).forEach((ocorrencia) => {
        const chaveBruta = obterChave(ocorrencia);
        const rotuloBruto = obterRotulo(ocorrencia);
        const chave = String(chaveBruta || rotuloBruto || "nao_informado").trim();
        const rotulo = String(rotuloBruto || chaveBruta || "Nao informado").trim() || "Nao informado";
        const atual = mapa.get(chave) || { label: rotulo, total: 0 };
        atual.total += 1;
        mapa.set(chave, atual);
    });

    return Array.from(mapa.values()).sort((a, b) => {
        if (b.total !== a.total) {
            return b.total - a.total;
        }
        return a.label.localeCompare(b.label, "pt-BR");
    });
}

function renderRankingLista(idLista, itens, vazio, totalBase = 0) {
    const lista = el(idLista);
    if (!lista) return;
    lista.innerHTML = "";

    if (!Array.isArray(itens) || itens.length === 0) {
        const itemVazio = document.createElement("li");
        itemVazio.className = "coordenacao-empty-state";
        itemVazio.innerText = vazio;
        lista.appendChild(itemVazio);
        return;
    }

    itens.slice(0, 5).forEach((item) => {
        const li = document.createElement("li");
        li.className = "coordenacao-ranking-item";

        const label = document.createElement("span");
        label.className = "coordenacao-ranking-label";
        label.innerText = item.label;

        const total = document.createElement("strong");
        total.innerText = String(item.total);

        const meta = document.createElement("span");
        meta.className = "coordenacao-ranking-meta";
        if (totalBase > 0) {
            const percentual = Math.round((item.total / totalBase) * 100);
            meta.innerText = `${percentual}% do relatorio`;
        } else {
            meta.innerText = `${item.total} registro(s)`;
        }

        li.appendChild(label);
        li.appendChild(total);
        li.appendChild(meta);
        lista.appendChild(li);
    });
}

function atualizarResumoRelatorioOcorrencias() {
    const total = relatorioOcorrenciasCache.length;
    const resolvidas = totalOcorrenciasPorStatus(relatorioOcorrenciasCache, "resolvido");
    const abertas = total - resolvidas;
    const turmasImpactadas = new Set(
        relatorioOcorrenciasCache
            .map((ocorrencia) => String(ocorrencia.turma_nome || ocorrencia.turma_id || "").trim())
            .filter(Boolean)
    ).size;

    if (el("relatorioMetricasTotal")) {
        el("relatorioMetricasTotal").innerText = String(total);
    }
    if (el("relatorioMetricasAbertas")) {
        el("relatorioMetricasAbertas").innerText = String(abertas);
    }
    if (el("relatorioMetricasResolvidas")) {
        el("relatorioMetricasResolvidas").innerText = String(resolvidas);
    }
    if (el("relatorioMetricasTurmas")) {
        el("relatorioMetricasTurmas").innerText = String(turmasImpactadas);
    }

    const descricaoFiltros = descreverFiltrosOcorrencias({
        nomeEstudanteId: "relatorioNomeEstudante",
        turmaIdId: "relatorioTurmaId",
        statusId: "relatorioStatus",
        dataInicialId: "relatorioDataInicial",
        dataFinalId: "relatorioDataFinal"
    });
    if (el("relatorioPeriodo")) {
        el("relatorioPeriodo").innerText = total > 0
            ? `Recorte atual: ${descricaoFiltros}`
            : `Nenhuma ocorrencia encontrada. ${descricaoFiltros}`;
    }

    renderRankingLista(
        "relatorioResumoStatus",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.status,
            (ocorrencia) => rotuloStatus(ocorrencia.status)
        ),
        "Nenhum status encontrado para o recorte selecionado.",
        total
    );
    renderRankingLista(
        "relatorioResumoTurmas",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.turma_id,
            (ocorrencia) => ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`
        ),
        "Nenhuma turma encontrada para o recorte selecionado.",
        total
    );
    renderRankingLista(
        "relatorioResumoProfessores",
        agruparOcorrencias(
            relatorioOcorrenciasCache,
            (ocorrencia) => ocorrencia.professor_requerente_id || ocorrencia.professor_requerente,
            (ocorrencia) => ocorrencia.professor_requerente || "Nao informado"
        ),
        "Nenhum professor encontrado para o recorte selecionado.",
        total
    );
}

function renderTabelaRelatorioOcorrencias() {
    const tbody = el("tbodyRelatorioOcorrencias");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(relatorioOcorrenciasCache) || relatorioOcorrenciasCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 6;
        td.className = "booking-empty";
        td.innerText = "Nenhuma ocorrencia encontrada para o relatorio.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    relatorioOcorrenciasCache.forEach((ocorrencia) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Data", formatarDataBr(ocorrencia.data_ocorrencia)));
        tr.appendChild(criarCelulaTabela("Estudante", ocorrencia.nome_estudante || ""));
        tr.appendChild(criarCelulaTabela("Turma", ocorrencia.turma_nome || ""));
        tr.appendChild(criarCelulaTabela("Professor requerente", ocorrencia.professor_requerente || ""));
        tr.appendChild(criarCelulaTabela("Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)));
        tr.appendChild(criarCelulaTabela("Status", rotuloStatus(ocorrencia.status)));
        tbody.appendChild(tr);
    });
}

function renderRelatorioOcorrencias() {
    atualizarResumoRelatorioOcorrencias();
    renderTabelaRelatorioOcorrencias();
}

function invalidarRelatorioOcorrencias() {
    if (!relatorioOcorrenciasCarregado) return;
    relatorioOcorrenciasCarregado = false;
    setMensagemRelatorios("Dados atualizados. Gere o relatorio novamente para refletir as alteracoes.");
}

async function carregarOpcoesOcorrencias() {
    const idsRegimentoSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const opcoesApi = await fetchJson("/ocorrencias/opcoes", { headers });
    opcoesOcorrencias = {
        turmas: Array.isArray(opcoesApi.turmas) ? opcoesApi.turmas : [],
        professores: Array.isArray(opcoesApi.professores) ? opcoesApi.professores : [],
        disciplinas: Array.isArray(opcoesApi.disciplinas) ? opcoesApi.disciplinas : [],
        status: Array.isArray(opcoesApi.status) ? opcoesApi.status : [],
        acoes_aplicadas: Array.isArray(opcoesApi.acoes_aplicadas) ? opcoesApi.acoes_aplicadas : [],
        regimento_itens: Array.isArray(opcoesApi.regimento_itens) ? opcoesApi.regimento_itens : [],
        status_padrao: opcoesApi.status_padrao || "registrado"
    };
    regimentoItensCache = Array.isArray(opcoesOcorrencias.regimento_itens)
        ? opcoesOcorrencias.regimento_itens.map((item) => ({
            ...item,
            atualizado_em: item.atualizado_em || "",
            criado_em: item.criado_em || ""
        }))
        : [];

    rotulosAcao.clear();
    rotulosStatus.clear();
    (opcoesOcorrencias.acoes_aplicadas || []).forEach((item) => {
        rotulosAcao.set(String(item.id), item.nome || item.id);
    });
    (opcoesOcorrencias.status || []).forEach((item) => {
        rotulosStatus.set(String(item.id), item.nome || item.id);
    });

    preencherSelect("ocorrenciaTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    preencherSelect("relatorioTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    preencherSelect("ocorrenciaAcaoAplicada", opcoesOcorrencias.acoes_aplicadas, { placeholder: "Selecione a acao aplicada" });
    preencherSelect("ocorrenciaStatus", opcoesOcorrencias.status, {
        placeholder: "Selecione o status",
        valorPadrao: opcoesOcorrencias.status_padrao || "registrado"
    });
    preencherSelect("filtroStatus", opcoesOcorrencias.status, { incluirTodos: true });
    preencherSelect("relatorioStatus", opcoesOcorrencias.status, { incluirTodos: true });

    preencherSelect("estudanteTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroEstudanteTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
    popularSugestoesProfessores();
    popularSugestoesDisciplinas();
    popularSugestoesRegimento();

    const turmaInicial = opcoesOcorrencias.turmas[0];
    atualizarSelectAulasPorTurma(turmaInicial ? turmaInicial.id : "");
    renderSelecionadorRegimento(idsRegimentoSelecionados);
    atualizarPreviewOcorrencia();
}

function queryFiltrosOcorrencias() {
    return montarQueryOcorrencias({
        nomeEstudanteId: "filtroNomeEstudante",
        turmaIdId: "filtroTurmaId",
        statusId: "filtroStatus",
        dataInicialId: "filtroDataInicial",
        dataFinalId: "filtroDataFinal"
    });
}

function queryFiltrosRelatorioOcorrencias() {
    return montarQueryOcorrencias({
        nomeEstudanteId: "relatorioNomeEstudante",
        turmaIdId: "relatorioTurmaId",
        statusId: "relatorioStatus",
        dataInicialId: "relatorioDataInicial",
        dataFinalId: "relatorioDataFinal"
    });
}

function queryFiltrosEstudantes() {
    const params = new URLSearchParams();
    const nome = el("filtroEstudanteNome").value.trim();
    const turmaId = el("filtroEstudanteTurmaId").value;
    if (nome) params.set("nome", nome);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("incluir_inativos", "true");
    return `?${params.toString()}`;
}

function criarCelulaTabela(rotulo, conteudo = "") {
    const td = document.createElement("td");
    td.dataset.label = rotulo;
    if (typeof Node !== "undefined" && conteudo instanceof Node) {
        td.appendChild(conteudo);
    } else {
        td.innerText = conteudo ?? "";
    }
    return td;
}

function renderTabelaOcorrencias() {
    const tbody = el("tbodyOcorrencias");
    atualizarResumoOcorrencias();
    tbody.innerHTML = "";

    if (!Array.isArray(ocorrenciasCache) || ocorrenciasCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 7;
        td.className = "booking-empty";
        td.innerText = "Nenhuma ocorrencia encontrada.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    ocorrenciasCache.forEach((ocorrencia) => {
        const tr = document.createElement("tr");
        const selecionada = Number(ocorrencia.id) === Number(ocorrenciaSelecionadaId);
        tr.classList.toggle("is-selected", selecionada);
        tr.addEventListener("click", () => {
            selecionarOcorrencia(ocorrencia);
        });

        tr.appendChild(criarCelulaTabela("Data", formatarDataBr(ocorrencia.data_ocorrencia)));
        tr.appendChild(criarCelulaTabela("Estudante", ocorrencia.nome_estudante || ""));
        tr.appendChild(criarCelulaTabela("Turma", ocorrencia.turma_nome || ""));
        tr.appendChild(criarCelulaTabela("Professor requerente", ocorrencia.professor_requerente || ""));
        tr.appendChild(criarCelulaTabela("Acao aplicada", rotuloAcao(ocorrencia.acao_aplicada)));

        const statusBadge = document.createElement("span");
        statusBadge.className = `status-chip ${classeStatus(ocorrencia.status)}`;
        statusBadge.innerText = rotuloStatus(ocorrencia.status);
        tr.appendChild(criarCelulaTabela("Status", statusBadge));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnVer = document.createElement("button");
        btnVer.type = "button";
        btnVer.innerText = "Ver";
        btnVer.addEventListener("click", (event) => {
            event.stopPropagation();
            selecionarOcorrencia(ocorrencia);
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", (event) => {
            event.stopPropagation();
            selecionarOcorrencia(ocorrencia);
            preencherFormularioOcorrencia(ocorrencia);
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", (event) => {
            event.stopPropagation();
            excluirOcorrencia(ocorrencia);
        });

        linhaAcoes.appendChild(btnVer);
        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));

        tbody.appendChild(tr);
    });
}

function renderTabelaEstudantes() {
    const tbody = el("tbodyEstudantes");
    tbody.innerHTML = "";

    const filtroStatus = el("filtroEstudanteStatus").value;
    const estudantesFiltrados = (estudantesCache || []).filter((estudante) => {
        if (filtroStatus === "ativos") return Boolean(estudante.ativo);
        if (filtroStatus === "inativos") return !Boolean(estudante.ativo);
        return true;
    });

    if (estudantesFiltrados.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.className = "booking-empty";
        td.innerText = "Nenhum estudante encontrado.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    estudantesFiltrados.forEach((estudante) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Nome", estudante.nome || ""));
        tr.appendChild(criarCelulaTabela("Turma", estudante.turma_nome || ""));

        const badge = document.createElement("span");
        badge.className = `status-chip ${classeStatusEstudante(Boolean(estudante.ativo))}`;
        badge.innerText = estudante.ativo ? "Ativo" : "Inativo";
        tr.appendChild(criarCelulaTabela("Status", badge));
        tr.appendChild(criarCelulaTabela("Atualizado em", formatarDataHora(estudante.atualizado_em)));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => iniciarEdicaoEstudante(estudante));

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = estudante.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/estudantes/${estudante.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(estudante.ativo) })
                });
                setMensagemEstudantes("Status atualizado.");
                await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
            } catch (err) {
                setMensagemEstudantes(err.message, true);
            }
        });

        const btnExcluir = document.createElement("button");
        btnExcluir.type = "button";
        btnExcluir.className = "coordenacao-btn-danger";
        btnExcluir.innerText = "Excluir";
        btnExcluir.addEventListener("click", () => {
            excluirEstudante(estudante);
        });

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnStatus);
        linhaAcoes.appendChild(btnExcluir);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));

        tbody.appendChild(tr);
    });
}

async function carregarOcorrencias() {
    ocorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosOcorrencias()}`, { headers });
    const ocorrenciaSelecionada = ocorrenciasCache.find(
        (ocorrencia) => Number(ocorrencia.id) === Number(ocorrenciaSelecionadaId)
    ) || null;

    if (ocorrenciaSelecionada) {
        renderDetalhesOcorrencia(ocorrenciaSelecionada);
    } else if (ocorrenciaSelecionadaId) {
        ocorrenciaSelecionadaId = null;
        renderDetalhesOcorrencia(null);
    }

    renderTabelaOcorrencias();
}

async function carregarRelatorioOcorrencias() {
    setMensagemRelatorios("");
    relatorioOcorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosRelatorioOcorrencias()}`, { headers });
    relatorioOcorrenciasCarregado = true;
    renderRelatorioOcorrencias();
}

async function carregarEstudantes() {
    estudantesCache = await fetchJson(`/estudantes${queryFiltrosEstudantes()}`, { headers });
    renderTabelaEstudantes();
}

function renderTabelaRegimento() {
    const tbody = el("tbodyRegimento");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(regimentoItensCache) || regimentoItensCache.length === 0) {
        const tr = document.createElement("tr");
        const td = document.createElement("td");
        td.colSpan = 5;
        td.className = "booking-empty";
        td.innerText = "Nenhum item da base legal cadastrado.";
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
    }

    regimentoItensCache.forEach((item) => {
        const tr = document.createElement("tr");
        tr.appendChild(criarCelulaTabela("Artigo", item.artigo || ""));
        tr.appendChild(criarCelulaTabela("Descricao", item.descricao || ""));

        const badge = document.createElement("span");
        badge.className = `status-chip ${classeStatusEstudante(Boolean(item.ativo))}`;
        badge.innerText = item.ativo ? "Ativo" : "Inativo";
        tr.appendChild(criarCelulaTabela("Status", badge));
        tr.appendChild(criarCelulaTabela("Atualizado em", formatarDataHora(item.atualizado_em)));

        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoRegimento(item);
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = item.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
            try {
                await fetchJson(`/regimento-itens/${item.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(item.ativo) })
                });
                setMensagemRegimento("Status da base legal atualizado.");
                await carregarRegimentoItens(idsSelecionados);
            } catch (err) {
                setMensagemRegimento(err.message, true);
            }
        });

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnStatus);
        tr.appendChild(criarCelulaTabela("Acoes", linhaAcoes));

        tbody.appendChild(tr);
    });
}

async function carregarRegimentoItens(idsSelecionados = null) {
    const idsPreferidos = idsSelecionados === null
        ? obterIdsRegimentoSelecionadosFormulario()
        : idsSelecionados;
    regimentoItensCache = await fetchJson("/regimento-itens?incluir_inativos=true", { headers });
    opcoesOcorrencias.regimento_itens = Array.isArray(regimentoItensCache)
        ? regimentoItensCache.map((item) => ({
            ...item,
            label: item.artigo || `Item ${item.id}`
        }))
        : [];
    popularSugestoesRegimento();
    renderTabelaRegimento();
    renderSelecionadorRegimento(idsPreferidos);
    atualizarPreviewOcorrencia();
}

function limparFormularioRegimento() {
    regimentoItemEmEdicao = null;
    el("formRegimento").reset();
    el("tituloFormRegimento").innerText = "Cadastrar base legal";
    el("btnCancelarEdicaoRegimento").style.display = "none";
}

function iniciarEdicaoRegimento(item) {
    regimentoItemEmEdicao = item;
    el("regimentoArtigo").value = item.artigo || "";
    el("regimentoDescricao").value = item.descricao || "";
    el("tituloFormRegimento").innerText = "Editar base legal";
    el("btnCancelarEdicaoRegimento").style.display = "inline-block";
    ativarAbaCoordenacao("regimento");
}

async function salvarRegimento(event) {
    event.preventDefault();
    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const payload = {
        artigo: el("regimentoArtigo").value.trim(),
        descricao: el("regimentoDescricao").value.trim()
    };

    try {
        if (regimentoItemEmEdicao) {
            await fetchJson(`/regimento-itens/${regimentoItemEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({
                    ...payload,
                    ativo: Boolean(regimentoItemEmEdicao.ativo)
                })
            });
            setMensagemRegimento("Base legal atualizada com sucesso.");
        } else {
            await fetchJson("/regimento-itens", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemRegimento("Base legal cadastrada com sucesso.");
        }

        limparFormularioRegimento();
        await carregarRegimentoItens(idsSelecionados);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

function limparFormularioEstudante() {
    estudanteEmEdicao = null;
    el("formEstudante").reset();
    el("tituloFormEstudante").innerText = "Cadastrar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "none";
}

function iniciarEdicaoEstudante(estudante) {
    estudanteEmEdicao = estudante;
    el("estudanteNome").value = estudante.nome || "";
    el("estudanteTurmaId").value = String(estudante.turma_id || "");
    el("tituloFormEstudante").innerText = "Editar estudante";
    el("btnCancelarEdicaoEstudante").style.display = "inline-block";
    ativarAbaCoordenacao("estudantes");
}

function aplicarSelecaoEstudantePorTexto() {
    const input = el("ocorrenciaBuscaEstudante");
    const hidden = el("ocorrenciaEstudanteId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaEstudantes, texto);
    if (!item) {
        hidden.value = "";
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    input.value = String(item.nome || item.label || texto).trim();
    hidden.value = String(item.id);
    el("ocorrenciaTurmaId").value = String(item.turma_id);
    atualizarSelectAulasPorTurma(item.turma_id);
    ocultarSugestoes("listaEstudantesBusca");
}

function aplicarSelecaoProfessorPorTexto() {
    const input = el("ocorrenciaBuscaProfessor");
    const hidden = el("ocorrenciaProfessorRequerenteId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        ocultarSugestoes("listaProfessoresBusca");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaProfessores, texto, opcoesOcorrencias.professores || []);
    if (item) {
        input.value = String(item.nome || item.label || texto).trim();
    }
    hidden.value = item ? String(item.id) : "";
    ocultarSugestoes("listaProfessoresBusca");
}

function aplicarSelecaoDisciplinaPorTexto() {
    const input = el("ocorrenciaDisciplina");
    const texto = input.value.trim();
    if (!texto) {
        ocultarSugestoes("listaDisciplinasBusca");
        return;
    }

    const item = obterItemSugestaoPorTexto(mapaBuscaDisciplinas, texto, opcoesOcorrencias.disciplinas || []);
    if (item) {
        input.value = String(item.nome || item.label || texto).trim();
    }
    ocultarSugestoes("listaDisciplinasBusca");
}

function selecionarSugestaoEstudante(item) {
    if (!item) return;
    el("ocorrenciaBuscaEstudante").value = String(item.nome || item.label || "").trim();
    el("ocorrenciaEstudanteId").value = String(item.id || "");
    if (item.turma_id) {
        el("ocorrenciaTurmaId").value = String(item.turma_id);
        atualizarSelectAulasPorTurma(item.turma_id);
    }
    atualizarPreviewOcorrencia();
}

function selecionarSugestaoProfessor(item) {
    if (!item) return;
    el("ocorrenciaBuscaProfessor").value = String(item.nome || item.label || "").trim();
    el("ocorrenciaProfessorRequerenteId").value = String(item.id || "");
    atualizarPreviewOcorrencia();
}

function selecionarSugestaoDisciplina(item) {
    if (!item) return;
    el("ocorrenciaDisciplina").value = String(item.nome || item.label || "").trim();
    atualizarPreviewOcorrencia();
}

function filtrarSugestoesLocais(itens, termo, { limite = 12, campos = ["nome", "label"] } = {}) {
    const lista = Array.isArray(itens) ? itens : [];
    const termoLimpo = String(termo || "").trim().toLowerCase();
    if (!termoLimpo) {
        return lista.slice(0, limite);
    }

    return lista.filter((item) => campos.some((campo) => {
        const valor = String(item?.[campo] || "").trim().toLowerCase();
        return valor.includes(termoLimpo);
    })).slice(0, limite);
}

async function atualizarSugestoesEstudantesBusca(forcar = false) {
    const input = el("ocorrenciaBuscaEstudante");
    const termo = input.value.trim();
    const turmaId = el("ocorrenciaTurmaId").value;
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaEstudantesBusca");
        return;
    }

    const params = new URLSearchParams();
    params.set("q", termo);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("limite", "20");
    const itens = await fetchJson(`/ocorrencias/busca/estudantes?${params.toString()}`, { headers });
    preencherDatalist("listaEstudantesBusca", mapaBuscaEstudantes, itens, {
        onSelect: selecionarSugestaoEstudante,
        textoVazio: "Nenhum estudante encontrado."
    });
}

function agendarBuscaEstudantes() {
    if (timerBuscaEstudantes) clearTimeout(timerBuscaEstudantes);
    timerBuscaEstudantes = setTimeout(() => {
        atualizarSugestoesEstudantesBusca().catch((err) => setMensagemOcorrencias(err.message, true));
    }, 250);
}

function atualizarSugestoesProfessoresBusca(forcar = false) {
    const termo = el("ocorrenciaBuscaProfessor").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaProfessoresBusca");
        return;
    }

    const itens = filtrarSugestoesLocais(opcoesOcorrencias.professores, termo, {
        limite: 12,
        campos: ["nome", "email", "label"]
    });
    preencherDatalist("listaProfessoresBusca", mapaBuscaProfessores, itens, {
        onSelect: selecionarSugestaoProfessor,
        textoVazio: "Nenhum professor encontrado."
    });
}

function atualizarSugestoesDisciplinasBusca(forcar = false) {
    const termo = el("ocorrenciaDisciplina").value.trim();
    if (!forcar && termo.length < 1) {
        ocultarSugestoes("listaDisciplinasBusca");
        return;
    }

    const itens = filtrarSugestoesLocais(opcoesOcorrencias.disciplinas, termo, {
        limite: 12,
        campos: ["nome", "label"]
    });
    preencherDatalist("listaDisciplinasBusca", mapaBuscaDisciplinas, itens, {
        onSelect: selecionarSugestaoDisciplina,
        textoVazio: "Nenhuma disciplina encontrada."
    });
}

function montarPayloadOcorrencia() {
    const textoEstudante = el("ocorrenciaBuscaEstudante").value.trim();
    const itemEstudante = obterItemSugestaoPorTexto(mapaBuscaEstudantes, textoEstudante);
    const textoProfessor = el("ocorrenciaBuscaProfessor").value.trim();
    const itemProfessor = obterItemSugestaoPorTexto(mapaBuscaProfessores, textoProfessor, opcoesOcorrencias.professores || []);

    const estudanteIdHidden = Number(el("ocorrenciaEstudanteId").value || 0);
    const professorIdSelecionado = Number(el("ocorrenciaProfessorRequerenteId").value || 0);
    const professorSelecionado = professorIdSelecionado > 0
        ? obterProfessorOpcaoPorId(professorIdSelecionado)
        : itemProfessor;

    const estudanteId = estudanteIdHidden || (itemEstudante ? Number(itemEstudante.id) : 0);
    const nomeEstudante = itemEstudante ? itemEstudante.nome : textoEstudante;

    return {
        nome_estudante: nomeEstudante || null,
        estudante_id: estudanteId > 0 ? estudanteId : null,
        turma_id: Number(el("ocorrenciaTurmaId").value),
        professor_requerente: professorSelecionado ? professorSelecionado.nome : (textoProfessor || null),
        professor_requerente_id: professorSelecionado ? Number(professorSelecionado.id) : null,
        disciplina: el("ocorrenciaDisciplina").value.trim(),
        data_ocorrencia: el("ocorrenciaData").value,
        aula: String(el("ocorrenciaAula").value || "").trim(),
        horario_ocorrencia: el("ocorrenciaHorario").value.trim(),
        descricao: el("ocorrenciaDescricao").value.trim(),
        regimento_item_ids: obterIdsRegimentoSelecionadosFormulario(),
        acao_aplicada: el("ocorrenciaAcaoAplicada").value,
        status: el("ocorrenciaStatus").value || opcoesOcorrencias.status_padrao || "registrado"
    };
}

async function salvarOcorrencia(event) {
    event.preventDefault();
    const payload = montarPayloadOcorrencia();

    try {
        let ocorrencia;
        if (ocorrenciaEmEdicaoId) {
            ocorrencia = await fetchJson(`/ocorrencias/${ocorrenciaEmEdicaoId}`, {
                method: "PATCH",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemOcorrencias("Ocorrencia atualizada com sucesso.");
        } else {
            ocorrencia = await fetchJson("/ocorrencias", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemOcorrencias("Ocorrencia registrada com sucesso.");
        }

        limparFormularioOcorrencia();
        invalidarRelatorioOcorrencias();
        await carregarOcorrencias();
        selecionarOcorrencia(ocorrencia);
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function filtrarOcorrencias(event) {
    event.preventDefault();
    try {
        await carregarOcorrencias();
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function limparFiltrosOcorrencias() {
    el("formFiltrosOcorrencias").reset();
    try {
        await carregarOcorrencias();
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function filtrarRelatorioOcorrencias(event) {
    event.preventDefault();
    try {
        await carregarRelatorioOcorrencias();
    } catch (err) {
        setMensagemRelatorios(err.message, true);
    }
}

async function limparFiltrosRelatorioOcorrencias() {
    el("formRelatorioOcorrencias").reset();
    try {
        await carregarRelatorioOcorrencias();
    } catch (err) {
        setMensagemRelatorios(err.message, true);
    }
}

async function excluirOcorrencia(ocorrencia) {
    const nomeEstudante = String(ocorrencia?.nome_estudante || "este registro").trim();
    const confirmou = window.confirm(`Excluir a ocorrencia de ${nomeEstudante}? Esta acao nao pode ser desfeita.`);
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/ocorrencias/${ocorrencia.id}`,
            `/ocorrencias/${ocorrencia.id}/excluir`
        );

        if (Number(ocorrenciaEmEdicaoId) === Number(ocorrencia.id)) {
            limparFormularioOcorrencia();
        }
        if (Number(ocorrenciaSelecionadaId) === Number(ocorrencia.id)) {
            selecionarOcorrencia(null);
        }

        invalidarRelatorioOcorrencias();
        await carregarOcorrencias();
        setMensagemOcorrencias(resposta?.mensagem || "Ocorrencia excluida com sucesso.");
    } catch (err) {
        setMensagemOcorrencias(err.message, true);
    }
}

async function excluirEstudante(estudante) {
    const nomeEstudante = String(estudante?.nome || "este estudante").trim();
    const confirmou = window.confirm(
        `Excluir o cadastro de ${nomeEstudante}? As ocorrencias ja registradas serao preservadas no historico.`
    );
    if (!confirmou) return;

    try {
        const resposta = await requisitarExclusao(
            `/estudantes/${estudante.id}`,
            `/estudantes/${estudante.id}/excluir`
        );

        if (Number(estudanteEmEdicao?.id) === Number(estudante.id)) {
            limparFormularioEstudante();
        }
        if (Number(el("ocorrenciaEstudanteId")?.value || 0) === Number(estudante.id)) {
            el("ocorrenciaEstudanteId").value = "";
        }

        invalidarRelatorioOcorrencias();
        await Promise.all([
            carregarEstudantes(),
            carregarOcorrencias(),
            atualizarSugestoesEstudantesBusca(true)
        ]);

        const totalDesvinculado = Number(resposta?.ocorrencias_desvinculadas || 0);
        const sufixo = totalDesvinculado > 0
            ? ` ${totalDesvinculado} ocorrencia(s) ficaram apenas com o nome do estudante no historico.`
            : "";
        setMensagemEstudantes((resposta?.mensagem || "Estudante excluido com sucesso.") + sufixo);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function salvarEstudante(event) {
    event.preventDefault();
    const payload = {
        nome: el("estudanteNome").value.trim(),
        turma_id: Number(el("estudanteTurmaId").value)
    };

    try {
        if (estudanteEmEdicao) {
            await fetchJson(`/estudantes/${estudanteEmEdicao.id}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify({
                    ...payload,
                    ativo: Boolean(estudanteEmEdicao.ativo)
                })
            });
            setMensagemEstudantes("Estudante atualizado com sucesso.");
        } else {
            await fetchJson("/estudantes", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagemEstudantes("Estudante cadastrado com sucesso.");
        }

        limparFormularioEstudante();
        await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function importarEstudantesCsv(event) {
    event.preventDefault();
    const arquivo = el("arquivoCsvEstudantes")?.files?.[0];
    if (!arquivo) {
        setMensagemEstudantes("Selecione um arquivo CSV para importar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/estudantes/importar-csv", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagemEstudantes(comporMensagemImportacaoCsv(resposta), houveFalhaImportacao(resposta));
        el("formImportarEstudantesCsv").reset();
        await Promise.all([carregarEstudantes(), atualizarSugestoesEstudantesBusca(true)]);
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function importarRegimentoCsv(event) {
    event.preventDefault();
    const arquivo = el("arquivoCsvRegimento")?.files?.[0];
    if (!arquivo) {
        setMensagemRegimento("Selecione um arquivo CSV para importar.", true);
        return;
    }

    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/regimento-itens/importar-csv", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagemRegimento(comporMensagemImportacaoCsv(resposta), houveFalhaImportacao(resposta));
        el("formImportarRegimentoCsv").reset();
        await carregarRegimentoItens(idsSelecionados);
    } catch (err) {
        setMensagemRegimento(err.message, true);
    }
}

function baixarModeloEstudantesCsv() {
    baixarArquivoTexto("modelo_estudantes.csv", MODELO_CSV_ESTUDANTES);
}

function baixarModeloRegimentoCsv() {
    baixarArquivoTexto("modelo_base_legal.csv", MODELO_CSV_BASE_LEGAL);
}

async function filtrarEstudantes(event) {
    event.preventDefault();
    try {
        await carregarEstudantes();
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function limparFiltrosEstudantes() {
    el("formFiltrosEstudantes").reset();
    try {
        await carregarEstudantes();
    } catch (err) {
        setMensagemEstudantes(err.message, true);
    }
}

async function validarAcessoGestao() {
    const usuario = await fetchJson("/me", { headers });
    const cargo = normalizarCargoUsuario(usuario);
    const ehGestor = cargo === "ADMIN" || cargo === "COORDENADOR";
    if (!ehGestor) {
        window.location.href = "/servicos";
        return false;
    }
    return true;
}

function registrarEventosAbas() {
    listarBotoesAbasCoord().forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAbaCoordenacao(botao.dataset.coordTabTrigger);
        });
    });
}

function registrarEventosOcorrencias() {
    el("formFiltrosOcorrencias").addEventListener("submit", filtrarOcorrencias);
    el("formOcorrencia").addEventListener("submit", salvarOcorrencia);
    el("formOcorrencia").addEventListener("input", atualizarPreviewOcorrencia);
    el("formOcorrencia").addEventListener("change", atualizarPreviewOcorrencia);
    el("btnLimparFiltros").addEventListener("click", limparFiltrosOcorrencias);
    el("btnNovaOcorrencia").addEventListener("click", () => {
        const painelAberto = painelFormularioOcorrenciaAberto();
        if (painelAberto && !ocorrenciaEmEdicaoId) {
            limparFormularioOcorrencia();
            return;
        }

        limparFormularioOcorrencia({ manterAberto: true });
        mostrarPainelFormularioOcorrencia({ scroll: true });
        el("ocorrenciaBuscaEstudante").focus();
    });
    el("btnFecharPainelOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
    });
    el("btnCancelarEdicaoOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
    });

    el("ocorrenciaBuscaEstudante").addEventListener("input", () => {
        el("ocorrenciaEstudanteId").value = "";
        agendarBuscaEstudantes();
    });
    el("ocorrenciaBuscaEstudante").addEventListener("change", aplicarSelecaoEstudantePorTexto);
    el("ocorrenciaBuscaEstudante").addEventListener("blur", aplicarSelecaoEstudantePorTexto);
    el("ocorrenciaBuscaEstudante").addEventListener("focus", () => {
        atualizarSugestoesEstudantesBusca(true).catch((err) => setMensagemOcorrencias(err.message, true));
    });

    el("ocorrenciaBuscaProfessor").addEventListener("input", () => {
        el("ocorrenciaProfessorRequerenteId").value = "";
        atualizarSugestoesProfessoresBusca();
    });
    el("ocorrenciaBuscaProfessor").addEventListener("change", aplicarSelecaoProfessorPorTexto);
    el("ocorrenciaBuscaProfessor").addEventListener("blur", aplicarSelecaoProfessorPorTexto);
    el("ocorrenciaBuscaProfessor").addEventListener("focus", () => {
        atualizarSugestoesProfessoresBusca(true);
    });

    el("ocorrenciaDisciplina").addEventListener("input", () => {
        atualizarSugestoesDisciplinasBusca();
    });
    el("ocorrenciaDisciplina").addEventListener("change", aplicarSelecaoDisciplinaPorTexto);
    el("ocorrenciaDisciplina").addEventListener("blur", aplicarSelecaoDisciplinaPorTexto);
    el("ocorrenciaDisciplina").addEventListener("focus", () => {
        atualizarSugestoesDisciplinasBusca(true);
    });

    el("ocorrenciaBuscaRegimento").addEventListener("input", () => {
        atualizarSugestoesRegimentoBusca();
    });
    el("ocorrenciaBuscaRegimento").addEventListener("change", aplicarSelecaoRegimentoPorTexto);
    el("ocorrenciaBuscaRegimento").addEventListener("blur", aplicarSelecaoRegimentoPorTexto);
    el("ocorrenciaBuscaRegimento").addEventListener("focus", () => {
        atualizarSugestoesRegimentoBusca(true);
    });

    el("ocorrenciaTurmaId").addEventListener("change", () => {
        el("ocorrenciaEstudanteId").value = "";
        atualizarSelectAulasPorTurma(el("ocorrenciaTurmaId").value);
        agendarBuscaEstudantes();
        ocultarSugestoes("listaEstudantesBusca");
        atualizarPreviewOcorrencia();
    });
}

function registrarEventosRelatorios() {
    el("formRelatorioOcorrencias").addEventListener("submit", filtrarRelatorioOcorrencias);
    el("btnLimparRelatorioOcorrencias").addEventListener("click", limparFiltrosRelatorioOcorrencias);
}

function registrarEventosEstudantes() {
    el("formEstudante").addEventListener("submit", salvarEstudante);
    el("formImportarEstudantesCsv").addEventListener("submit", importarEstudantesCsv);
    el("btnCancelarEdicaoEstudante").addEventListener("click", limparFormularioEstudante);
    el("btnBaixarModeloEstudantesCsv").addEventListener("click", baixarModeloEstudantesCsv);
    el("formFiltrosEstudantes").addEventListener("submit", filtrarEstudantes);
    el("btnLimparFiltrosEstudantes").addEventListener("click", limparFiltrosEstudantes);
    el("filtroEstudanteStatus").addEventListener("change", renderTabelaEstudantes);
}

function registrarEventosRegimento() {
    el("formRegimento").addEventListener("submit", salvarRegimento);
    el("formImportarRegimentoCsv").addEventListener("submit", importarRegimentoCsv);
    el("btnCancelarEdicaoRegimento").addEventListener("click", limparFormularioRegimento);
    el("btnBaixarModeloRegimentoCsv").addEventListener("click", baixarModeloRegimentoCsv);
}

function registrarEventosGerais() {
    document.addEventListener("click", (event) => {
        if (event.target.closest(".coordenacao-autocomplete-shell")) return;
        ocultarTodasSugestoes();
    });
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnIrAdmin").addEventListener("click", () => {
        window.location.href = "/admin";
    });
    el("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        const autorizado = await validarAcessoGestao();
        if (!autorizado) return;

        registrarEventosAbas();
        registrarEventosOcorrencias();
        registrarEventosRelatorios();
        registrarEventosEstudantes();
        registrarEventosRegimento();
        registrarEventosGerais();

        await carregarOpcoesOcorrencias();
        limparFormularioOcorrencia();
        limparFormularioEstudante();
        limparFormularioRegimento();
        renderDetalhesOcorrencia(null);
        renderRelatorioOcorrencias();
        ativarAbaCoordenacao(abaCoordAtiva);

        await Promise.all([
            carregarOcorrencias(),
            carregarEstudantes(),
            carregarRegimentoItens()
        ]);
    } catch (err) {
        setMensagemOcorrencias(err.message || "Erro ao carregar modulo de coordenacao.", true);
    }
}

init();
