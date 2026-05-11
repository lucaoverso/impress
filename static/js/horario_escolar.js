const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    encerrarSessao,
    modulosPermitidos,
    normalizarCargoUsuario,
} = window.AppAuth;
const { fetchJson } = window.AppApi;

const tokenHorario = garantirToken();
const headersHorario = criarHeadersAuth(tokenHorario);

let contextoHorario = {
    anos_letivos: [],
    dias_semana: [],
    turmas: [],
    disciplinas: [],
    professores: [],
};
let usuarioHorario = null;
let ultimoResultadoHorario = {
    total_registros: 0,
    itens: [],
    grupos_turma: [],
    grupos_professor: [],
};
let estadoMatrizHorario = null;

function setMensagemHorario(texto, erro = false) {
    const alvo = el("msgHorarioForm");
    if (!alvo) return;
    alvo.innerText = texto || "";
    alvo.style.color = erro ? "#b91c1c" : "#0f766e";
}

function preencherSelect(
    selectId,
    itens,
    { placeholder = "", incluirTodos = false, valor = "id", label = "nome" } = {}
) {
    const select = el(selectId);
    if (!select) return;
    select.innerHTML = "";

    if (placeholder) {
        const option = document.createElement("option");
        option.value = "";
        option.innerText = placeholder;
        option.disabled = !incluirTodos;
        option.selected = !incluirTodos;
        select.appendChild(option);
    }

    if (incluirTodos) {
        const optionTodos = document.createElement("option");
        optionTodos.value = "";
        optionTodos.innerText = "Todos";
        select.appendChild(optionTodos);
    }

    (itens || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item?.[valor] ?? "");
        option.innerText = String(item?.[label] ?? "");
        select.appendChild(option);
    });
}

function preencherSelectAnos(selectId, anos, { incluirTodos = false } = {}) {
    const itens = (anos || []).map((ano) => ({ id: ano, nome: String(ano) }));
    preencherSelect(selectId, itens, {
        placeholder: incluirTodos ? "" : "Selecione o ano",
        incluirTodos,
    });
}

function obterTurmaPorId(turmaId) {
    const valor = Number(turmaId || 0);
    return (contextoHorario.turmas || []).find((item) => Number(item.id) === valor) || null;
}

function obterDiaInfo(valor) {
    return (contextoHorario.dias_semana || []).find((item) => item.valor === valor) || null;
}

function labelAulaHorario(item = {}) {
    const faixaGlobal = Number(item.faixa_global || 0);
    const aulaNumero = Number(item.aula_numero || 0);
    if (aulaNumero > 0 && faixaGlobal > 0) {
        return `${aulaNumero}ª aula (faixa ${faixaGlobal})`;
    }
    if (aulaNumero > 0) {
        return `${aulaNumero}ª aula`;
    }
    return "";
}

function preencherContextoHorario() {
    preencherSelectAnos("horarioAnoLetivo", contextoHorario.anos_letivos);
    preencherSelect("horarioTurmaId", contextoHorario.turmas, {
        placeholder: "Selecione a turma",
    });

    preencherSelectAnos("filtroHorarioAnoLetivo", contextoHorario.anos_letivos, {
        incluirTodos: true,
    });
    preencherSelect("filtroHorarioTurmaId", contextoHorario.turmas, {
        incluirTodos: true,
    });
    preencherSelect("filtroHorarioProfessorId", contextoHorario.professores, {
        incluirTodos: true,
        label: "label",
    });
    preencherSelect("filtroHorarioDiaSemana", contextoHorario.dias_semana, {
        incluirTodos: true,
        valor: "valor",
        label: "label",
    });

    const anoAtual = String(contextoHorario.ano_letivo_atual || "");
    if (anoAtual) {
        el("horarioAnoLetivo").value = anoAtual;
        el("filtroHorarioAnoLetivo").value = anoAtual;
    }
}

function atualizarResumoHorario() {
    const gruposTurma = Array.isArray(ultimoResultadoHorario.grupos_turma)
        ? ultimoResultadoHorario.grupos_turma
        : [];
    const gruposProfessor = Array.isArray(ultimoResultadoHorario.grupos_professor)
        ? ultimoResultadoHorario.grupos_professor
        : [];

    el("horarioResumoRegistros").innerText = String(
        ultimoResultadoHorario.total_registros || 0
    );
    el("horarioResumoTurmas").innerText = String(gruposTurma.length);
    el("horarioResumoProfessores").innerText = String(gruposProfessor.length);

    const ano = String(el("filtroHorarioAnoLetivo")?.value || "").trim();
    const turmaId = String(el("filtroHorarioTurmaId")?.value || "").trim();
    const professorId = String(el("filtroHorarioProfessorId")?.value || "").trim();
    const dia = String(el("filtroHorarioDiaSemana")?.value || "").trim();

    const partes = [];
    if (ano) partes.push(`Ano ${ano}`);
    if (turmaId) {
        const turma = obterTurmaPorId(turmaId);
        if (turma?.nome) partes.push(`Turma ${turma.nome}`);
    }
    if (professorId) {
        const professor = (contextoHorario.professores || []).find(
            (item) => String(item.id) === professorId
        );
        if (professor?.nome) partes.push(professor.nome);
    }
    if (dia) {
        const diaInfo = obterDiaInfo(dia);
        if (diaInfo?.label) partes.push(diaInfo.label);
    }

    el("horarioResumoPeriodo").innerText =
        partes.length > 0 ? partes.join(" - ") : "Sem filtro aplicado.";
}

function criarBotaoAcao(texto, onClick, danger = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.innerText = texto;
    if (danger) button.className = "coordenacao-btn-danger";
    button.addEventListener("click", onClick);
    return button;
}

function serializarDragPayload(payload) {
    return JSON.stringify(payload || {});
}

function lerDragPayload(event) {
    try {
        return JSON.parse(event.dataTransfer.getData("application/x-horario-card") || "{}");
    } catch (_err) {
        return null;
    }
}

function registrarDragCard(elemento, payload) {
    if (!elemento) return;
    elemento.draggable = true;
    elemento.addEventListener("dragstart", (event) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData(
            "application/x-horario-card",
            serializarDragPayload(payload)
        );
        elemento.classList.add("is-dragging");
    });
    elemento.addEventListener("dragend", () => {
        elemento.classList.remove("is-dragging");
        document
            .querySelectorAll(".horario-slot.is-drop-target, .horario-drop-pool.is-drop-target")
            .forEach((node) => node.classList.remove("is-drop-target"));
    });
}

function configurarDropTarget(elemento, onDrop) {
    if (!elemento) return;
    elemento.addEventListener("dragover", (event) => {
        const payload = lerDragPayload(event);
        if (!payload) return;
        event.preventDefault();
        elemento.classList.add("is-drop-target");
    });
    elemento.addEventListener("dragleave", () => {
        elemento.classList.remove("is-drop-target");
    });
    elemento.addEventListener("drop", async (event) => {
        const payload = lerDragPayload(event);
        elemento.classList.remove("is-drop-target");
        if (!payload) return;
        event.preventDefault();
        await onDrop(payload);
    });
}

function obterAnoBuilder() {
    return Number(el("horarioAnoLetivo")?.value || 0);
}

function obterTurmaBuilderId() {
    return Number(el("horarioTurmaId")?.value || 0);
}

function atualizarCabecalhoBuilder() {
    const turma = obterTurmaPorId(obterTurmaBuilderId());
    const ano = obterAnoBuilder();
    const titulo = el("horarioBuilderTitulo");
    const meta = el("horarioBuilderMeta");
    const tituloMatriz = el("horarioMatrizTitulo");

    if (!turma || ano <= 0) {
        titulo.innerText = "Selecione uma turma para abrir a matriz.";
        meta.innerText =
            "Os cards ao lado serão gerados a partir das atribuições e da carga horária vinculada à turma.";
        tituloMatriz.innerText = "Matriz semanal";
        return;
    }

    titulo.innerText = `${turma.nome} - ${ano}`;
    meta.innerText = `${turma.turno || "Turno não informado"} com montagem visual por arraste.`;
    tituloMatriz.innerText = `Matriz semanal da turma ${turma.nome}`;
}

function limparMatrizHorario() {
    estadoMatrizHorario = null;
    el("horarioMatrizWrap").innerHTML =
        '<div class="horario-empty-state">Selecione uma turma para visualizar a matriz do horário.</div>';
    el("horarioCardsDisponiveis").innerHTML = "";
    el("horarioPoolMeta").innerHTML = "";
    el("horarioAlertas").hidden = true;
    el("horarioAlertas").innerHTML = "";
    atualizarCabecalhoBuilder();
}

async function recarregarDadosHorarioCompleto() {
    await Promise.all([carregarMatrizHorario(), carregarRegistrosHorario()]);
}

async function excluirRegistroHorario(id, mensagem = "Registro removido com sucesso.") {
    try {
        const resposta = await fetchJson(`/horario-escolar/registros/${id}`, {
            method: "DELETE",
            headers: headersHorario,
        });
        setMensagemHorario(resposta?.mensagem || mensagem);
        await recarregarDadosHorarioCompleto();
    } catch (err) {
        setMensagemHorario(err.message || "Falha ao remover o registro.", true);
    }
}

async function abrirTurmaNaMatriz(item) {
    if (item?.ano_letivo) {
        el("horarioAnoLetivo").value = String(item.ano_letivo);
    }
    if (item?.turma_id) {
        el("horarioTurmaId").value = String(item.turma_id);
    }
    await carregarMatrizHorario();
    document.querySelector(".horario-matrix-card")?.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
}

function renderizarGrupoHorario(grupo, modo = "turma") {
    const card = document.createElement("article");
    card.className = "horario-group-card";

    const header = document.createElement("div");
    header.className = "horario-group-header";

    const info = document.createElement("div");
    const titulo = document.createElement("h3");
    titulo.innerText =
        modo === "turma"
            ? `${grupo.turma_nome || "Turma não informada"}`
            : `${grupo.professor_nome || "Professor não informado"}`;
    info.appendChild(titulo);

    const subtitulo = document.createElement("p");
    subtitulo.innerText =
        modo === "turma"
            ? `${grupo.turno || "Turno não informado"} - Ano ${grupo.ano_letivo || "-"}`
            : `${grupo.professor_email || "Sem e-mail"} - Ano ${grupo.ano_letivo || "-"}`;
    info.appendChild(subtitulo);
    header.appendChild(info);

    const count = document.createElement("span");
    count.className = "horario-group-count";
    count.innerText = `${(grupo.itens || []).length} aula(s)`;
    header.appendChild(count);
    card.appendChild(header);

    const wrap = document.createElement("div");
    wrap.className = "horario-table-wrap";

    const table = document.createElement("table");
    table.className = "horario-table";

    const thead = document.createElement("thead");
    thead.innerHTML =
        modo === "turma"
            ? "<tr><th>Dia</th><th>Aula</th><th>Disciplina</th><th>Professor</th><th>Ações</th></tr>"
            : "<tr><th>Dia</th><th>Aula</th><th>Turma</th><th>Disciplina</th><th>Ações</th></tr>";
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    (grupo.itens || []).forEach((item) => {
        const tr = document.createElement("tr");

        const celulas = modo === "turma"
            ? [
                item.dia_semana_nome || item.dia_semana || "",
                labelAulaHorario(item),
                item.disciplina_nome || "",
                item.professor_nome || "",
            ]
            : [
                item.dia_semana_nome || item.dia_semana || "",
                labelAulaHorario(item),
                item.turma_nome || "",
                item.disciplina_nome || "",
            ];
        celulas.forEach((texto) => {
            const td = document.createElement("td");
            td.innerText = String(texto);
            tr.appendChild(td);
        });

        const tdAcoes = document.createElement("td");
        const acoes = document.createElement("div");
        acoes.className = "horario-inline-actions";
        acoes.appendChild(
            criarBotaoAcao("Abrir matriz", () => abrirTurmaNaMatriz(item))
        );
        acoes.appendChild(
            criarBotaoAcao(
                "Remover",
                () => excluirRegistroHorario(item.id),
                true
            )
        );
        tdAcoes.appendChild(acoes);
        tr.appendChild(tdAcoes);
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    card.appendChild(wrap);
    return card;
}

function renderizarAgrupamentosHorario() {
    const listaTurmas = el("horarioListaTurmas");
    const listaProfessores = el("horarioListaProfessores");
    listaTurmas.innerHTML = "";
    listaProfessores.innerHTML = "";

    const gruposTurma = Array.isArray(ultimoResultadoHorario.grupos_turma)
        ? ultimoResultadoHorario.grupos_turma
        : [];
    const gruposProfessor = Array.isArray(ultimoResultadoHorario.grupos_professor)
        ? ultimoResultadoHorario.grupos_professor
        : [];

    if (gruposTurma.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "horario-empty-state";
        vazio.innerText = "Nenhum horário encontrado para os filtros selecionados.";
        listaTurmas.appendChild(vazio);
    } else {
        gruposTurma.forEach((grupo) => {
            listaTurmas.appendChild(renderizarGrupoHorario(grupo, "turma"));
        });
    }

    if (gruposProfessor.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "horario-empty-state";
        vazio.innerText = "Nenhum professor com horário no recorte atual.";
        listaProfessores.appendChild(vazio);
    } else {
        gruposProfessor.forEach((grupo) => {
            listaProfessores.appendChild(renderizarGrupoHorario(grupo, "professor"));
        });
    }
}

async function carregarRegistrosHorario() {
    const params = new URLSearchParams();
    const ano = String(el("filtroHorarioAnoLetivo")?.value || "").trim();
    const turmaId = String(el("filtroHorarioTurmaId")?.value || "").trim();
    const professorId = String(el("filtroHorarioProfessorId")?.value || "").trim();
    const dia = String(el("filtroHorarioDiaSemana")?.value || "").trim();

    if (ano) params.set("ano_letivo", ano);
    if (turmaId) params.set("turma_id", turmaId);
    if (professorId) params.set("professor_id", professorId);
    if (dia) params.set("dia_semana", dia);

    const sufixo = params.toString() ? `?${params.toString()}` : "";
    ultimoResultadoHorario = await fetchJson(`/horario-escolar/registros${sufixo}`, {
        headers: headersHorario,
    });
    atualizarResumoHorario();
    renderizarAgrupamentosHorario();
}

function renderizarAlertasHorario(alertas) {
    const container = el("horarioAlertas");
    container.innerHTML = "";
    if (!Array.isArray(alertas) || alertas.length === 0) {
        container.hidden = true;
        return;
    }

    alertas.forEach((texto) => {
        const aviso = document.createElement("div");
        aviso.className = "horario-alert-item";
        aviso.innerText = String(texto || "");
        container.appendChild(aviso);
    });
    container.hidden = false;
}

function renderizarMetaPool(cardsResumo, cardsDisponiveis) {
    const alvo = el("horarioPoolMeta");
    alvo.innerHTML = "";

    const totalDisponiveis = Array.isArray(cardsDisponiveis) ? cardsDisponiveis.length : 0;
    const totalPlanejado = (cardsResumo || []).reduce(
        (soma, item) => soma + Number(item.quantidade_total || 0),
        0
    );

    const resumo = document.createElement("p");
    resumo.className = "horario-pool-summary";
    resumo.innerText = `${totalDisponiveis} card(s) disponível(is) de ${totalPlanejado} aula(s) planejada(s).`;
    alvo.appendChild(resumo);

    if (!Array.isArray(cardsResumo) || cardsResumo.length === 0) {
        return;
    }

    const chips = document.createElement("div");
    chips.className = "horario-pool-chips";
    cardsResumo.forEach((item) => {
        const chip = document.createElement("span");
        chip.className = "horario-pool-chip";
        chip.innerText = `${item.disciplina_nome}: ${item.quantidade_alocada}/${item.quantidade_total}`;
        chips.appendChild(chip);
    });
    alvo.appendChild(chips);
}

async function processarDropNaCelula(payload, diaSemana, aulaNumero, celulaOcupada) {
    if (!payload || !diaSemana || !aulaNumero) return;

    if (payload.source === "scheduled") {
        if (
            String(payload.dia_semana || "") === String(diaSemana) &&
            Number(payload.aula_numero || 0) === Number(aulaNumero)
        ) {
            return;
        }
        if (celulaOcupada) {
            setMensagemHorario("Esse campo já possui uma aula. Remova ou reposicione a atual antes de continuar.", true);
            return;
        }
        try {
            await fetchJson(`/horario-escolar/registros/${payload.registro_id}`, {
                method: "PUT",
                headers: Object.assign({}, headersHorario, {
                    "Content-Type": "application/json",
                }),
                body: JSON.stringify({
                    ano_letivo: payload.ano_letivo,
                    turma_id: payload.turma_id,
                    disciplina_id: payload.disciplina_id,
                    professor_id: payload.professor_id,
                    dia_semana: diaSemana,
                    aula_numero: Number(aulaNumero),
                }),
            });
            setMensagemHorario("Aula reposicionada com sucesso.");
            await recarregarDadosHorarioCompleto();
        } catch (err) {
            setMensagemHorario(err.message || "Não foi possível reposicionar a aula.", true);
        }
        return;
    }

    if (payload.source === "available") {
        if (celulaOcupada) {
            setMensagemHorario("Esse campo já possui uma aula. Escolha outro horário vazio.", true);
            return;
        }
        try {
            await fetchJson("/horario-escolar/registros", {
                method: "POST",
                headers: Object.assign({}, headersHorario, {
                    "Content-Type": "application/json",
                }),
                body: JSON.stringify({
                    ano_letivo: obterAnoBuilder(),
                    turma_id: obterTurmaBuilderId(),
                    disciplina_id: payload.disciplina_id,
                    professor_id: payload.professor_id,
                    dia_semana: diaSemana,
                    aula_numero: Number(aulaNumero),
                }),
            });
            setMensagemHorario("Aula criada com sucesso.");
            await recarregarDadosHorarioCompleto();
        } catch (err) {
            setMensagemHorario(err.message || "Não foi possível criar a aula.", true);
        }
    }
}

function criarCardVisualHorario(payload, { agendado = false } = {}) {
    const card = document.createElement("article");
    card.className = `horario-card-item${agendado ? " is-scheduled" : ""}`;

    const topo = document.createElement("div");
    topo.className = "horario-card-top";

    const titulo = document.createElement("strong");
    titulo.innerText = payload.disciplina_nome || "Disciplina";
    topo.appendChild(titulo);

    const badge = document.createElement("span");
    badge.className = "horario-card-badge";
    badge.innerText = agendado ? "Alocada" : "Disponível";
    topo.appendChild(badge);
    card.appendChild(topo);

    const professor = document.createElement("p");
    professor.className = "horario-card-professor";
    professor.innerText = payload.professor_nome || "Professor não informado";
    card.appendChild(professor);

    if (!agendado) {
        const meta = document.createElement("small");
        meta.className = "horario-card-meta";
        meta.innerText = `Card ${payload.indice_disponivel || 1} de ${payload.quantidade_total || 1}`;
        card.appendChild(meta);
    } else {
        const meta = document.createElement("small");
        meta.className = "horario-card-meta";
        meta.innerText = `${payload.dia_semana_nome || payload.dia_semana || ""} - ${labelAulaHorario(payload)}`;
        card.appendChild(meta);
    }

    if (agendado) {
        const remover = criarBotaoAcao(
            "Remover",
            () => excluirRegistroHorario(payload.registro_id, "Aula removida da matriz."),
            true
        );
        remover.classList.add("horario-card-remove");
        card.appendChild(remover);
    }

    registrarDragCard(card, payload);
    return card;
}

function renderizarPoolCards(cardsDisponiveis) {
    const container = el("horarioCardsDisponiveis");
    container.innerHTML = "";

    if (!Array.isArray(cardsDisponiveis) || cardsDisponiveis.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "horario-empty-state";
        vazio.innerText = "Nenhum card disponível para esta turma. Verifique a carga horária ou as aulas já alocadas.";
        container.appendChild(vazio);
        return;
    }

    cardsDisponiveis.forEach((item) => {
        const card = criarCardVisualHorario(
            {
                ...item,
                source: "available",
            },
            { agendado: false }
        );
        container.appendChild(card);
    });
}

function renderizarMatrizHorario() {
    const wrap = el("horarioMatrizWrap");
    wrap.innerHTML = "";

    if (!estadoMatrizHorario || !estadoMatrizHorario.turma) {
        wrap.innerHTML =
            '<div class="horario-empty-state">Selecione uma turma para visualizar a matriz do horário.</div>';
        return;
    }

    const tabela = document.createElement("table");
    tabela.className = "horario-matrix-table";

    const thead = document.createElement("thead");
    const trHead = document.createElement("tr");
    const thAula = document.createElement("th");
    thAula.innerText = "Aula";
    trHead.appendChild(thAula);
    (estadoMatrizHorario.dias_semana || []).forEach((dia) => {
        const th = document.createElement("th");
        th.innerText = dia.label;
        trHead.appendChild(th);
    });
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const mapaRegistros = new Map();
    (estadoMatrizHorario.registros || []).forEach((item) => {
        mapaRegistros.set(
            `${item.dia_semana}:${item.aula_numero}`,
            item
        );
    });

    const tbody = document.createElement("tbody");
    const faixas = Array.isArray(estadoMatrizHorario.faixas) && estadoMatrizHorario.faixas.length > 0
        ? estadoMatrizHorario.faixas
        : (estadoMatrizHorario.aulas || []).map((aulaNumero) => ({
            aula_numero: aulaNumero,
            faixa_global: 0,
            label: `${aulaNumero}a aula`,
            label_curta: `${aulaNumero}a aula`,
        }));

    faixas.forEach((faixaInfo) => {
        const aulaNumero = Number(faixaInfo.aula_numero || 0);
        const tr = document.createElement("tr");
        const th = document.createElement("th");
        th.innerText = faixaInfo.label || `${aulaNumero}a aula`;
        tr.appendChild(th);

        (estadoMatrizHorario.dias_semana || []).forEach((dia) => {
            const td = document.createElement("td");
            td.className = "horario-slot";
            td.dataset.diaSemana = dia.valor;
            td.dataset.aulaNumero = String(aulaNumero);
            td.dataset.faixaGlobal = String(faixaInfo.faixa_global || 0);

            const registro = mapaRegistros.get(`${dia.valor}:${aulaNumero}`) || null;
            if (registro) {
                td.classList.add("is-occupied");
                const card = criarCardVisualHorario(
                    {
                        ...registro,
                        registro_id: registro.id,
                        source: "scheduled",
                    },
                    { agendado: true }
                );
                td.appendChild(card);
            } else {
                const hint = document.createElement("span");
                hint.className = "horario-slot-hint";
                hint.innerText = "Solte aqui";
                td.appendChild(hint);
            }

            configurarDropTarget(td, async (payload) => {
                await processarDropNaCelula(payload, dia.valor, aulaNumero, Boolean(registro));
            });
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    tabela.appendChild(tbody);
    wrap.appendChild(tabela);
}

async function carregarMatrizHorario() {
    atualizarCabecalhoBuilder();

    const turmaId = obterTurmaBuilderId();
    const anoLetivo = obterAnoBuilder();
    if (turmaId <= 0 || anoLetivo <= 0) {
        limparMatrizHorario();
        return;
    }

    try {
        estadoMatrizHorario = await fetchJson(
            `/horario-escolar/turmas/${turmaId}/matriz?ano_letivo=${anoLetivo}`,
            { headers: headersHorario }
        );
        atualizarCabecalhoBuilder();
        renderizarAlertasHorario(estadoMatrizHorario.alertas || []);
        renderizarMetaPool(
            estadoMatrizHorario.cards_resumo || [],
            estadoMatrizHorario.cards_disponiveis || []
        );
        renderizarPoolCards(estadoMatrizHorario.cards_disponiveis || []);
        renderizarMatrizHorario();
    } catch (err) {
        limparMatrizHorario();
        setMensagemHorario(err.message || "Não foi possível carregar a matriz da turma.", true);
    }
}

function configurarDropPool() {
    const pool = el("horarioDropPool");
    configurarDropTarget(pool, async (payload) => {
        if (!payload || payload.source !== "scheduled" || !payload.registro_id) {
            return;
        }
        await excluirRegistroHorario(payload.registro_id, "Aula devolvida para o pool.");
    });
}

function registrarEventosHorario() {
    el("formFiltrosHorarioEscolar")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarRegistrosHorario();
    });
    el("btnLimparFiltrosHorario")?.addEventListener("click", async () => {
        el("formFiltrosHorarioEscolar").reset();
        if (contextoHorario.ano_letivo_atual) {
            el("filtroHorarioAnoLetivo").value = String(contextoHorario.ano_letivo_atual);
        }
        await carregarRegistrosHorario();
    });

    el("horarioAnoLetivo")?.addEventListener("change", async () => {
        await carregarMatrizHorario();
    });
    el("horarioTurmaId")?.addEventListener("change", async () => {
        await carregarMatrizHorario();
    });

    el("btnVoltarServicos")?.addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnSair")?.addEventListener("click", () => {
        encerrarSessao();
    });
    el("btnIrAdmin")?.addEventListener("click", () => {
        window.location.href = "/admin";
    });

    configurarDropPool();
}

async function carregarContextoHorario() {
    contextoHorario = await fetchJson("/horario-escolar/contexto", {
        headers: headersHorario,
    });
    preencherContextoHorario();
}

async function validarAcessoHorario() {
    usuarioHorario = await fetchJson("/me", { headers: headersHorario });
    const modulos = modulosPermitidos(usuarioHorario);
    if (!modulos.has("horario")) {
        window.location.href = "/servicos";
        return false;
    }

    const btnIrAdmin = el("btnIrAdmin");
    if (btnIrAdmin) {
        btnIrAdmin.hidden = normalizarCargoUsuario(usuarioHorario) !== "ADMIN";
    }
    return true;
}

async function initHorarioEscolar() {
    try {
        registrarEventosHorario();
        const acessoValido = await validarAcessoHorario();
        if (!acessoValido) return;
        await carregarContextoHorario();
        await Promise.all([carregarMatrizHorario(), carregarRegistrosHorario()]);
    } catch (_err) {
        encerrarSessao();
    }
}

window.addEventListener("DOMContentLoaded", initHorarioEscolar);
