const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    normalizarCargoUsuario,
} = window.AppAuth;
const { fetchJson, fetchResposta } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);
const headersJson = criarHeadersJsonAuth(token);

let abaCoordAtiva = "ocorrencias";
let ocorrenciaEmEdicaoId = null;
let ocorrenciaSelecionadaId = null;
let estudanteEmEdicao = null;
let leiBaseLegalEmEdicao = null;
let artigoBaseLegalEmEdicao = null;
let incisoBaseLegalEmEdicao = null;
let alineaBaseLegalEmEdicao = null;
let ocorrenciasCache = [];
let estudantesCache = [];
let regimentoItensCache = [];
let leisBaseLegalCache = [];
let artigosBaseLegalCache = [];
let incisosBaseLegalCache = [];
let alineasBaseLegalCache = [];
let relatorioOcorrenciasCache = [];
let relatorioOcorrenciasCarregado = false;
let selecaoDescricaoEditor = null;
let regimentoSelecionadoIds = [];
let estudantesVinculadosSelecionados = [];
let professoresVinculadosSelecionados = [];
let opcoesOcorrencias = {
    tipos_registro: [],
    turmas: [],
    professores: [],
    disciplinas: [],
    leis: [],
    artigos: [],
    incisos: [],
    alineas: [],
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
const rotulosTipoRegistro = new Map();
const mapaBuscaEstudantes = new Map();
const mapaBuscaProfessores = new Map();
const mapaBuscaDisciplinas = new Map();
const mapaBuscaRegimento = new Map();
const mapaBuscaLeisBaseLegal = new Map();
const mapaBuscaArtigosBaseLegal = new Map();
const mapaBuscaIncisosBaseLegal = new Map();
let timerBuscaEstudantes = null;
const MODELO_JSON_ESTUDANTES = [
    "{",
    "  \"turma\": \"6o Ano A\",",
    "  \"turno\": \"Integral\",",
    "  \"ano_letivo\": 2026,",
    "  \"estudantes\": [",
    "    {",
    "      \"matricula\": \"1428172\",",
    "      \"nome\": \"Adam Jose Marques Machado\",",
    "      \"situacao\": \"Em curso\",",
    "      \"faltas\": 0",
    "    },",
    "    {",
    "      \"matricula\": \"1474330\",",
    "      \"nome\": \"Bianca Oliveira de Souza\",",
    "      \"situacao\": \"Em curso\",",
    "      \"faltas\": 0",
    "    },",
    "    {",
    "      \"matricula\": \"1465299\",",
    "      \"nome\": \"Davi Yudi Kimura\",",
    "      \"situacao\": \"Remanejado\",",
    "      \"faltas\": 0",
    "    }",
    "  ]",
    "}"
].join("\n");
const MODELO_JSON_BASE_LEGAL = [
    "{",
    "  \"lei\": \"Regimento Escolar\",",
    "  \"artigos\": [",
    "    {",
    "      \"numero\": 76,",
    "      \"descricao\": \"Sao deveres do estudante, alem daqueles previstos na legislacao vigente, os seguintes:\",",
    "      \"incisos\": [",
    "        {",
    "          \"numero\": \"I\",",
    "          \"descricao\": \"comparecer, pontualmente, as aulas, provas e outras atividades preparadas e programadas pelo professor;\"",
    "        },",
    "        {",
    "          \"numero\": \"IV\",",
    "          \"descricao\": \"apresentar-se, adequadamente, trajado para as aulas...\",",
    "          \"alineas\": [",
    "            {",
    "              \"identificador\": \"a\",",
    "              \"descricao\": \"short e bermuda (5 (cinco) centimetros acima do joelho);\"",
    "            },",
    "            {",
    "              \"identificador\": \"b\",",
    "              \"descricao\": \"oculos escuros, salvo se recomendacao medica;\"",
    "            }",
    "          ]",
    "        }",
    "      ]",
    "    }",
    "  ]",
    "}"
].join("\n");
const OBSERVACOES_ACAO_PREVIEW = {
    advertencia_verbal: "OBS.: Aplicada advertencia verbal com orientacao pedagogica, conforme a base legal selecionada.",
    retirada_sala_orientacao: "OBS.: Aplicada retirada do estudante da sala ou atividade, com encaminhamento para orientacao.",
    suspensao_extracurricular: "OBS.: Aplicada suspensao temporaria de participacao em programas extracurriculares.",
    suspensao_orientada_2_dias: "OBS.: Aplicada suspensao orientada das aulas pelo periodo definido pela equipe escolar.",
    suspensao_aulas_3_dias: "OBS.: Aplicada suspensao das aulas, respeitado o limite previsto na base legal.",
    transferencia_compulsoria: "OBS.: Aplicada transferencia compulsoria, conforme decisao institucional cabivel ao caso.",
    orientacao_verbal: "OBS.: O registro fica arquivado para acompanhamento pedagogico e orientacao verbal junto ao estudante.",
    advertencia: "OBS.: Pela falta de integracao e compromisso e por nao acatar as solicitacoes da docente, recebe esta acao pedagogico-disciplinar de advertencia.",
    chamada_responsavel: "OBS.: Solicitado o comparecimento do responsavel para alinhamento e acompanhamento conjunto do caso.",
    encaminhamento_direcao: "OBS.: O registro segue encaminhado a Direcao para providencias e acompanhamento institucional.",
    registro_informativo: "OBS.: Documento emitido para registro informativo e acompanhamento pedagogico interno.",
    orientacao_professor: "OBS.: Registro emitido para documentar a orientacao individual feita ao professor, com ciencia formal das partes.",
    reuniao_alinhamento: "OBS.: Registro emitido para documentar reuniao de alinhamento e pactuacao institucional com o professor.",
    orientacao_geral_docentes: "OBS.: Registro emitido para documentar orientacao geral apresentada ao corpo docente, com coleta de assinaturas ao final."
};
const GRAVIDADE_ROTULOS = {
    leve: "Falta leve",
    grave: "Falta grave",
    gravissima: "Falta gravissima"
};
const ORDEM_GRAVIDADE = {
    leve: 1,
    grave: 2,
    gravissima: 3
};

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
    window.AppApi.baixarArquivoTexto(nomeArquivo, conteudo, tipo);
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

function rotuloTipoRegistro(tipo) {
    return rotulosTipoRegistro.get(tipo) || tipo || "Nao informado";
}

function obterTipoRegistroFormulario() {
    return String(el("ocorrenciaTipoRegistro")?.value || "estudante").trim() || "estudante";
}

function registroExigeBaseLegal(tipo = obterTipoRegistroFormulario()) {
    return String(tipo || "").trim() === "estudante";
}

function classeStatus(status) {
    const texto = String(status || "").trim().toLowerCase();
    if (!texto) return "status-registrado";
    return `status-${texto.replace(/[^a-z0-9_]/g, "-")}`;
}

function classeStatusEstudante(ativo) {
    return ativo ? "status-resolvido" : "status-aguardando_responsavel";
}

function obterReferenciaRegistro(ocorrencia) {
    const tipo = String(ocorrencia?.tipo_registro || "").trim();
    const estudantesVinculados = normalizarEstudantesVinculados(ocorrencia?.estudantes_vinculados);
    const professoresVinculados = normalizarProfessoresVinculados(ocorrencia?.professores_vinculados);
    if (tipo === "professor") {
        return resumoNomesVinculados(professoresVinculados)
            || String(ocorrencia?.professor_requerente || ocorrencia?.nome_estudante || "").trim()
            || "Nao informado";
    }
    if (tipo === "estudante") {
        return resumoNomesVinculados(estudantesVinculados)
            || String(ocorrencia?.nome_estudante || "").trim()
            || "Nao informado";
    }
    return String(ocorrencia?.nome_estudante || "").trim() || "Nao informado";
}

function obterContextoRegistro(ocorrencia) {
    const tipo = String(ocorrencia?.tipo_registro || "").trim();
    if (tipo === "professor") {
        const totalProfessores = normalizarProfessoresVinculados(ocorrencia?.professores_vinculados).length;
        return totalProfessores > 1 ? `${totalProfessores} professores vinculados` : "Professor individual";
    }
    if (tipo === "geral") return "Orientacao geral";
    const estudantes = normalizarEstudantesVinculados(ocorrencia?.estudantes_vinculados);
    const turmasVinculadas = Array.from(new Set(
        estudantes
            .map((item) => String(item?.turma_nome || "").trim() || (item?.turma_id ? `ID ${item.turma_id}` : ""))
            .filter(Boolean)
    ));
    if (turmasVinculadas.length > 1) {
        return `${turmasVinculadas.length} turmas vinculadas`;
    }
    if (turmasVinculadas.length === 1) {
        return turmasVinculadas[0];
    }
    const turmaNome = String(ocorrencia?.turma_nome || "").trim();
    if (turmaNome) return turmaNome;
    const turmaId = Number(ocorrencia?.turma_id || 0);
    return turmaId > 0 ? `ID ${turmaId}` : "Sem turma";
}

function resumoNomesVinculados(itens) {
    return (itens || [])
        .map((item) => String(item?.nome || "").trim())
        .filter(Boolean)
        .join(", ");
}

function normalizarEstudantesVinculados(valores) {
    const vistos = new Set();
    return (valores || []).map((item) => {
        if (!item || typeof item !== "object") return null;
        const estudanteId = Number(item.estudante_id || 0);
        const turmaId = Number(item.turma_id || 0);
        const nome = String(item.nome || "").trim();
        const turmaNome = String(item.turma_nome || "").trim();
        if (!nome) return null;
        return {
            estudante_id: estudanteId > 0 ? estudanteId : null,
            nome,
            turma_id: turmaId > 0 ? turmaId : null,
            turma_nome: turmaNome
        };
    }).filter(Boolean).filter((item) => {
        const chave = item.estudante_id ? `id:${item.estudante_id}` : `nome:${item.nome.toLowerCase()}`;
        if (vistos.has(chave)) return false;
        vistos.add(chave);
        return true;
    });
}

function normalizarProfessoresVinculados(valores) {
    const vistos = new Set();
    return (valores || []).map((item) => {
        if (!item || typeof item !== "object") return null;
        const professorId = Number(item.professor_id || 0);
        const nome = String(item.nome || "").trim();
        const email = String(item.email || "").trim();
        if (!nome) return null;
        return {
            professor_id: professorId > 0 ? professorId : null,
            nome,
            email
        };
    }).filter(Boolean).filter((item) => {
        const chave = item.professor_id ? `id:${item.professor_id}` : `nome:${item.nome.toLowerCase()}`;
        if (vistos.has(chave)) return false;
        vistos.add(chave);
        return true;
    });
}

function obterEstudantesVinculadosFormulario() {
    estudantesVinculadosSelecionados = normalizarEstudantesVinculados(estudantesVinculadosSelecionados);
    return [...estudantesVinculadosSelecionados];
}

function obterProfessoresVinculadosFormulario() {
    professoresVinculadosSelecionados = normalizarProfessoresVinculados(professoresVinculadosSelecionados);
    return [...professoresVinculadosSelecionados];
}

function renderSelecionadorVinculados(containerId, itens, {
    textoVazio,
    metaItem = () => "",
    onRemove = null
} = {}) {
    const container = el(containerId);
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(itens) || itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = textoVazio;
        container.appendChild(vazio);
        return;
    }

    itens.forEach((item, indice) => {
        const card = document.createElement("article");
        card.className = "coordenacao-selection-card";

        const corpo = document.createElement("div");
        corpo.className = "coordenacao-selection-card-body";

        const titulo = document.createElement("strong");
        titulo.innerText = String(item?.nome || "").trim() || "Nao informado";
        corpo.appendChild(titulo);

        const metaTexto = String(metaItem(item, indice) || "").trim();
        if (metaTexto) {
            const meta = document.createElement("span");
            meta.innerText = metaTexto;
            corpo.appendChild(meta);
        }

        card.appendChild(corpo);

        if (typeof onRemove === "function") {
            const btnRemover = document.createElement("button");
            btnRemover.type = "button";
            btnRemover.className = "coordenacao-selection-remove";
            btnRemover.innerText = "Remover";
            btnRemover.addEventListener("click", () => onRemove(item, indice));
            card.appendChild(btnRemover);
        }

        container.appendChild(card);
    });
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
        botao.innerText = "Novo registro";
    } else if (ocorrenciaEmEdicaoId) {
        botao.innerText = "Novo registro";
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
            item.referencia,
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
    return String(item?.label || item?.nome || item?.artigo || item?.referencia || "").trim();
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
            item.referencia,
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
    [
        "listaEstudantesBusca",
        "listaProfessoresBusca",
        "listaDisciplinasBusca",
        "listaRegimentoBusca",
        "listaLeisBaseLegal",
        "listaArtigosBaseLegal",
        "listaIncisosBaseLegal"
    ].forEach(ocultarSugestoes);
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
    const idsDom = normalizarIdsRegimento(
        Array.from(document.querySelectorAll("#ocorrenciaRegimentoSelecionados [data-regimento-item-id]"))
            .map((item) => item.dataset.regimentoItemId)
    );
    return normalizarIdsRegimento([
        ...regimentoSelecionadoIds,
        ...idsDom
    ]);
}

function validarBaseLegalSelecionadaAntesSalvar() {
    const idsSelecionados = obterIdsRegimentoSelecionadosFormulario();
    if (!registroExigeBaseLegal()) {
        return idsSelecionados;
    }
    if (idsSelecionados.length > 0) {
        return idsSelecionados;
    }

    setMensagemOcorrencias("Selecione ao menos uma base legal para vincular o registro de estudante.", true);
    el("ocorrenciaBuscaRegimento")?.focus();
    atualizarSugestoesRegimentoBusca(true);
    return [];
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
        atualizarAcaoAplicadaPorGravidade({
            gravidade: inferirGravidadeOcorrenciaBaseLegal(obterItensRegimentoSelecionadosPreview())
        });
        atualizarPreviewOcorrencia();
        return;
    }

    const idsAtivos = new Set(
        idsSelecionados === null
            ? obterIdsRegimentoSelecionadosFormulario()
            : normalizarIdsRegimento(idsSelecionados)
    );
    regimentoSelecionadoIds = normalizarIdsRegimento(Array.from(idsAtivos));
    container.innerHTML = "";

    const itens = Array.isArray(opcoesOcorrencias.regimento_itens)
        ? opcoesOcorrencias.regimento_itens
        : [];
    if (itens.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = "Cadastre itens da base legal para anexa-los na ocorrencia.";
        container.appendChild(vazio);
        atualizarAcaoAplicadaPorGravidade({ gravidade: "" });
        atualizarPreviewOcorrencia();
        return;
    }

    const itensSelecionados = itens.filter((item) => idsAtivos.has(Number(item.id || 0)));
    if (itensSelecionados.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = "Nenhuma base legal anexada ainda.";
        container.appendChild(vazio);
        atualizarAcaoAplicadaPorGravidade({ gravidade: "" });
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
    atualizarAcaoAplicadaPorGravidade({
        gravidade: inferirGravidadeOcorrenciaBaseLegal(itensSelecionados)
    });
    atualizarPreviewOcorrencia();
}
