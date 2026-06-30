let acompanhamentoDocenteCache = [];
let acompanhamentoDocenteSelecionadoId = null;
let timerBuscaRegistroDocente = null;
const mapaBuscaRegistroDocente = new Map();

function setMensagemAcompanhamentoDocente(texto, erro = false) {
    const target = el("msgAcompanhamentoDocente");
    if (!target) return;
    target.innerText = texto || "";
    target.style.color = erro ? "#b42318" : "#0f766e";
}

function rotuloPercentualPrazo(valor) {
    if (valor === null || valor === undefined) return "Sem entregas";
    return `${Number(valor).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function rotuloTipoRegistroDocente(tipo) {
    const rotulos = {
        positive: "Positivo",
        attention: "Ponto de atencao",
        guidance: "Orientacao",
        informative: "Informativo"
    };
    return rotulos[tipo] || tipo || "Registro";
}

function obterFiltrosPeriodoAcompanhamentoDocente() {
    return {
        date_from: el("periodoInicialAcompanhamentoDocente")?.value || "",
        date_to: el("periodoFinalAcompanhamentoDocente")?.value || ""
    };
}

function montarQueryAcompanhamentoDocente(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([chave, valor]) => {
        if (valor !== null && valor !== undefined && String(valor).trim()) {
            query.set(chave, String(valor).trim());
        }
    });
    const texto = query.toString();
    return texto ? `?${texto}` : "";
}

function renderResumoPrazo(container, indicadores, labels = {}) {
    if (!container) return;
    container.innerHTML = "";
    [
        [labels.expected || "Atividades previstas", indicadores?.expected || 0],
        [labels.on_time || "No prazo", indicadores?.on_time || 0],
        [labels.late || "Com atraso", indicadores?.late || 0],
        [labels.pending || "Pendentes", indicadores?.pending || 0],
        [labels.percent || "Cumprimento", rotuloPercentualPrazo(indicadores?.on_time_percent)]
    ].forEach(([label, value]) => {
        const item = document.createElement("article");
        const strong = document.createElement("strong");
        strong.innerText = String(value);
        const span = document.createElement("span");
        span.innerText = label;
        item.appendChild(strong);
        item.appendChild(span);
        container.appendChild(item);
    });
}

function abrirModalRegistroDocente(professor = null) {
    const modal = el("modalRegistroDocente");
    if (!modal) return;
    el("formRegistroDocente")?.reset();
    el("registroDocenteData").value = new Date().toISOString().slice(0, 10);
    el("registroDocenteProfessorId").value = professor?.id ? String(professor.id) : "";
    el("registroDocenteProfessorBusca").value = professor?.name || "";
    ocultarSugestoes("listaRegistroDocenteProfessores");
    modal.hidden = false;
    document.body.classList.add("coordenacao-modal-open");
    modal.querySelector("[role='dialog']")?.focus();
}

function fecharModalRegistroDocente() {
    const modal = el("modalRegistroDocente");
    if (!modal) return;
    modal.hidden = true;
    document.body.classList.remove("coordenacao-modal-open");
    el("btnNovoRegistroDocente")?.focus();
}

function renderListaAcompanhamentoDocente(professores) {
    const lista = el("listaAcompanhamentoDocente");
    if (!lista) return;
    lista.innerHTML = "";

    if (!professores.length) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = "Nenhum professor encontrado para a busca atual.";
        lista.appendChild(vazio);
        return;
    }

    professores.forEach((professor) => {
        const card = document.createElement("article");
        card.className = "acompanhamento-docente-teacher";
        if (Number(professor.id) === Number(acompanhamentoDocenteSelecionadoId)) {
            card.classList.add("is-selected");
        }

        const header = document.createElement("div");
        header.className = "acompanhamento-docente-teacher-header";
        const title = document.createElement("div");
        const nome = document.createElement("h3");
        nome.innerText = professor.name || "Professor";
        const disciplina = document.createElement("p");
        disciplina.innerText = professor.discipline || "Sem disciplina vinculada";
        title.appendChild(nome);
        title.appendChild(disciplina);

        const botao = document.createElement("button");
        botao.type = "button";
        botao.innerText = "Ver perfil";
        botao.addEventListener("click", () => carregarPerfilAcompanhamentoDocente(professor.id));

        header.appendChild(title);
        header.appendChild(botao);
        card.appendChild(header);

        const metrics = document.createElement("dl");
        metrics.className = "acompanhamento-docente-metrics";
        [
            ["Previstas", professor.deadline_indicators?.expected || 0],
            ["No prazo", rotuloPercentualPrazo(professor.on_time_percent)],
            ["Atrasadas", professor.deadline_indicators?.late || 0],
            ["Pendentes", professor.deadline_indicators?.pending || 0],
            ["Positivos", professor.positive_count || 0],
            ["Atencao", professor.attention_count || 0]
        ].forEach(([label, value]) => {
            const group = document.createElement("div");
            const dt = document.createElement("dt");
            dt.innerText = label;
            const dd = document.createElement("dd");
            dd.innerText = String(value);
            group.appendChild(dt);
            group.appendChild(dd);
            metrics.appendChild(group);
        });
        card.appendChild(metrics);
        lista.appendChild(card);
    });
}

async function carregarAcompanhamentoDocente() {
    const query = el("buscaAcompanhamentoDocente")?.value || "";
    const periodo = obterFiltrosPeriodoAcompanhamentoDocente();
    setMensagemAcompanhamentoDocente("Carregando acompanhamento...");
    const resposta = await fetchJson(
        `/teacher-followup/teachers${montarQueryAcompanhamentoDocente({ q: query, ...periodo })}`,
        { headers }
    );
    acompanhamentoDocenteCache = Array.isArray(resposta.teachers) ? resposta.teachers : [];
    renderListaAcompanhamentoDocente(acompanhamentoDocenteCache);
    renderResumoPrazo(el("resumoPeriodoAcompanhamentoDocente"), resposta.period_summary || {});
    setMensagemAcompanhamentoDocente(
        acompanhamentoDocenteCache.length
            ? `${acompanhamentoDocenteCache.length} professor(es) encontrado(s).`
            : "Nenhum professor encontrado."
    );
}

function renderPerfilAcompanhamentoDocente(perfil) {
    const container = el("perfilAcompanhamentoDocente");
    if (!container) return;
    const professor = perfil.teacher || {};
    const indicadores = perfil.deadline_indicators || {};
    container.innerHTML = "";

    const header = document.createElement("div");
    header.className = "acompanhamento-docente-profile-header";
    const title = document.createElement("div");
    const nome = document.createElement("h2");
    nome.innerText = professor.name || "Professor";
    const disciplina = document.createElement("p");
    disciplina.innerText = professor.discipline || "Sem disciplina vinculada";
    title.appendChild(nome);
    title.appendChild(disciplina);

    const novo = document.createElement("button");
    novo.type = "button";
    novo.className = "btn-destaque";
    novo.innerText = "Novo registro";
    novo.addEventListener("click", () => abrirModalRegistroDocente(professor));
    header.appendChild(title);
    header.appendChild(novo);
    container.appendChild(header);

    const resumo = document.createElement("section");
    resumo.className = "acompanhamento-docente-summary";
    [
        ["Registros no periodo", perfil.period_summary?.records_total || 0],
        ["Entregas no prazo", rotuloPercentualPrazo(professor.on_time_percent)],
        ["Pendentes", indicadores.pending || 0],
        ["Atrasadas", indicadores.late || 0]
    ].forEach(([label, value]) => {
        const item = document.createElement("article");
        const strong = document.createElement("strong");
        strong.innerText = String(value);
        const span = document.createElement("span");
        span.innerText = label;
        item.appendChild(strong);
        item.appendChild(span);
        resumo.appendChild(item);
    });
    container.appendChild(resumo);

    const prazos = document.createElement("section");
    prazos.className = "acompanhamento-docente-deadlines";
    const prazosTitulo = document.createElement("h3");
    prazosTitulo.innerText = "Cumprimento de prazos";
    const prazosResumo = document.createElement("div");
    prazosResumo.className = "acompanhamento-docente-period-summary";
    renderResumoPrazo(prazosResumo, indicadores, {
        expected: "Atividades previstas",
        on_time: "Entregues no prazo",
        late: "Entregues com atraso",
        pending: "Ainda pendentes",
        percent: "Percentual no prazo"
    });
    prazos.appendChild(prazosTitulo);
    prazos.appendChild(prazosResumo);
    container.appendChild(prazos);

    const filtros = document.createElement("div");
    filtros.className = "acompanhamento-docente-filters";
    const todos = document.createElement("button");
    todos.type = "button";
    todos.innerText = "Todos";
    todos.addEventListener("click", () => carregarPerfilAcompanhamentoDocente(professor.id));
    filtros.appendChild(todos);
    (perfil.record_types || []).forEach((tipo) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.innerText = tipo.label;
        botao.addEventListener("click", () => carregarPerfilAcompanhamentoDocente(professor.id, tipo.id));
        filtros.appendChild(botao);
    });
    container.appendChild(filtros);

    const timeline = document.createElement("section");
    timeline.className = "acompanhamento-docente-timeline";
    const timelineTitle = document.createElement("h3");
    timelineTitle.innerText = "Linha do tempo";
    timeline.appendChild(timelineTitle);

    if (!Array.isArray(perfil.timeline) || perfil.timeline.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "coordenacao-empty-state";
        vazio.innerText = "Nenhum registro encontrado para o filtro atual.";
        timeline.appendChild(vazio);
    } else {
        perfil.timeline.forEach((registro) => {
            const item = document.createElement("article");
            item.className = `acompanhamento-docente-timeline-item is-${registro.type}`;
            const meta = document.createElement("div");
            meta.className = "acompanhamento-docente-timeline-meta";
            meta.innerText = `${formatarDataBr(registro.date)} - ${rotuloTipoRegistroDocente(registro.type)}`;
            const titulo = document.createElement("strong");
            titulo.innerText = registro.category || "Sem categoria";
            const descricao = document.createElement("p");
            descricao.innerText = registro.description || "";
            item.appendChild(meta);
            item.appendChild(titulo);
            item.appendChild(descricao);
            timeline.appendChild(item);
        });
    }
    container.appendChild(timeline);

    const avaliacoes = document.createElement("section");
    avaliacoes.className = "acompanhamento-docente-future";
    const avalTitle = document.createElement("h3");
    avalTitle.innerText = "Avaliacoes anteriores";
    const avalText = document.createElement("p");
    avalText.innerText = "Secao preparada para historico de avaliacoes futuras.";
    avaliacoes.appendChild(avalTitle);
    avaliacoes.appendChild(avalText);
    container.appendChild(avaliacoes);
}

async function carregarPerfilAcompanhamentoDocente(professorId, tipo = "") {
    acompanhamentoDocenteSelecionadoId = Number(professorId);
    renderListaAcompanhamentoDocente(acompanhamentoDocenteCache);
    const perfil = await fetchJson(
        `/teacher-followup/teachers/${professorId}${montarQueryAcompanhamentoDocente({
            type: tipo,
            ...obterFiltrosPeriodoAcompanhamentoDocente()
        })}`,
        { headers }
    );
    renderPerfilAcompanhamentoDocente(perfil);
}

function selecionarProfessorRegistroDocente(professor) {
    if (!professor) return;
    el("registroDocenteProfessorId").value = String(professor.id || "");
    el("registroDocenteProfessorBusca").value = professor.name || "";
    ocultarSugestoes("listaRegistroDocenteProfessores");
}

async function atualizarSugestoesRegistroDocente(forcar = false) {
    const termo = el("registroDocenteProfessorBusca")?.value || "";
    if (!forcar && termo.trim().length < 2) {
        ocultarSugestoes("listaRegistroDocenteProfessores");
        return;
    }
    const resposta = await fetchJson(`/teacher-followup/teachers/search?q=${encodeURIComponent(termo)}`, { headers });
    const professores = Array.isArray(resposta.teachers) ? resposta.teachers : [];
    mapaBuscaRegistroDocente.clear();
    preencherDatalist(
        "listaRegistroDocenteProfessores",
        mapaBuscaRegistroDocente,
        professores.map((professor) => ({
            ...professor,
            label: professor.name,
            nome: professor.name,
            email: professor.discipline || professor.email
        })),
        {
            textoVazio: "Nenhum professor encontrado.",
            onSelect: selecionarProfessorRegistroDocente
        }
    );
}

function aplicarSelecaoProfessorRegistroDocentePorTexto() {
    const item = obterItemSugestaoPorTexto(
        mapaBuscaRegistroDocente,
        el("registroDocenteProfessorBusca")?.value || ""
    );
    if (item) selecionarProfessorRegistroDocente(item);
}

async function salvarRegistroDocente(event) {
    event.preventDefault();
    aplicarSelecaoProfessorRegistroDocentePorTexto();
    const professorId = Number(el("registroDocenteProfessorId").value || 0);
    if (!professorId) {
        setMensagemAcompanhamentoDocente("Selecione um professor valido.", true);
        el("registroDocenteProfessorBusca").focus();
        return;
    }

    const payload = {
        teacher_id: professorId,
        record_type: el("registroDocenteTipo").value,
        category: el("registroDocenteCategoria").value,
        description: el("registroDocenteDescricao").value,
        record_date: el("registroDocenteData").value
    };
    await fetchJson("/teacher-followup/records", {
        method: "POST",
        headers: headersJson,
        body: JSON.stringify(payload)
    });
    fecharModalRegistroDocente();
    await carregarAcompanhamentoDocente();
    await carregarPerfilAcompanhamentoDocente(professorId);
    setMensagemAcompanhamentoDocente("Registro docente salvo.");
}

function registrarEventosAcompanhamentoDocente() {
    el("formBuscaAcompanhamentoDocente")?.addEventListener("submit", (event) => {
        event.preventDefault();
        carregarAcompanhamentoDocente().catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("btnLimparBuscaAcompanhamentoDocente")?.addEventListener("click", () => {
        el("buscaAcompanhamentoDocente").value = "";
        el("periodoInicialAcompanhamentoDocente").value = "";
        el("periodoFinalAcompanhamentoDocente").value = "";
        carregarAcompanhamentoDocente().catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("btnNovoRegistroDocente")?.addEventListener("click", () => abrirModalRegistroDocente());
    el("btnFecharRegistroDocente")?.addEventListener("click", fecharModalRegistroDocente);
    el("btnCancelarRegistroDocente")?.addEventListener("click", fecharModalRegistroDocente);
    el("modalRegistroDocente")?.addEventListener("click", (event) => {
        if (event.target.matches("[data-fechar-modal-docente]")) fecharModalRegistroDocente();
    });
    el("formRegistroDocente")?.addEventListener("submit", (event) => {
        salvarRegistroDocente(event).catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("registroDocenteProfessorBusca")?.addEventListener("input", () => {
        el("registroDocenteProfessorId").value = "";
        window.clearTimeout(timerBuscaRegistroDocente);
        timerBuscaRegistroDocente = window.setTimeout(() => {
            atualizarSugestoesRegistroDocente().catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
        }, 180);
    });
    el("registroDocenteProfessorBusca")?.addEventListener("focus", () => {
        atualizarSugestoesRegistroDocente(true).catch((err) => setMensagemAcompanhamentoDocente(err.message, true));
    });
    el("registroDocenteProfessorBusca")?.addEventListener("change", aplicarSelecaoProfessorRegistroDocentePorTexto);
    el("registroDocenteProfessorBusca")?.addEventListener("blur", aplicarSelecaoProfessorRegistroDocentePorTexto);
}
