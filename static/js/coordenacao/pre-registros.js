const PRE_REGISTRATION_CONTACT_LABELS = {
    none: "Sem solicitação de contato",
    communicate: "Comunicar o responsável",
    summon: "Convocar o responsável"
};

const PRE_REGISTRATION_STATUS_LABELS = {
    pending: "Pendente de complementação",
    completed: "Concluído",
    cancelled: "Cancelado"
};

let motivosPreRegistroCache = [];
let timerBuscaEstudantePreRegistro = null;
let estudantesPreRegistroSelecionados = [];

function setMensagemPreRegistro(id, texto, erro = false) {
    const target = el(id);
    if (!target) return;
    target.innerText = texto || "";
    target.classList.toggle("erro", Boolean(erro));
}

function preencherMotivosPreRegistro(motivos) {
    motivosPreRegistroCache = Array.isArray(motivos) ? motivos : [];
    const container = el("preRegistroMotivos");
    if (!container) return;
    container.innerHTML = "";
    motivosPreRegistroCache.filter((motivo) => Boolean(motivo.active)).forEach((motivo) => {
        const label = document.createElement("label");
        const input = document.createElement("input");
        const text = document.createElement("span");
        input.type = "checkbox";
        input.name = "preRegistroMotivo";
        input.value = String(motivo.id);
        text.innerText = motivo.name;
        label.append(input, text);
        container.appendChild(label);
    });
}

function renderEstudantesPreRegistroSelecionados() {
    const container = el("preRegistroEstudantesSelecionados");
    if (!container) return;
    container.innerHTML = "";
    if (!estudantesPreRegistroSelecionados.length) {
        const empty = document.createElement("p");
        empty.className = "coordenacao-empty-state";
        empty.innerText = "Nenhum estudante selecionado.";
        container.appendChild(empty);
        return;
    }
    estudantesPreRegistroSelecionados.forEach((student) => {
        const item = document.createElement("div");
        item.className = "coordenacao-pre-selected-item";
        const text = document.createElement("span");
        text.innerText = `${student.nome} - ${student.turma_nome || "Sem turma"}`;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.setAttribute("aria-label", `Remover ${student.nome}`);
        remove.innerText = "Remover";
        remove.addEventListener("click", () => {
            estudantesPreRegistroSelecionados = estudantesPreRegistroSelecionados.filter(
                (itemSelecionado) => Number(itemSelecionado.id) !== Number(student.id)
            );
            renderEstudantesPreRegistroSelecionados();
        });
        item.append(text, remove);
        container.appendChild(item);
    });
}

function adicionarEstudantePreRegistro(student) {
    if (!estudantesPreRegistroSelecionados.some(
        (item) => Number(item.id) === Number(student.id)
    )) {
        estudantesPreRegistroSelecionados.push(student);
    }
    el("preRegistroBuscaEstudante").value = "";
    el("listaPreRegistroEstudantes").hidden = true;
    renderEstudantesPreRegistroSelecionados();
}

function renderSugestoesEstudantesPreRegistro(estudantes) {
    const lista = el("listaPreRegistroEstudantes");
    if (!lista) return;
    lista.innerHTML = "";
    if (!estudantes.length) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-autocomplete-empty";
        vazio.innerText = "Nenhum estudante encontrado.";
        lista.appendChild(vazio);
    }
    estudantes.forEach((estudante) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "coordenacao-autocomplete-item";
        const nome = document.createElement("strong");
        nome.innerText = estudante.nome;
        const turma = document.createElement("span");
        turma.innerText = estudante.turma_nome || "Sem turma";
        botao.append(nome, turma);
        botao.addEventListener("click", () => {
            adicionarEstudantePreRegistro(estudante);
        });
        lista.appendChild(botao);
    });
    lista.hidden = false;
}

async function buscarEstudantesPreRegistro() {
    const termo = String(el("preRegistroBuscaEstudante")?.value || "").trim();
    const estudantes = await fetchJson(
        `/occurrences/students?q=${encodeURIComponent(termo)}&limit=20`,
        { headers }
    );
    renderSugestoesEstudantesPreRegistro(Array.isArray(estudantes) ? estudantes : []);
}

function agendarBuscaEstudantesPreRegistro() {
    window.clearTimeout(timerBuscaEstudantePreRegistro);
    timerBuscaEstudantePreRegistro = window.setTimeout(() => {
        buscarEstudantesPreRegistro().catch((err) => {
            setMensagemPreRegistro("msgPreRegistroProfessor", err.message, true);
        });
    }, 220);
}

function criarCardPreRegistro(item, { manager = false } = {}) {
    const card = document.createElement("article");
    card.className = "coordenacao-pre-registration-item";
    const header = document.createElement("div");
    header.className = "coordenacao-pre-registration-item-header";
    const title = document.createElement("strong");
    title.innerText = (item.students || []).map((student) => student.name).join(", ")
        || item.student_name;
    const status = document.createElement("span");
    status.className = `status-chip status-${item.status === "completed" ? "resolvido" : "aguardando_responsavel"}`;
    status.innerText = PRE_REGISTRATION_STATUS_LABELS[item.status] || item.status;
    header.append(title, status);

    const meta = document.createElement("div");
    meta.className = "coordenacao-pre-registration-meta";
    [
        `Turma(s): ${[...new Set((item.students || []).map((student) => student.class_name).filter(Boolean))].join(", ") || item.class_name || "Sem turma"}`,
        `Motivo(s): ${(item.reasons || []).map((reason) => reason.name).join(", ") || item.reason_name}`,
        item.discipline ? `Disciplina: ${item.discipline}` : "",
        item.lesson ? `Aula: ${item.lesson}` : "",
        PRE_REGISTRATION_CONTACT_LABELS[item.responsible_contact] || item.responsible_contact,
        manager ? `Professor: ${item.professor_name}` : "",
        `Registrado em: ${formatarDataHora(item.occurred_at || item.created_at)}`
    ].filter(Boolean).forEach((texto) => {
        const linha = document.createElement("span");
        linha.innerText = texto;
        meta.appendChild(linha);
    });
    card.append(header, meta);

    if (manager && item.status === "pending") {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "btn-destaque";
        botao.innerText = "Concluir ocorrência";
        botao.addEventListener("click", () => iniciarComplementacaoPreRegistro(item));
        card.appendChild(botao);
    }
    return card;
}

function renderPreRegistros(containerId, items, options = {}) {
    const container = el(containerId);
    if (!container) return;
    container.innerHTML = "";
    if (!items.length) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = options.manager
            ? "Nenhuma pendência enviada pelos professores."
            : "Nenhum pre-registro encontrado.";
        container.appendChild(vazio);
        return;
    }
    items.forEach((item) => container.appendChild(criarCardPreRegistro(item, options)));
}

async function carregarPreRegistros({ manager = false } = {}) {
    const items = await fetchJson("/occurrences/pre-registrations", { headers });
    renderPreRegistros(
        manager ? "listaPreRegistrosGestao" : "listaMeusPreRegistros",
        Array.isArray(items) ? items : [],
        { manager }
    );
}

async function salvarPreRegistroProfessor(event) {
    event.preventDefault();
    const studentIds = estudantesPreRegistroSelecionados.map((student) => Number(student.id));
    const reasonIds = Array.from(
        document.querySelectorAll('[name="preRegistroMotivo"]:checked')
    ).map((input) => Number(input.value));
    const contact = document.querySelector('[name="preRegistroContatoResponsavel"]:checked')?.value || "none";
    if (!studentIds.length) {
        setMensagemPreRegistro("msgPreRegistroProfessor", "Selecione pelo menos um estudante.", true);
        el("preRegistroBuscaEstudante").focus();
        return;
    }
    if (!reasonIds.length) {
        setMensagemPreRegistro("msgPreRegistroProfessor", "Marque pelo menos um motivo.", true);
        el("preRegistroMotivos").querySelector("input")?.focus();
        return;
    }
    await fetchJson("/occurrences/pre-registrations", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            student_ids: studentIds,
            reason_ids: reasonIds,
            responsible_contact: contact
        })
    });
    el("formPreRegistroProfessor").reset();
    estudantesPreRegistroSelecionados = [];
    renderEstudantesPreRegistroSelecionados();
    setMensagemPreRegistro("msgPreRegistroProfessor", "Pré-registro enviado à coordenação.");
    await carregarPreRegistros();
}

function renderMotivosGestao() {
    const container = el("listaMotivosPreRegistro");
    if (!container) return;
    container.innerHTML = "";
    motivosPreRegistroCache.forEach((motivo) => {
        const item = document.createElement("div");
        item.className = "coordenacao-reason-item";
        item.classList.toggle("is-inactive", !Boolean(motivo.active));
        const nome = document.createElement("strong");
        nome.innerText = motivo.name;
        const botao = document.createElement("button");
        botao.type = "button";
        botao.innerText = motivo.active ? "Inativar" : "Ativar";
        botao.addEventListener("click", async () => {
            await fetchJson(`/occurrences/reasons/${motivo.id}`, {
                method: "PATCH",
                headers: headersJson,
                body: JSON.stringify({ active: !Boolean(motivo.active) })
            });
            await carregarContextoPreRegistros(true);
        });
        item.append(nome, botao);
        container.appendChild(item);
    });
}

async function salvarMotivoPreRegistro(event) {
    event.preventDefault();
    const input = el("motivoPreRegistroNome");
    await fetchJson("/occurrences/reasons", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({ name: input.value.trim() })
    });
    input.value = "";
    await carregarContextoPreRegistros(true);
}

function iniciarComplementacaoPreRegistro(item) {
    ativarAbaCoordenacao("ocorrencias");
    limparFormularioOcorrencia({ manterAberto: true });
    preRegistroEmComplementacaoId = Number(item.id);
    el("ocorrenciaTipoRegistro").value = "estudante";
    renderSelecionadorEstudantesVinculados((item.students || []).map((student) => ({
        estudante_id: student.student_id,
        nome: student.name,
        turma_id: student.class_id,
        turma_nome: student.class_name
    })));
    el("ocorrenciaBuscaProfessor").value = item.professor_name || "";
    el("ocorrenciaProfessorRequerenteId").value = String(item.professor_id || "");
    atualizarModoFormularioRegistro();
    sincronizarTurmaOcorrenciaComEstudantes({ manterAulaAtual: false });
    el("ocorrenciaDisciplina").value = item.discipline || "";
    if (item.lesson) {
        el("ocorrenciaAula").value = String(item.lesson);
    }
    const occurredAt = String(item.occurred_at || item.created_at || "");
    if (occurredAt) {
        const [datePart, timePart = ""] = occurredAt.replace("T", " ").split(" ");
        el("ocorrenciaData").value = datePart;
        el("ocorrenciaHorario").value = timePart.slice(0, 5);
    }
    definirDescricaoEditor({
        texto: `Motivos informados no pre-registro: ${(item.reasons || []).map((reason) => reason.name).join("; ") || item.reason_name}.\n${PRE_REGISTRATION_CONTACT_LABELS[item.responsible_contact] || ""}`
    });
    el("tituloFormOcorrencia").innerText = "Complementar pre-registro";
    ativarEtapaFormularioOcorrencia(1);
    atualizarPreviewOcorrencia();
}

async function carregarContextoPreRegistros(manager = false) {
    const context = await fetchJson("/occurrences/context", { headers });
    preencherMotivosPreRegistro(context.reasons || []);
    if (manager) renderMotivosGestao();
    return context;
}

function registrarEventosPreRegistrosProfessor() {
    renderEstudantesPreRegistroSelecionados();
    el("formPreRegistroProfessor").addEventListener("submit", (event) => {
        salvarPreRegistroProfessor(event).catch((err) => {
            setMensagemPreRegistro("msgPreRegistroProfessor", err.message, true);
        });
    });
    el("preRegistroBuscaEstudante").addEventListener("input", () => {
        agendarBuscaEstudantesPreRegistro();
    });
    el("preRegistroBuscaEstudante").addEventListener("focus", () => {
        buscarEstudantesPreRegistro().catch((err) => {
            setMensagemPreRegistro("msgPreRegistroProfessor", err.message, true);
        });
    });
}

function registrarEventosPreRegistrosGestao() {
    el("formMotivoPreRegistro").addEventListener("submit", (event) => {
        salvarMotivoPreRegistro(event).catch((err) => {
            setMensagemPreRegistro("msgPreRegistrosGestao", err.message, true);
        });
    });
    el("btnAtualizarPreRegistros").addEventListener("click", () => {
        carregarPreRegistros({ manager: true }).catch((err) => {
            setMensagemPreRegistro("msgPreRegistrosGestao", err.message, true);
        });
    });
}
