const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": `Bearer ${token}`
};

const headersJson = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
};

const SENHA_FORTE_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;
let opcoesProfessor = { turmas: [], disciplinas: [] };
let professorEmEdicaoId = null;
let recursoEmEdicaoId = null;
const TURNO_LABEL = {
    INTEGRAL: "Período integral",
    MATUTINO: "Matutino",
    VESPERTINO: "Vespertino",
    VESPERTINO_EM: "Vespertino E.M."
};
const CARGO_ADMIN = "ADMIN";
const CARGO_PROFESSOR = "PROFESSOR";
const CARGO_COORDENADOR = "COORDENADOR";
let usuarioAtual = null;
let usuarioEhAdmin = false;
let usuarioEhGestor = false;

function el(id) {
    return document.getElementById(id);
}

function mesAtualIso() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function setMensagem(id, texto, erro = false) {
    const target = el(id);
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
    } catch (err) {
        body = null;
    }

    if (res.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
        throw new Error("Sessão expirada.");
    }

    if (!res.ok) {
        throw new Error(normalizarErro(res, body));
    }
    return body;
}

function normalizarCargoUsuario(usuario = {}) {
    const cargo = String(usuario.cargo || "").trim().toUpperCase();
    if (cargo) {
        return cargo;
    }

    const perfil = String(usuario.perfil || "").trim().toLowerCase();
    if (perfil === "admin") return CARGO_ADMIN;
    if (perfil === "coordenador") return CARGO_COORDENADOR;
    return CARGO_PROFESSOR;
}

function aplicarPermissoesTela() {
    document.querySelectorAll("[data-admin-only='true']").forEach((secao) => {
        secao.style.display = usuarioEhAdmin ? "" : "none";
    });
}

function atualizarVisibilidadeCamposCargo() {
    const cargo = String(el("profCargo")?.value || CARGO_PROFESSOR).toUpperCase();
    const hint = el("profCargoHint");
    if (!hint) {
        return;
    }
    hint.style.display = cargo === CARGO_COORDENADOR ? "block" : "none";
}

async function carregarUsuarioAtual() {
    usuarioAtual = await fetchJson("/me", { headers });
    const cargo = normalizarCargoUsuario(usuarioAtual);
    usuarioEhAdmin = cargo === CARGO_ADMIN;
    usuarioEhGestor = usuarioEhAdmin || cargo === CARGO_COORDENADOR;

    if (!usuarioEhGestor) {
        window.location.href = "/servicos";
    }
}

async function atualizarOpcoesProfessorSePermitido() {
    if (!usuarioEhAdmin) {
        return;
    }
    await carregarOpcoesProfessor();
}

function validarSenhaForte(senha) {
    return SENHA_FORTE_REGEX.test(senha || "");
}

function atualizarHintSenha() {
    const senha = el("profSenha").value.trim();
    const hint = el("profSenhaHint");
    if (!senha) {
        hint.style.color = "#4b5563";
        return;
    }
    hint.style.color = validarSenhaForte(senha) ? "#0f766e" : "#b42318";
}

function renderCheckboxes(containerId, opcoes, prefixo) {
    const container = el(containerId);
    container.innerHTML = "";

    if (!Array.isArray(opcoes) || opcoes.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma opção ativa cadastrada.";
        container.appendChild(vazio);
        return;
    }

    opcoes.forEach((item, index) => {
        const id = `${prefixo}_${index}`;
        const label = document.createElement("label");
        label.className = "admin-checkbox-item";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = id;
        input.value = item;

        const texto = document.createElement("span");
        texto.innerText = item;

        label.appendChild(input);
        label.appendChild(texto);
        container.appendChild(label);
    });
}

function listarSelecionados(containerId) {
    return Array.from(el(containerId).querySelectorAll("input[type='checkbox']:checked"))
        .map((input) => input.value);
}

function definirSelecionados(containerId, valores = []) {
    const selecionados = new Set((valores || []).map((item) => String(item)));
    Array.from(el(containerId).querySelectorAll("input[type='checkbox']")).forEach((input) => {
        input.checked = selecionados.has(String(input.value));
    });
}

function resumoLista(lista, limite = 3) {
    if (!Array.isArray(lista) || lista.length === 0) return "Não informado";
    if (lista.length <= limite) return lista.join(", ");
    return `${lista.slice(0, limite).join(", ")} +${lista.length - limite}`;
}

function formatarDataBr(dataIso) {
    if (!dataIso) return "Não informada";
    const data = new Date(`${dataIso}T00:00:00`);
    if (Number.isNaN(data.getTime())) return dataIso;
    return data.toLocaleDateString("pt-BR");
}

function nomeTurno(turno) {
    return TURNO_LABEL[turno] || turno || "Não informado";
}

function aplicarModoFormularioProfessor(edicao = false) {
    const titulo = el("tituloFormProfessor");
    const btnSalvar = el("btnSalvarProfessor");
    const btnCancelar = el("btnCancelarEdicaoProfessor");
    const inputSenha = el("profSenha");
    const hintSenha = el("profSenhaHint");
    const selectCargo = el("profCargo");

    if (edicao) {
        titulo.innerText = "Editar professor";
        btnSalvar.innerText = "Salvar alterações";
        btnCancelar.style.display = "inline-block";
        if (selectCargo) {
            selectCargo.value = CARGO_PROFESSOR;
            selectCargo.disabled = true;
        }
        inputSenha.value = "";
        inputSenha.required = false;
        inputSenha.disabled = true;
        inputSenha.placeholder = "Senha não alterada nesta edição";
        hintSenha.innerText = "Edição de cadastro: a senha não é alterada por este formulário.";
        hintSenha.style.color = "#4b5563";
        atualizarVisibilidadeCamposCargo();
        return;
    }

    const cargoSelecionado = String(selectCargo?.value || CARGO_PROFESSOR).toUpperCase();
    const ehCoordenador = cargoSelecionado === CARGO_COORDENADOR;
    titulo.innerText = ehCoordenador ? "Cadastrar coordenador" : "Cadastrar professor";
    btnSalvar.innerText = "Cadastrar";
    btnCancelar.style.display = "none";
    if (selectCargo) {
        selectCargo.disabled = false;
    }
    inputSenha.required = true;
    inputSenha.disabled = false;
    inputSenha.placeholder = "Senha inicial";
    hintSenha.innerText = ehCoordenador
        ? "Senha inicial do coordenador."
        : "Mínimo 8 caracteres com maiúscula, minúscula, número e caractere especial.";
    atualizarHintSenha();
    atualizarVisibilidadeCamposCargo();
}

function limparFormularioProfessor() {
    el("formProfessor").reset();
    el("profCargo").value = CARGO_PROFESSOR;
    el("profAulas").value = "0";
    definirSelecionados("profTurmasLista", []);
    definirSelecionados("profDisciplinasLista", []);
    professorEmEdicaoId = null;
    aplicarModoFormularioProfessor(false);
}

function iniciarEdicaoProfessor(professor) {
    professorEmEdicaoId = Number(professor.id);
    el("profNome").value = professor.nome || "";
    el("profEmail").value = professor.email || "";
    el("profDataNascimento").value = professor.data_nascimento || "";
    el("profCargo").value = CARGO_PROFESSOR;
    el("profAulas").value = String(professor.aulas_semanais ?? 0);
    definirSelecionados("profTurmasLista", professor.turmas || []);
    definirSelecionados("profDisciplinasLista", professor.disciplinas || []);
    aplicarModoFormularioProfessor(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function aplicarModoFormularioRecurso(edicao = false) {
    const titulo = el("tituloFormRecurso");
    const btnSalvar = el("btnSalvarRecurso");
    const btnCancelar = el("btnCancelarEdicaoRecurso");

    if (edicao) {
        titulo.innerText = "Editar recurso";
        btnSalvar.innerText = "Salvar alterações";
        btnCancelar.style.display = "inline-block";
        return;
    }

    titulo.innerText = "Cadastrar recurso";
    btnSalvar.innerText = "Cadastrar recurso";
    btnCancelar.style.display = "none";
}

function limparFormularioRecurso() {
    el("formRecurso").reset();
    el("recursoQuantidadeItens").value = "1";
    recursoEmEdicaoId = null;
    aplicarModoFormularioRecurso(false);
}

function iniciarEdicaoRecurso(recurso) {
    recursoEmEdicaoId = Number(recurso.id);
    el("recursoNome").value = recurso.nome || "";
    el("recursoTipo").value = recurso.tipo || "";
    el("recursoDescricao").value = recurso.descricao || "";
    el("recursoQuantidadeItens").value = String(recurso.quantidade_itens ?? 1);
    aplicarModoFormularioRecurso(true);
    el("formRecurso").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function carregarOpcoesProfessor() {
    const dados = await fetchJson("/admin/professores/opcoes", { headers });
    opcoesProfessor = {
        turmas: Array.isArray(dados.turmas) ? dados.turmas : [],
        disciplinas: Array.isArray(dados.disciplinas) ? dados.disciplinas : []
    };

    renderCheckboxes("profTurmasLista", opcoesProfessor.turmas, "turma");
    renderCheckboxes("profDisciplinasLista", opcoesProfessor.disciplinas, "disciplina");
}

async function carregarTurmasAdmin() {
    const turmas = await fetchJson("/admin/turmas?incluir_inativas=true", { headers });
    const ul = el("listaTurmasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(turmas) || turmas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    turmas.forEach((turma) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = turma.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turno: ${nomeTurno(turma.turno)} | Estudantes: ${turma.quantidade_estudantes ?? 0} | Status: ${turma.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputTurno = document.createElement("select");
        ["MATUTINO", "VESPERTINO", "VESPERTINO_EM", "INTEGRAL"].forEach((turno) => {
            const option = document.createElement("option");
            option.value = turno;
            option.innerText = nomeTurno(turno);
            inputTurno.appendChild(option);
        });
        inputTurno.value = turma.turno && TURNO_LABEL[turma.turno] ? turma.turno : "MATUTINO";

        const inputQuantidade = document.createElement("input");
        inputQuantidade.type = "number";
        inputQuantidade.min = "0";
        inputQuantidade.value = String(turma.quantidade_estudantes ?? 0);
        inputQuantidade.title = "Quantidade de estudantes";

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar dados";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        turno: inputTurno.value,
                        quantidade_estudantes: Number(inputQuantidade.value)
                    })
                });
                setMensagem("msgTurma", `Dados da turma ${turma.nome} atualizados.`);
                await carregarTurmasAdmin();
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = turma.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(turma.ativo) })
                });
                await Promise.all([carregarTurmasAdmin(), atualizarOpcoesProfessorSePermitido()]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        linha.appendChild(inputTurno);
        linha.appendChild(inputQuantidade);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarTurma(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/turmas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("turmaNome").value.trim(),
                turno: el("turmaTurno").value,
                quantidade_estudantes: Number(el("turmaQuantidadeEstudantes").value)
            })
        });

        setMensagem("msgTurma", "Turma cadastrada com sucesso.");
        el("formTurma").reset();
        el("turmaTurno").value = "MATUTINO";
        el("turmaQuantidadeEstudantes").value = "0";
        await Promise.all([carregarTurmasAdmin(), atualizarOpcoesProfessorSePermitido()]);
    } catch (err) {
        setMensagem("msgTurma", err.message, true);
    }
}

async function carregarDisciplinasAdmin() {
    const disciplinas = await fetchJson("/admin/disciplinas?incluir_inativas=true", { headers });
    const ul = el("listaDisciplinasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(disciplinas) || disciplinas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma disciplina cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    disciplinas.forEach((disciplina) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = disciplina.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Aulas semanais: ${disciplina.aulas_semanais ?? 0} | Status: ${disciplina.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(disciplina.aulas_semanais ?? 0);
        inputAulas.title = "Aulas semanais";

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar aulas";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value)
                    })
                });
                setMensagem("msgDisciplina", `Aulas da disciplina ${disciplina.nome} atualizadas.`);
                await carregarDisciplinasAdmin();
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = disciplina.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(disciplina.ativo) })
                });
                await Promise.all([carregarDisciplinasAdmin(), atualizarOpcoesProfessorSePermitido()]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        linha.appendChild(inputAulas);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarDisciplina(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/disciplinas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("disciplinaNome").value.trim(),
                aulas_semanais: Number(el("disciplinaAulasSemanais").value)
            })
        });

        setMensagem("msgDisciplina", "Disciplina cadastrada com sucesso.");
        el("formDisciplina").reset();
        el("disciplinaAulasSemanais").value = "0";
        await Promise.all([carregarDisciplinasAdmin(), atualizarOpcoesProfessorSePermitido()]);
    } catch (err) {
        setMensagem("msgDisciplina", err.message, true);
    }
}

function queryPeriodo(prefix = "") {
    const inicio = el(`${prefix}relDataInicio`) ? el(`${prefix}relDataInicio`).value : el("relDataInicio").value;
    const fim = el(`${prefix}relDataFim`) ? el(`${prefix}relDataFim`).value : el("relDataFim").value;

    const params = new URLSearchParams();
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

function queryHistorico() {
    const params = new URLSearchParams();
    const inicio = el("inicio").value;
    const fim = el("fim").value;
    if (inicio) params.set("data_inicio", inicio);
    if (fim) params.set("data_fim", fim);
    return params.toString() ? `?${params.toString()}` : "";
}

async function carregarFilaAdmin() {
    const jobs = await fetchJson("/admin/fila", { headers });
    const ul = el("fila-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const descricao = document.createElement("p");
        descricao.innerText = `${job.arquivo} | ${job.status} | ${job.paginas_totais ?? 0} páginas`;

        const actions = document.createElement("div");
        actions.className = "admin-inline";

        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarJob(job.id));

        const btnUrgente = document.createElement("button");
        btnUrgente.type = "button";
        btnUrgente.innerText = "Urgente";
        btnUrgente.addEventListener("click", () => prioridadeJob(job.id));

        actions.appendChild(btnCancelar);
        actions.appendChild(btnUrgente);
        li.appendChild(descricao);
        li.appendChild(actions);
        ul.appendChild(li);
    });
}

async function cancelarJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/cancelar`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function prioridadeJob(jobId) {
    try {
        await fetchJson(`/jobs/${jobId}/prioridade`, {
            method: "POST",
            headers
        });
        await carregarFilaAdmin();
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

async function buscarHistorico() {
    const jobs = await fetchJson(`/admin/historico${queryHistorico()}`, { headers });
    const ul = el("historico-admin");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${job.criado_em} | ${job.arquivo} | ${job.paginas_totais ?? 0} páginas | ${job.status}`;
        ul.appendChild(li);
    });
}

async function carregarProfessores() {
    const mes = el("mesReferenciaCota").value || mesAtualIso();
    const dados = await fetchJson(`/admin/professores?mes=${mes}`, { headers });

    if (dados.regras_cota) {
        el("cotaMensalEscola").value = dados.regras_cota.cota_mensal_escola ?? 0;
        el("cotaBase").value = dados.regras_cota.base_paginas ?? 0;
        el("cotaPorAula").value = dados.regras_cota.paginas_por_aula ?? 0;
        el("cotaPorTurma").value = dados.regras_cota.paginas_por_turma ?? 0;
    }

    const ul = el("listaProfessoresAdmin");
    ul.innerHTML = "";

    dados.professores.forEach((prof) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${prof.nome} (${prof.email})`;

        const cadastro = document.createElement("p");
        cadastro.className = "booking-detail";
        cadastro.innerText = `Nascimento: ${formatarDataBr(prof.data_nascimento)} | Turmas: ${resumoLista(prof.turmas)} | Disciplinas: ${resumoLista(prof.disciplinas)}`;

        const meta = document.createElement("p");
        const limiteMes = prof.cota_mes ? prof.cota_mes.limite_paginas : "-";
        const usadasMes = prof.cota_mes ? prof.cota_mes.usadas_paginas : "-";
        meta.className = "booking-detail";
        meta.innerText = `Projetada: ${prof.cota_projetada} | Mês: ${usadasMes}/${limiteMes}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(prof.aulas_semanais ?? "");
        inputAulas.title = "Aulas semanais";
        inputAulas.placeholder = "Quantidade de aulas semanais";

        const inputTurmas = document.createElement("input");
        inputTurmas.type = "number";
        inputTurmas.min = "0";
        inputTurmas.placeholder = "Quantidade de turmas";
        inputTurmas.value = String(prof.turmas_quantidade ?? "");
        inputTurmas.title = "Quantidade de turmas";

        const btnSalvar = document.createElement("button");
        btnSalvar.type = "button";
        btnSalvar.innerText = "Salvar carga";
        btnSalvar.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/professores/${prof.id}/carga`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value),
                        turmas_quantidade: Number(inputTurmas.value)
                    })
                });
                setMensagem("msgProfessor", `Carga atualizada para ${prof.nome}.`);
                await carregarProfessores();
            } catch (err) {
                setMensagem("msgProfessor", err.message, true);
            }
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar cadastro";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoProfessor(prof);
        });

        linha.appendChild(inputAulas);
        linha.appendChild(inputTurmas);
        linha.appendChild(btnSalvar);
        linha.appendChild(btnEditar);

        li.appendChild(titulo);
        li.appendChild(cadastro);
        li.appendChild(meta);
        li.appendChild(linha);
        ul.appendChild(li);
    });
}

async function carregarCoordenadores() {
    const ul = el("listaCoordenadoresAdmin");
    if (!ul || !usuarioEhAdmin) {
        return;
    }

    const coordenadores = await fetchJson("/admin/coordenadores", { headers });
    ul.innerHTML = "";

    if (!Array.isArray(coordenadores) || coordenadores.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhum coordenador cadastrado.";
        ul.appendChild(vazio);
        return;
    }

    coordenadores.forEach((coord) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = `${coord.nome} (${coord.email}) | Nascimento: ${formatarDataBr(coord.data_nascimento)}`;
        ul.appendChild(li);
    });
}

async function cadastrarProfessor(event) {
    event.preventDefault();
    if (!usuarioEhAdmin) {
        setMensagem("msgProfessor", "Apenas administradores podem cadastrar usuários.", true);
        return;
    }

    const cargoSelecionado = String(el("profCargo").value || CARGO_PROFESSOR).toUpperCase();
    const ehCoordenador = cargoSelecionado === CARGO_COORDENADOR;
    const turmas = listarSelecionados("profTurmasLista");
    const disciplinas = listarSelecionados("profDisciplinasLista");

    if (!ehCoordenador && turmas.length === 0) {
        setMensagem("msgProfessor", "Selecione ao menos uma turma.", true);
        return;
    }
    if (!ehCoordenador && disciplinas.length === 0) {
        setMensagem("msgProfessor", "Selecione ao menos uma disciplina.", true);
        return;
    }

    const payloadBase = {
        nome: el("profNome").value.trim(),
        email: el("profEmail").value.trim(),
        data_nascimento: el("profDataNascimento").value,
        aulas_semanais: Number(el("profAulas").value),
        turmas,
        disciplinas
    };

    try {
        if (professorEmEdicaoId) {
            if (ehCoordenador) {
                setMensagem("msgProfessor", "A edição deste formulário é exclusiva para professor.", true);
                return;
            }
            await fetchJson(`/admin/professores/${professorEmEdicaoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payloadBase)
            });
            setMensagem("msgProfessor", "Professor atualizado com sucesso.");
        } else {
            const senha = el("profSenha").value.trim();
            if (!validarSenhaForte(senha)) {
                setMensagem("msgProfessor", "Senha fora do padrão de segurança.", true);
                return;
            }

            if (ehCoordenador) {
                await fetchJson("/admin/coordenadores", {
                    method: "POST",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: payloadBase.nome,
                        email: payloadBase.email,
                        senha,
                        data_nascimento: payloadBase.data_nascimento
                    })
                });
                setMensagem("msgProfessor", "Coordenador cadastrado com sucesso.");
            } else {
                await fetchJson("/admin/professores", {
                    method: "POST",
                    headers: headersJson,
                    body: JSON.stringify({
                        ...payloadBase,
                        senha
                    })
                });
                setMensagem("msgProfessor", "Professor cadastrado com sucesso.");
            }
        }

        limparFormularioProfessor();
        if (ehCoordenador) {
            await carregarCoordenadores();
        } else {
            await carregarProfessores();
        }
    } catch (err) {
        setMensagem("msgProfessor", err.message, true);
    }
}

async function salvarRegrasCota(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/cotas/regras", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                cota_mensal_escola: Number(el("cotaMensalEscola").value),
                base_paginas: Number(el("cotaBase").value),
                paginas_por_aula: Number(el("cotaPorAula").value),
                paginas_por_turma: Number(el("cotaPorTurma").value)
            })
        });

        setMensagem("msgCotas", "Regras de cota atualizadas.");
        await carregarProfessores();
    } catch (err) {
        setMensagem("msgCotas", err.message, true);
    }
}

async function recalcularCotasMes() {
    try {
        const mes = el("mesReferenciaCota").value || mesAtualIso();
        await fetchJson(`/admin/cotas/recalcular?mes=${mes}`, {
            method: "POST",
            headers
        });
        setMensagem("msgCotas", `Cotas recalculadas para ${mes}.`);
        await carregarProfessores();
    } catch (err) {
        setMensagem("msgCotas", err.message, true);
    }
}

async function carregarRecursos() {
    const recursos = await fetchJson("/admin/recursos?incluir_inativos=true", { headers });
    const ul = el("listaRecursosAdmin");
    ul.innerHTML = "";

    recursos.forEach((recurso) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${recurso.nome} (${recurso.tipo})`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `${recurso.descricao || "Sem descrição"} | Quantidade: ${recurso.quantidade_itens ?? 1} | Status: ${recurso.ativo ? "Ativo" : "Inativo"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputQuantidadeItens = document.createElement("input");
        inputQuantidadeItens.type = "number";
        inputQuantidadeItens.min = "1";
        inputQuantidadeItens.value = String(recurso.quantidade_itens ?? 1);
        inputQuantidadeItens.title = "Quantidade de itens";

        const btnSalvarQuantidade = document.createElement("button");
        btnSalvarQuantidade.type = "button";
        btnSalvarQuantidade.innerText = "Salvar quantidade";
        btnSalvarQuantidade.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        nome: recurso.nome,
                        tipo: recurso.tipo,
                        descricao: recurso.descricao || "",
                        quantidade_itens: Number(inputQuantidadeItens.value)
                    })
                });
                setMensagem("msgRecurso", `Quantidade atualizada para ${recurso.nome}.`);
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar cadastro";
        btnEditar.addEventListener("click", () => {
            iniciarEdicaoRecurso(recurso);
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = recurso.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/recursos/${recurso.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(recurso.ativo) })
                });
                await carregarRecursos();
            } catch (err) {
                setMensagem("msgRecurso", err.message, true);
            }
        });

        linha.appendChild(inputQuantidadeItens);
        linha.appendChild(btnSalvarQuantidade);
        linha.appendChild(btnEditar);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarRecurso(event) {
    event.preventDefault();
    const payload = {
        nome: el("recursoNome").value.trim(),
        tipo: el("recursoTipo").value.trim(),
        descricao: el("recursoDescricao").value.trim(),
        quantidade_itens: Number(el("recursoQuantidadeItens").value)
    };

    try {
        if (recursoEmEdicaoId) {
            await fetchJson(`/admin/recursos/${recursoEmEdicaoId}`, {
                method: "PUT",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgRecurso", "Recurso atualizado com sucesso.");
        } else {
            await fetchJson("/admin/recursos", {
                method: "POST",
                headers: headersJson,
                body: JSON.stringify(payload)
            });
            setMensagem("msgRecurso", "Recurso cadastrado com sucesso.");
        }

        limparFormularioRecurso();
        await carregarRecursos();
    } catch (err) {
        setMensagem("msgRecurso", err.message, true);
    }
}

function renderListaRelatorio(id, itens, formatador, vazio = "Sem dados no período.") {
    const ul = el(id);
    ul.innerHTML = "";

    if (!itens || itens.length === 0) {
        const li = document.createElement("li");
        li.className = "booking-empty";
        li.innerText = vazio;
        ul.appendChild(li);
        return;
    }

    itens.forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";
        li.innerText = formatador(item);
        ul.appendChild(li);
    });
}

async function carregarRelatorios() {
    try {
        const query = queryPeriodo();
        const relImpressao = await fetchJson(`/admin/relatorio/impressao${query}`, { headers });
        const relRecursos = await fetchJson(`/admin/relatorio/recursos${query}`, { headers });

        renderListaRelatorio(
            "relatorioImpressaoAdmin",
            relImpressao,
            (item) => `${item.nome}: ${item.total_jobs} job(s), ${item.total_paginas} páginas`
        );

        renderListaRelatorio(
            "relatorioRecursosAdmin",
            relRecursos.por_recurso,
            (item) => `${item.recurso_nome} (${item.recurso_tipo}): ${item.total_reservas} reservas, ${item.professores_distintos} professor(es)`
        );

        renderListaRelatorio(
            "relatorioRecursosProfessorAdmin",
            relRecursos.por_professor,
            (item) => `${item.nome}: ${item.total_reservas} reserva(s)`
        );

        setMensagem("msgRelatorios", "Relatórios atualizados.");
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

function registrarEventos() {
    el("formTurma").addEventListener("submit", cadastrarTurma);
    el("formDisciplina").addEventListener("submit", cadastrarDisciplina);
    el("formRecurso").addEventListener("submit", cadastrarRecurso);
    el("btnCancelarEdicaoRecurso").addEventListener("click", limparFormularioRecurso);

    el("btnGerarRelatorios").addEventListener("click", carregarRelatorios);
    el("btnBuscarHistorico").addEventListener("click", buscarHistorico);

    if (usuarioEhAdmin) {
        el("formProfessor").addEventListener("submit", cadastrarProfessor);
        el("formCotaRegras").addEventListener("submit", salvarRegrasCota);
        el("profSenha").addEventListener("input", atualizarHintSenha);
        el("profCargo").addEventListener("change", () => {
            if (!professorEmEdicaoId) {
                aplicarModoFormularioProfessor(false);
            }
        });
        el("btnCancelarEdicaoProfessor").addEventListener("click", limparFormularioProfessor);
        el("btnRecalcularCotas").addEventListener("click", recalcularCotasMes);
        el("mesReferenciaCota").addEventListener("change", carregarProfessores);
    }

    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        localStorage.removeItem("token");
        localStorage.removeItem("token_expira_em");
        window.location.href = "/login-page";
    });
}

async function init() {
    try {
        await carregarUsuarioAtual();
        if (!usuarioEhGestor) {
            return;
        }

        aplicarPermissoesTela();

        if (usuarioEhAdmin) {
            el("mesReferenciaCota").value = mesAtualIso();
            await carregarOpcoesProfessor();
            limparFormularioProfessor();
        }
        limparFormularioRecurso();
        registrarEventos();
        if (usuarioEhAdmin) {
            atualizarHintSenha();
        }

        const tarefas = [
            carregarFilaAdmin(),
            buscarHistorico(),
            carregarRecursos(),
            carregarRelatorios(),
            carregarTurmasAdmin(),
            carregarDisciplinasAdmin()
        ];
        if (usuarioEhAdmin) {
            tarefas.push(carregarProfessores(), carregarCoordenadores());
        }
        await Promise.all(tarefas);
    } catch (err) {
        setMensagem("msgRelatorios", err.message, true);
    }
}

init();
