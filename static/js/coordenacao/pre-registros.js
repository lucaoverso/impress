const PRE_REGISTRATION_CONTACT_LABELS = {
    none: "Sem solicitacao de contato",
    communicate: "Comunicar o responsavel",
    summon: "Convocar o responsavel"
};

const PRE_REGISTRATION_STATUS_LABELS = {
    pending: "Pendente de complementacao",
    completed: "Concluido",
    cancelled: "Cancelado"
};

let motivosPreRegistroCache = [];
let timerBuscaEstudantePreRegistro = null;

function setMensagemPreRegistro(id, texto, erro = false) {
    const target = el(id);
    if (!target) return;
    target.innerText = texto || "";
    target.classList.toggle("erro", Boolean(erro));
}

function preencherMotivosPreRegistro(motivos) {
    motivosPreRegistroCache = Array.isArray(motivos) ? motivos : [];
    const select = el("preRegistroMotivoId");
    if (!select) return;
    select.innerHTML = '<option value="">Selecione um motivo cadastrado</option>';
    motivosPreRegistroCache.filter((motivo) => Boolean(motivo.active)).forEach((motivo) => {
        const option = document.createElement("option");
        option.value = String(motivo.id);
        option.innerText = motivo.name;
        select.appendChild(option);
    });
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
            el("preRegistroEstudanteId").value = String(estudante.id);
            el("preRegistroBuscaEstudante").value = estudante.label;
            lista.hidden = true;
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
    title.innerText = item.student_name;
    const status = document.createElement("span");
    status.className = `status-chip status-${item.status === "completed" ? "resolvido" : "aguardando_responsavel"}`;
    status.innerText = PRE_REGISTRATION_STATUS_LABELS[item.status] || item.status;
    header.append(title, status);

    const meta = document.createElement("div");
    meta.className = "coordenacao-pre-registration-meta";
    [
        `Turma: ${item.class_name || "Sem turma"}`,
        `Motivo: ${item.reason_name}`,
        PRE_REGISTRATION_CONTACT_LABELS[item.responsible_contact] || item.responsible_contact,
        manager ? `Professor: ${item.professor_name}` : "",
        `Enviado em: ${formatarDataHora(item.created_at)}`
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
        botao.innerText = "Complementar registro";
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
        vazio.innerText = "Nenhum pre-registro encontrado.";
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
    const studentId = Number(el("preRegistroEstudanteId").value || 0);
    const reasonId = Number(el("preRegistroMotivoId").value || 0);
    const contact = document.querySelector('[name="preRegistroContatoResponsavel"]:checked')?.value || "none";
    if (studentId <= 0) {
        setMensagemPreRegistro("msgPreRegistroProfessor", "Selecione um estudante da lista.", true);
        el("preRegistroBuscaEstudante").focus();
        return;
    }
    if (reasonId <= 0) {
        setMensagemPreRegistro("msgPreRegistroProfessor", "Selecione o motivo do pre-registro.", true);
        el("preRegistroMotivoId").focus();
        return;
    }
    await fetchJson("/occurrences/pre-registrations", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify({
            student_id: studentId,
            reason_id: reasonId,
            responsible_contact: contact
        })
    });
    el("formPreRegistroProfessor").reset();
    el("preRegistroEstudanteId").value = "";
    setMensagemPreRegistro("msgPreRegistroProfessor", "Pre-registro enviado a coordenacao.");
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
    renderSelecionadorEstudantesVinculados([{
        estudante_id: item.student_id,
        nome: item.student_name,
        turma_id: item.turma_id,
        turma_nome: item.class_name
    }]);
    el("ocorrenciaBuscaProfessor").value = item.professor_name || "";
    el("ocorrenciaProfessorRequerenteId").value = String(item.professor_id || "");
    atualizarModoFormularioRegistro();
    sincronizarTurmaOcorrenciaComEstudantes({ manterAulaAtual: false });
    definirDescricaoEditor({
        texto: `Motivo informado no pre-registro: ${item.reason_name}.\n${PRE_REGISTRATION_CONTACT_LABELS[item.responsible_contact] || ""}`
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
    el("formPreRegistroProfessor").addEventListener("submit", (event) => {
        salvarPreRegistroProfessor(event).catch((err) => {
            setMensagemPreRegistro("msgPreRegistroProfessor", err.message, true);
        });
    });
    el("preRegistroBuscaEstudante").addEventListener("input", () => {
        el("preRegistroEstudanteId").value = "";
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
