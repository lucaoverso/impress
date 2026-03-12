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
let estudanteEmEdicao = null;
let ocorrenciasCache = [];
let estudantesCache = [];
let opcoesOcorrencias = {
    turmas: [],
    status: [],
    acoes_aplicadas: [],
    status_padrao: "registrado"
};

const rotulosAcao = new Map();
const rotulosStatus = new Map();
const mapaBuscaEstudantes = new Map();
const mapaBuscaProfessores = new Map();
let timerBuscaEstudantes = null;
let timerBuscaProfessores = null;

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
        throw new Error(normalizarErro(res, body));
    }
    return body;
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
}

function preencherSelect(selectId, opcoes, {
    incluirTodos = false,
    placeholder = "",
    valorPadrao = ""
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
        option.innerText = item.nome || item.id;
        select.appendChild(option);
    });

    if (valorPadrao !== "") {
        select.value = String(valorPadrao);
    }
}

function preencherDatalist(datalistId, mapa, itens) {
    const datalist = el(datalistId);
    if (!datalist) return;
    datalist.innerHTML = "";
    mapa.clear();

    (itens || []).forEach((item) => {
        const label = String(item.label || item.nome || "").trim();
        if (!label) return;

        const option = document.createElement("option");
        option.value = label;
        datalist.appendChild(option);
        mapa.set(label, item);
    });
}

function limparFormularioOcorrencia() {
    el("formOcorrencia").reset();
    ocorrenciaEmEdicaoId = null;
    el("ocorrenciaEstudanteId").value = "";
    el("ocorrenciaProfessorRequerenteId").value = "";
    const hoje = new Date();
    el("ocorrenciaData").value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}-${String(hoje.getDate()).padStart(2, "0")}`;
    if (opcoesOcorrencias.status_padrao) {
        el("ocorrenciaStatus").value = opcoesOcorrencias.status_padrao;
    }
    el("tituloFormOcorrencia").innerText = "Nova ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "none";
}

function preencherFormularioOcorrencia(ocorrencia) {
    ocorrenciaEmEdicaoId = Number(ocorrencia.id);
    el("ocorrenciaBuscaEstudante").value = ocorrencia.nome_estudante || "";
    el("ocorrenciaEstudanteId").value = ocorrencia.estudante_id || "";
    el("ocorrenciaTurmaId").value = String(ocorrencia.turma_id || "");
    el("ocorrenciaBuscaProfessor").value = ocorrencia.professor_requerente || "";
    el("ocorrenciaProfessorRequerenteId").value = ocorrencia.professor_requerente_id || "";
    el("ocorrenciaDisciplina").value = ocorrencia.disciplina || "";
    el("ocorrenciaData").value = ocorrencia.data_ocorrencia || "";
    el("ocorrenciaAula").value = ocorrencia.aula || "";
    el("ocorrenciaHorario").value = ocorrencia.horario_ocorrencia || "";
    el("ocorrenciaDescricao").value = ocorrencia.descricao || "";
    el("ocorrenciaAcaoAplicada").value = ocorrencia.acao_aplicada || "";
    el("ocorrenciaStatus").value = ocorrencia.status || opcoesOcorrencias.status_padrao || "registrado";
    el("tituloFormOcorrencia").innerText = "Editar ocorrencia";
    el("btnCancelarEdicaoOcorrencia").style.display = "inline-block";
    ativarAbaCoordenacao("ocorrencias");
    el("formOcorrencia").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderDetalhesOcorrencia(ocorrencia) {
    const container = el("detalhesOcorrencia");
    if (!container) return;
    if (!ocorrencia) {
        container.innerText = "Selecione uma ocorrencia para visualizar os detalhes.";
        return;
    }

    container.innerHTML = "";
    const campos = [
        ["Estudante", ocorrencia.nome_estudante],
        ["Turma", ocorrencia.turma_nome || `ID ${ocorrencia.turma_id}`],
        ["Professor requerente", ocorrencia.professor_requerente],
        ["Disciplina", ocorrencia.disciplina],
        ["Data", formatarDataBr(ocorrencia.data_ocorrencia)],
        ["Aula", ocorrencia.aula],
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
}

async function carregarOpcoesOcorrencias() {
    opcoesOcorrencias = await fetchJson("/ocorrencias/opcoes", { headers });

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
    preencherSelect("ocorrenciaAcaoAplicada", opcoesOcorrencias.acoes_aplicadas, { placeholder: "Selecione a acao aplicada" });
    preencherSelect("ocorrenciaStatus", opcoesOcorrencias.status, {
        placeholder: "Selecione o status",
        valorPadrao: opcoesOcorrencias.status_padrao || "registrado"
    });
    preencherSelect("filtroStatus", opcoesOcorrencias.status, { incluirTodos: true });

    preencherSelect("estudanteTurmaId", opcoesOcorrencias.turmas, { placeholder: "Selecione a turma" });
    preencherSelect("filtroEstudanteTurmaId", opcoesOcorrencias.turmas, { incluirTodos: true });
}

function queryFiltrosOcorrencias() {
    const params = new URLSearchParams();
    const nomeEstudante = el("filtroNomeEstudante").value.trim();
    const turmaId = el("filtroTurmaId").value;
    const status = el("filtroStatus").value;
    const dataInicial = el("filtroDataInicial").value;
    const dataFinal = el("filtroDataFinal").value;

    if (nomeEstudante) params.set("nome_estudante", nomeEstudante);
    if (turmaId) params.set("turma_id", turmaId);
    if (status) params.set("status", status);
    if (dataInicial) params.set("data_inicial", dataInicial);
    if (dataFinal) params.set("data_final", dataFinal);

    return params.toString() ? `?${params.toString()}` : "";
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

function renderTabelaOcorrencias() {
    const tbody = el("tbodyOcorrencias");
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

        const tdData = document.createElement("td");
        tdData.innerText = formatarDataBr(ocorrencia.data_ocorrencia);
        tr.appendChild(tdData);

        const tdEstudante = document.createElement("td");
        tdEstudante.innerText = ocorrencia.nome_estudante || "";
        tr.appendChild(tdEstudante);

        const tdTurma = document.createElement("td");
        tdTurma.innerText = ocorrencia.turma_nome || "";
        tr.appendChild(tdTurma);

        const tdProfessor = document.createElement("td");
        tdProfessor.innerText = ocorrencia.professor_requerente || "";
        tr.appendChild(tdProfessor);

        const tdAcao = document.createElement("td");
        tdAcao.innerText = rotuloAcao(ocorrencia.acao_aplicada);
        tr.appendChild(tdAcao);

        const tdStatus = document.createElement("td");
        const statusBadge = document.createElement("span");
        statusBadge.className = `status-chip ${classeStatus(ocorrencia.status)}`;
        statusBadge.innerText = rotuloStatus(ocorrencia.status);
        tdStatus.appendChild(statusBadge);
        tr.appendChild(tdStatus);

        const tdAcoes = document.createElement("td");
        const linhaAcoes = document.createElement("div");
        linhaAcoes.className = "coordenacao-inline";

        const btnVer = document.createElement("button");
        btnVer.type = "button";
        btnVer.innerText = "Ver";
        btnVer.addEventListener("click", async () => {
            const detalhe = await fetchJson(`/ocorrencias/${ocorrencia.id}`, { headers });
            renderDetalhesOcorrencia(detalhe);
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar";
        btnEditar.addEventListener("click", () => preencherFormularioOcorrencia(ocorrencia));

        linhaAcoes.appendChild(btnVer);
        linhaAcoes.appendChild(btnEditar);
        tdAcoes.appendChild(linhaAcoes);
        tr.appendChild(tdAcoes);

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

        const tdNome = document.createElement("td");
        tdNome.innerText = estudante.nome || "";
        tr.appendChild(tdNome);

        const tdTurma = document.createElement("td");
        tdTurma.innerText = estudante.turma_nome || "";
        tr.appendChild(tdTurma);

        const tdStatus = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `status-chip ${classeStatusEstudante(Boolean(estudante.ativo))}`;
        badge.innerText = estudante.ativo ? "Ativo" : "Inativo";
        tdStatus.appendChild(badge);
        tr.appendChild(tdStatus);

        const tdAtualizado = document.createElement("td");
        tdAtualizado.innerText = formatarDataHora(estudante.atualizado_em);
        tr.appendChild(tdAtualizado);

        const tdAcoes = document.createElement("td");
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

        linhaAcoes.appendChild(btnEditar);
        linhaAcoes.appendChild(btnStatus);
        tdAcoes.appendChild(linhaAcoes);
        tr.appendChild(tdAcoes);

        tbody.appendChild(tr);
    });
}

async function carregarOcorrencias() {
    ocorrenciasCache = await fetchJson(`/ocorrencias${queryFiltrosOcorrencias()}`, { headers });
    renderTabelaOcorrencias();
}

async function carregarEstudantes() {
    estudantesCache = await fetchJson(`/estudantes${queryFiltrosEstudantes()}`, { headers });
    renderTabelaEstudantes();
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
        return;
    }

    const item = mapaBuscaEstudantes.get(texto);
    if (!item) {
        hidden.value = "";
        return;
    }

    hidden.value = String(item.id);
    el("ocorrenciaTurmaId").value = String(item.turma_id);
}

function aplicarSelecaoProfessorPorTexto() {
    const input = el("ocorrenciaBuscaProfessor");
    const hidden = el("ocorrenciaProfessorRequerenteId");
    const texto = input.value.trim();
    if (!texto) {
        hidden.value = "";
        return;
    }

    const item = mapaBuscaProfessores.get(texto);
    hidden.value = item ? String(item.id) : "";
}

async function atualizarSugestoesEstudantesBusca(forcar = false) {
    const input = el("ocorrenciaBuscaEstudante");
    const termo = input.value.trim();
    const turmaId = el("ocorrenciaTurmaId").value;
    if (!forcar && termo.length < 2) {
        preencherDatalist("listaEstudantesBusca", mapaBuscaEstudantes, []);
        return;
    }

    const params = new URLSearchParams();
    params.set("q", termo);
    if (turmaId) params.set("turma_id", turmaId);
    params.set("limite", "20");
    const itens = await fetchJson(`/ocorrencias/busca/estudantes?${params.toString()}`, { headers });
    preencherDatalist("listaEstudantesBusca", mapaBuscaEstudantes, itens);
}

async function atualizarSugestoesProfessoresBusca(forcar = false) {
    const input = el("ocorrenciaBuscaProfessor");
    const termo = input.value.trim();
    if (!forcar && termo.length < 2) {
        preencherDatalist("listaProfessoresBusca", mapaBuscaProfessores, []);
        return;
    }

    const params = new URLSearchParams();
    params.set("q", termo);
    params.set("limite", "20");
    const itens = await fetchJson(`/ocorrencias/busca/professores?${params.toString()}`, { headers });
    preencherDatalist("listaProfessoresBusca", mapaBuscaProfessores, itens);
}

function agendarBuscaEstudantes() {
    if (timerBuscaEstudantes) clearTimeout(timerBuscaEstudantes);
    timerBuscaEstudantes = setTimeout(() => {
        atualizarSugestoesEstudantesBusca().catch((err) => setMensagemOcorrencias(err.message, true));
    }, 250);
}

function agendarBuscaProfessores() {
    if (timerBuscaProfessores) clearTimeout(timerBuscaProfessores);
    timerBuscaProfessores = setTimeout(() => {
        atualizarSugestoesProfessoresBusca().catch((err) => setMensagemOcorrencias(err.message, true));
    }, 250);
}

function montarPayloadOcorrencia() {
    const textoEstudante = el("ocorrenciaBuscaEstudante").value.trim();
    const textoProfessor = el("ocorrenciaBuscaProfessor").value.trim();
    const itemEstudante = mapaBuscaEstudantes.get(textoEstudante);
    const itemProfessor = mapaBuscaProfessores.get(textoProfessor);

    const estudanteIdHidden = Number(el("ocorrenciaEstudanteId").value || 0);
    const professorIdHidden = Number(el("ocorrenciaProfessorRequerenteId").value || 0);

    const estudanteId = estudanteIdHidden || (itemEstudante ? Number(itemEstudante.id) : 0);
    const professorId = professorIdHidden || (itemProfessor ? Number(itemProfessor.id) : 0);

    const nomeEstudante = itemEstudante ? itemEstudante.nome : textoEstudante;
    const nomeProfessor = itemProfessor ? itemProfessor.nome : textoProfessor;

    return {
        nome_estudante: nomeEstudante || null,
        estudante_id: estudanteId > 0 ? estudanteId : null,
        turma_id: Number(el("ocorrenciaTurmaId").value),
        professor_requerente: nomeProfessor || null,
        professor_requerente_id: professorId > 0 ? professorId : null,
        disciplina: el("ocorrenciaDisciplina").value.trim(),
        data_ocorrencia: el("ocorrenciaData").value,
        aula: el("ocorrenciaAula").value.trim(),
        horario_ocorrencia: el("ocorrenciaHorario").value.trim(),
        descricao: el("ocorrenciaDescricao").value.trim(),
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
        await carregarOcorrencias();
        renderDetalhesOcorrencia(ocorrencia);
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
    el("btnLimparFiltros").addEventListener("click", limparFiltrosOcorrencias);
    el("btnNovaOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
        renderDetalhesOcorrencia(null);
    });
    el("btnCancelarEdicaoOcorrencia").addEventListener("click", () => {
        limparFormularioOcorrencia();
        renderDetalhesOcorrencia(null);
    });

    el("ocorrenciaBuscaEstudante").addEventListener("input", () => {
        el("ocorrenciaEstudanteId").value = "";
        agendarBuscaEstudantes();
    });
    el("ocorrenciaBuscaEstudante").addEventListener("change", aplicarSelecaoEstudantePorTexto);
    el("ocorrenciaBuscaEstudante").addEventListener("blur", aplicarSelecaoEstudantePorTexto);

    el("ocorrenciaBuscaProfessor").addEventListener("input", () => {
        el("ocorrenciaProfessorRequerenteId").value = "";
        agendarBuscaProfessores();
    });
    el("ocorrenciaBuscaProfessor").addEventListener("change", aplicarSelecaoProfessorPorTexto);
    el("ocorrenciaBuscaProfessor").addEventListener("blur", aplicarSelecaoProfessorPorTexto);

    el("ocorrenciaTurmaId").addEventListener("change", () => {
        el("ocorrenciaEstudanteId").value = "";
        agendarBuscaEstudantes();
    });
}

function registrarEventosEstudantes() {
    el("formEstudante").addEventListener("submit", salvarEstudante);
    el("btnCancelarEdicaoEstudante").addEventListener("click", limparFormularioEstudante);
    el("formFiltrosEstudantes").addEventListener("submit", filtrarEstudantes);
    el("btnLimparFiltrosEstudantes").addEventListener("click", limparFiltrosEstudantes);
    el("filtroEstudanteStatus").addEventListener("change", renderTabelaEstudantes);
}

function registrarEventosGerais() {
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
        registrarEventosEstudantes();
        registrarEventosGerais();

        await carregarOpcoesOcorrencias();
        limparFormularioOcorrencia();
        limparFormularioEstudante();
        renderDetalhesOcorrencia(null);
        ativarAbaCoordenacao(abaCoordAtiva);

        await Promise.all([
            carregarOcorrencias(),
            carregarEstudantes()
        ]);
    } catch (err) {
        setMensagemOcorrencias(err.message || "Erro ao carregar modulo de coordenacao.", true);
    }
}

init();
