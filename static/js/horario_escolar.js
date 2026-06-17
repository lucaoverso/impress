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
    grade_aulas: [],
    turmas: [],
    disciplinas: [],
    professores: [],
    modo_interface: "gestor",
    permite_edicao: false,
    professor_logado_id: null,
};
let usuarioHorario = null;
let ultimoResultadoHorario = {
    total_registros: 0,
    itens: [],
    grupos_turma: [],
    grupos_professor: [],
    modo_interface: "gestor",
    professor_logado_id: null,
};
let estadoMatrizHorario = null;
let escopoProfessorHorario = "geral";
let modoVisualizacaoGestorHorario = "turmas";
const TIPO_GRADE_AULA = "AULA";
const TIPO_GRADE_INTERVALO = "INTERVALO";

function interfaceProfessorAtiva() {
    return String(contextoHorario.modo_interface || "").toLowerCase() === "professor";
}

function interfaceGestorAtiva() {
    return !interfaceProfessorAtiva();
}

function visualizacaoGestorPorProfessorAtiva() {
    return interfaceGestorAtiva() && modoVisualizacaoGestorHorario === "professores";
}

function permiteEdicaoHorario() {
    return Boolean(contextoHorario.permite_edicao);
}

function obterProfessorLogadoId() {
    const contextoId = Number(contextoHorario.professor_logado_id || 0);
    if (contextoId > 0) return contextoId;
    const usuarioId = Number(usuarioHorario?.id || 0);
    return usuarioId > 0 ? usuarioId : 0;
}

function itemEhDoProfessorLogado(item = {}) {
    if (typeof item.eh_do_professor_logado === "boolean") {
        return item.eh_do_professor_logado;
    }
    const professorId = obterProfessorLogadoId();
    return professorId > 0 && Number(item.professor_id || 0) === professorId;
}

function filtrarItensEscopoProfessor(itens) {
    const lista = Array.isArray(itens) ? itens : [];
    if (!interfaceProfessorAtiva()) {
        return lista;
    }
    if (escopoProfessorHorario === "minhas") {
        return lista.filter((item) => itemEhDoProfessorLogado(item));
    }
    if (escopoProfessorHorario === "colegas") {
        return lista.filter((item) => !itemEhDoProfessorLogado(item));
    }
    return lista;
}

function agruparItensPorChave(itens, modo) {
    const grupos = new Map();
    (itens || []).forEach((item) => {
        const chave = modo === "professor"
            ? `${item.ano_letivo}:${item.professor_id}`
            : `${item.ano_letivo}:${item.turma_id}`;
        if (!grupos.has(chave)) {
            grupos.set(
                chave,
                modo === "professor"
                    ? {
                        ano_letivo: Number(item.ano_letivo || 0),
                        professor_id: Number(item.professor_id || 0),
                        professor_nome: item.professor_nome || "",
                        professor_email: item.professor_email || "",
                        itens: [],
                    }
                    : {
                        ano_letivo: Number(item.ano_letivo || 0),
                        turma_id: Number(item.turma_id || 0),
                        turma_nome: item.turma_nome || "",
                        turno: item.turno || "",
                        itens: [],
                    }
            );
        }
        grupos.get(chave).itens.push(item);
    });
    return Array.from(grupos.values());
}

function obterResultadoHorarioFiltrado() {
    const itens = filtrarItensEscopoProfessor(ultimoResultadoHorario.itens);
    return {
        itens,
        grupos_turma: agruparItensPorChave(itens, "turma"),
        grupos_professor: agruparItensPorChave(itens, "professor"),
    };
}

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
    const aulaNumero = Number(item.aula_numero || 0);
    if (String(item?.aula_label || "").trim()) {
        return String(item.aula_label).trim();
    }

    const aulaConfig = obterAulaGlobalHorario(aulaNumero || item.faixa_global);
    if (aulaConfig?.label) {
        return String(aulaConfig.label).trim();
    }

    if (aulaNumero > 0) {
        return `${aulaNumero}a aula`;
    }
    return "";
}

function itensGradeHorarioAtivos() {
    return (Array.isArray(contextoHorario.grade_aulas) ? contextoHorario.grade_aulas : [])
        .filter((item) => Boolean(item?.ativo ?? true))
        .sort((a, b) => Number(a?.ordem_visual || 0) - Number(b?.ordem_visual || 0));
}

function aulasGlobaisHorarioAtivas() {
    return itensGradeHorarioAtivos()
        .filter((item) => String(item?.tipo || "").trim().toUpperCase() === TIPO_GRADE_AULA)
        .sort((a, b) => Number(a?.aula_numero || 0) - Number(b?.aula_numero || 0));
}

function obterAulaGlobalHorario(aulaNumero) {
    const valor = Number(aulaNumero || 0);
    return aulasGlobaisHorarioAtivas()
        .find((item) => Number(item?.aula_numero || 0) === valor) || null;
}

function obterJanelaAulasTurmaHorario(grupo = {}) {
    const turma = obterTurmaPorId(grupo.turma_id);
    const aulasConfiguradas = aulasGlobaisHorarioAtivas();
    const primeiraAula = Number(aulasConfiguradas[0]?.aula_numero || 0);
    const ultimaAula = Number(aulasConfiguradas[aulasConfiguradas.length - 1]?.aula_numero || 0);

    let aulaInicial = Number(grupo.aula_inicial || turma?.aula_inicial || 0);
    let aulaFinal = Number(grupo.aula_final || turma?.aula_final || 0);

    if (aulaInicial <= 0) {
        aulaInicial = primeiraAula;
    }
    if (aulaFinal < aulaInicial) {
        aulaFinal = ultimaAula || aulaInicial;
    }

    return [aulaInicial, aulaFinal];
}

function criarGradeFallbackTurmaHorario(grupo = {}) {
    const [aulaInicial, aulaFinal] = obterJanelaAulasTurmaHorario(grupo);
    if (aulaInicial <= 0 || aulaFinal < aulaInicial) {
        return [];
    }
    return Array.from({ length: aulaFinal - aulaInicial + 1 }, (_, index) => {
        const aulaNumero = aulaInicial + index;
        return {
            tipo: TIPO_GRADE_AULA,
            aula_numero: aulaNumero,
            faixa_global: aulaNumero,
            label: `${aulaNumero}a aula`,
            label_curta: `${aulaNumero}a aula`,
        };
    });
}

function adicionarFaixasRegistrosOcultos(faixas, itens) {
    const resultado = Array.isArray(faixas) ? faixas.map((item) => ({ ...item })) : [];
    const aulasVisiveis = new Set(
        resultado
            .filter((item) => String(item?.tipo || "").trim().toUpperCase() === TIPO_GRADE_AULA)
            .map((item) => Number(item?.aula_numero || 0))
            .filter((numero) => numero > 0)
    );

    (itens || []).forEach((item) => {
        const aulaNumero = Number(item?.aula_numero || 0);
        if (aulaNumero <= 0 || aulasVisiveis.has(aulaNumero)) return;

        resultado.push({
            tipo: TIPO_GRADE_AULA,
            aula_numero: aulaNumero,
            faixa_global: Number(item?.faixa_global || aulaNumero),
            label: `${labelAulaHorario(item) || `${aulaNumero}a aula`} (fora da janela atual)`,
            label_curta: `${aulaNumero}a aula`,
            ordem_visual: aulaNumero,
            fora_janela_turma: true,
            aceita_lancamento: false,
        });
        aulasVisiveis.add(aulaNumero);
    });

    return resultado.sort((atual, proxima) => {
        const ordemAtual = Number(atual?.ordem_visual || atual?.aula_numero || 0);
        const ordemProxima = Number(proxima?.ordem_visual || proxima?.aula_numero || 0);
        if (ordemAtual !== ordemProxima) return ordemAtual - ordemProxima;
        return Number(atual?.aula_numero || 0) - Number(proxima?.aula_numero || 0);
    });
}

function obterFaixasGrupoTurma(grupo = {}) {
    const itensGrade = itensGradeHorarioAtivos();
    if (itensGrade.length === 0) {
        return adicionarFaixasRegistrosOcultos(
            criarGradeFallbackTurmaHorario(grupo),
            grupo.itens || []
        );
    }

    const [aulaInicial, aulaFinal] = obterJanelaAulasTurmaHorario(grupo);
    const faixas = itensGrade.filter((item, index, lista) => {
        const tipo = String(item?.tipo || "").trim().toUpperCase();
        if (tipo === TIPO_GRADE_AULA) {
            const aulaNumero = Number(item?.aula_numero || 0);
            return aulaNumero >= aulaInicial && aulaNumero <= aulaFinal;
        }

        if (tipo !== TIPO_GRADE_INTERVALO) {
            return false;
        }

        const itensAnteriores = lista
            .slice(0, index)
            .filter((candidato) => String(candidato?.tipo || "").trim().toUpperCase() === TIPO_GRADE_AULA)
            .map((candidato) => Number(candidato?.aula_numero || 0))
            .filter((numero) => numero > 0);
        const itensPosteriores = lista
            .slice(index + 1)
            .filter((candidato) => String(candidato?.tipo || "").trim().toUpperCase() === TIPO_GRADE_AULA)
            .map((candidato) => Number(candidato?.aula_numero || 0))
            .filter((numero) => numero > 0);

        const aulaAnterior = itensAnteriores[itensAnteriores.length - 1] || 0;
        const aulaPosterior = itensPosteriores[0] || 0;
        return (
            aulaAnterior > 0
            && aulaPosterior > 0
            && aulaAnterior >= aulaInicial
            && aulaPosterior <= aulaFinal
        );
    });
    return adicionarFaixasRegistrosOcultos(faixas, grupo.itens || []);
}

function descricaoCelulaHorarioProfessor(item) {
    const disciplina = String(item?.disciplina_nome || "").trim();
    const professor = String(item?.professor_nome || "").trim();
    if (disciplina && professor) {
        return `${disciplina} - ${professor}`;
    }
    return disciplina || professor || "";
}

function atualizarTitulosConsultaHorario() {
    const turmasEyebrow = el("horarioTurmasEyebrow");
    const turmasTitulo = el("horarioTurmasTitulo");
    const turmasDescricao = el("horarioTurmasDescricao");

    if (!turmasEyebrow || !turmasTitulo || !turmasDescricao) {
        return;
    }

    if (interfaceProfessorAtiva() && escopoProfessorHorario === "minhas") {
        turmasEyebrow.innerText = "Minha agenda";
        turmasTitulo.innerText = "Meu horario";
        turmasDescricao.innerText =
            "Grade semanal consolidada com os dias, as disciplinas e as turmas do professor logado.";
        return;
    }

    if (interfaceProfessorAtiva()) {
        turmasEyebrow.innerText = "Visao do professor";
        turmasTitulo.innerText = "Horario por turma";
        turmasDescricao.innerText =
            "Leitura organizada por turma com destaque visual para as aulas do professor logado.";
        return;
    }

    if (visualizacaoGestorPorProfessorAtiva()) {
        turmasEyebrow.innerText = "Visao administrativa";
        turmasTitulo.innerText = "Horario por professor";
        turmasDescricao.innerText =
            "Uma grade semanal separada para cada professor, com todas as turmas e disciplinas do recorte atual.";
        return;
    }

    turmasEyebrow.innerText = "Visao principal";
    turmasTitulo.innerText = "Grade por turma";
    turmasDescricao.innerText =
        "Resumo textual da grade organizada por turma para conferencia rapida.";
}

function aplicarModoPaginaHorario() {
    document.body.classList.toggle("horario-professor-mode", interfaceProfessorAtiva());

    const topbarContext = el("horarioTopbarContext");
    if (topbarContext) {
        topbarContext.innerText = interfaceProfessorAtiva() ? "Visao do professor" : "Gestao escolar";
    }

    const headerDescricao = el("horarioHeaderDescricao");
    if (headerDescricao) {
        headerDescricao.innerText = interfaceProfessorAtiva()
            ? "Consulte sua grade completa por turma, acompanhe o horario geral da escola e destaque rapidamente suas proprias aulas."
            : "Organize a grade por turma e acompanhe uma leitura complementar por professor para preparar os proximos modulos operacionais.";
    }

    const filtroDescricao = el("horarioFiltroDescricao");
    if (filtroDescricao) {
        filtroDescricao.innerText = interfaceProfessorAtiva()
            ? "Filtre por ano, turma e dia para comparar o horario geral, somente colegas ou apenas suas aulas."
            : "Aplique filtros e escolha se deseja revisar a grade por turma ou por professor.";
    }

    atualizarTitulosConsultaHorario();

    const builderGrid = el("horarioBuilderGrid");
    if (builderGrid) {
        builderGrid.hidden = interfaceProfessorAtiva();
    }

    const professorScope = el("horarioEscopoProfessorCard");
    if (professorScope) {
        professorScope.hidden = !interfaceProfessorAtiva();
    }

    const gestorScope = el("horarioVisualizacaoGestorCard");
    if (gestorScope) {
        gestorScope.hidden = !interfaceGestorAtiva();
    }

    const professorField = el("filtroHorarioProfessorField");
    if (professorField) {
        professorField.hidden = interfaceProfessorAtiva();
    }
}

function preencherContextoHorario() {
    preencherSelectAnos("filtroHorarioAnoLetivo", contextoHorario.anos_letivos, {
        incluirTodos: true,
    });
    preencherSelect("filtroHorarioTurmaId", contextoHorario.turmas, {
        incluirTodos: true,
    });
    preencherSelect("filtroHorarioDiaSemana", contextoHorario.dias_semana, {
        incluirTodos: true,
        valor: "valor",
        label: "label",
    });

    if (permiteEdicaoHorario()) {
        preencherSelectAnos("horarioAnoLetivo", contextoHorario.anos_letivos);
        preencherSelect("horarioTurmaId", contextoHorario.turmas, {
            placeholder: "Selecione a turma",
        });
        preencherSelect("filtroHorarioProfessorId", contextoHorario.professores, {
            incluirTodos: true,
            label: "label",
        });
    }

    const anoAtual = String(contextoHorario.ano_letivo_atual || "");
    if (anoAtual) {
        if (el("filtroHorarioAnoLetivo")) {
            el("filtroHorarioAnoLetivo").value = anoAtual;
        }
        if (el("horarioAnoLetivo")) {
            el("horarioAnoLetivo").value = anoAtual;
        }
    }
}

function atualizarResumoHorario() {
    const resultadoFiltrado = obterResultadoHorarioFiltrado();
    const gruposTurma = resultadoFiltrado.grupos_turma;
    const gruposProfessor = resultadoFiltrado.grupos_professor;

    el("horarioResumoRegistros").innerText = String(resultadoFiltrado.itens.length);
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
    if (professorId && !interfaceProfessorAtiva()) {
        const professor = (contextoHorario.professores || []).find(
            (item) => String(item.id) === professorId
        );
        if (professor?.nome) partes.push(professor.nome);
    }
    if (dia) {
        const diaInfo = obterDiaInfo(dia);
        if (diaInfo?.label) partes.push(diaInfo.label);
    }
    if (interfaceProfessorAtiva()) {
        const legendaEscopo = {
            geral: "Horario geral",
            colegas: "Somente colegas",
            minhas: "Ver meu horario",
        };
        partes.push(legendaEscopo[escopoProfessorHorario] || "Horario geral");
    } else {
        partes.push(
            visualizacaoGestorPorProfessorAtiva()
                ? "Visualizacao por professor"
                : "Visualizacao por turma"
        );
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
    if (!elemento || !permiteEdicaoHorario()) return;
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
    if (!elemento || !permiteEdicaoHorario()) return;
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

    if (!titulo || !meta || !tituloMatriz) return;

    if (!turma || ano <= 0) {
        titulo.innerText = "Selecione uma turma para abrir a matriz.";
        meta.innerText =
            "Os cards ao lado serao gerados a partir das atribuicoes e da carga horaria vinculada a turma.";
        tituloMatriz.innerText = "Matriz semanal";
        return;
    }

    titulo.innerText = `${turma.nome} - ${ano}`;
    meta.innerText = `${turma.turno || "Turno nao informado"} com montagem visual por arraste.`;
    tituloMatriz.innerText = `Matriz semanal da turma ${turma.nome}`;
}

function limparMatrizHorario() {
    estadoMatrizHorario = null;
    if (el("horarioMatrizWrap")) {
        el("horarioMatrizWrap").innerHTML =
            '<div class="horario-empty-state">Selecione uma turma para visualizar a matriz do horario.</div>';
    }
    if (el("horarioCardsDisponiveis")) {
        el("horarioCardsDisponiveis").innerHTML = "";
    }
    if (el("horarioPoolMeta")) {
        el("horarioPoolMeta").innerHTML = "";
    }
    if (el("horarioAlertas")) {
        el("horarioAlertas").hidden = true;
        el("horarioAlertas").innerHTML = "";
    }
    atualizarCabecalhoBuilder();
}

async function recarregarDadosHorarioCompleto() {
    if (permiteEdicaoHorario()) {
        await Promise.all([carregarMatrizHorario(), carregarRegistrosHorario()]);
        return;
    }
    await carregarRegistrosHorario();
}

async function excluirRegistroHorario(id, mensagem = "Registro removido com sucesso.") {
    if (!permiteEdicaoHorario()) return;
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
    if (!permiteEdicaoHorario()) return;
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
            ? `${grupo.turma_nome || "Turma nao informada"}`
            : `${grupo.professor_nome || "Professor nao informado"}`;
    info.appendChild(titulo);

    const subtitulo = document.createElement("p");
    subtitulo.innerText =
        modo === "turma"
            ? `${grupo.turno || "Turno nao informado"} - Ano ${grupo.ano_letivo || "-"}`
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

    if (modo === "turma") {
        table.innerHTML = permiteEdicaoHorario()
            ? "<thead><tr><th>Dia</th><th>Aula</th><th>Disciplina</th><th>Professor</th><th>Destaque</th><th>Acoes</th></tr></thead>"
            : "<thead><tr><th>Dia</th><th>Aula</th><th>Disciplina</th><th>Professor</th><th>Destaque</th></tr></thead>";
    } else {
        table.innerHTML = permiteEdicaoHorario()
            ? "<thead><tr><th>Dia</th><th>Aula</th><th>Turma</th><th>Disciplina</th><th>Acoes</th></tr></thead>"
            : "<thead><tr><th>Dia</th><th>Aula</th><th>Turma</th><th>Disciplina</th></tr></thead>";
    }

    const tbody = document.createElement("tbody");
    (grupo.itens || []).forEach((item) => {
        const tr = document.createElement("tr");
        if (modo === "turma" && itemEhDoProfessorLogado(item)) {
            tr.classList.add("horario-row-own");
        }

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

        if (modo === "turma") {
            const tdDestaque = document.createElement("td");
            if (itemEhDoProfessorLogado(item)) {
                const badge = document.createElement("span");
                badge.className = "horario-own-badge";
                badge.innerText = "Minhas aulas";
                tdDestaque.appendChild(badge);
            } else {
                tdDestaque.innerText = interfaceProfessorAtiva() ? "Colega" : "";
            }
            tr.appendChild(tdDestaque);
        }

        if (permiteEdicaoHorario()) {
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
        }

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    card.appendChild(wrap);
    return card;
}

function renderizarGradeTurmaSemanal(grupo) {
    const card = document.createElement("article");
    card.className = "horario-group-card horario-professor-grid-card";

    const header = document.createElement("div");
    header.className = "horario-group-header";

    const info = document.createElement("div");
    const titulo = document.createElement("h3");
    titulo.innerText = grupo.turma_nome || "Turma nao informada";
    info.appendChild(titulo);

    const subtitulo = document.createElement("p");
    subtitulo.innerText = `${grupo.turno || "Turno nao informado"} - Ano ${grupo.ano_letivo || "-"}`;
    info.appendChild(subtitulo);
    header.appendChild(info);

    const count = document.createElement("span");
    count.className = "horario-group-count";
    count.innerText = `${(grupo.itens || []).length} aula(s)`;
    header.appendChild(count);
    card.appendChild(header);

    if (permiteEdicaoHorario()) {
        const acoes = document.createElement("div");
        acoes.className = "horario-inline-actions";
        acoes.appendChild(
            criarBotaoAcao("Abrir matriz", () => abrirTurmaNaMatriz(grupo))
        );
        card.appendChild(acoes);
    }

    const wrap = document.createElement("div");
    wrap.className = "horario-professor-grid-wrap";

    const table = document.createElement("table");
    table.className = "horario-professor-grid";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");

    const thAula = document.createElement("th");
    thAula.innerText = "Aula";
    headRow.appendChild(thAula);

    (contextoHorario.dias_semana || []).forEach((dia) => {
        const th = document.createElement("th");
        th.innerText = dia.label || dia.valor || "";
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const mapa = new Map();
    (grupo.itens || []).forEach((item) => {
        mapa.set(`${item.dia_semana}:${item.aula_numero}`, item);
    });

    const tbody = document.createElement("tbody");
    obterFaixasGrupoTurma(grupo).forEach((faixaInfo) => {
        if (String(faixaInfo?.tipo || "").trim().toUpperCase() === TIPO_GRADE_INTERVALO) {
            const trIntervalo = document.createElement("tr");
            trIntervalo.className = "weekly-turno-row";

            const thIntervalo = document.createElement("th");
            thIntervalo.scope = "colgroup";
            thIntervalo.colSpan = (contextoHorario.dias_semana || []).length + 1;
            thIntervalo.innerText = String(faixaInfo.label || faixaInfo.nome || "Intervalo");
            trIntervalo.appendChild(thIntervalo);
            tbody.appendChild(trIntervalo);
            return;
        }

        const aulaNumero = Number(faixaInfo?.aula_numero || 0);
        const tr = document.createElement("tr");

        const thLinha = document.createElement("th");
        thLinha.innerText = String(faixaInfo.label || `${aulaNumero}a aula`);
        tr.appendChild(thLinha);

        (contextoHorario.dias_semana || []).forEach((dia) => {
            const td = document.createElement("td");
            const item = mapa.get(`${dia.valor}:${aulaNumero}`) || null;

            if (!item) {
                td.className = "is-empty";
                td.innerHTML = "<span>&nbsp;</span>";
            } else {
                td.innerText = descricaoCelulaHorarioProfessor(item);
                td.classList.add(
                    itemEhDoProfessorLogado(item)
                        ? "is-own"
                        : "is-colleague"
                );
            }

            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    card.appendChild(wrap);
    return card;
}

function obterDiasGradeProfessor() {
    const diaSelecionado = String(el("filtroHorarioDiaSemana")?.value || "").trim().toUpperCase();
    if (diaSelecionado) {
        const diaInfo = obterDiaInfo(diaSelecionado);
        return diaInfo ? [diaInfo] : [];
    }
    return Array.isArray(contextoHorario.dias_semana) ? contextoHorario.dias_semana : [];
}

function obterFaixasGradeProfessor(itens) {
    const gradeConfigurada = itensGradeHorarioAtivos();
    if (gradeConfigurada.length > 0) {
        return gradeConfigurada;
    }

    const faixas = new Map();
    (itens || []).forEach((item) => {
        const faixaGlobal = Number(item.faixa_global || item.aula_numero || 0);
        if (faixaGlobal <= 0) return;
        if (!faixas.has(faixaGlobal)) {
            faixas.set(faixaGlobal, {
                tipo: TIPO_GRADE_AULA,
                faixa_global: faixaGlobal,
                aula_numero: Number(item.aula_numero || 0),
                label: String(item.aula_label || labelAulaHorario(item) || "").trim() || `${item.aula_numero}a aula`,
            });
        }
    });
    return Array.from(faixas.values()).sort((atual, proxima) => {
        if (atual.faixa_global !== proxima.faixa_global) {
            return atual.faixa_global - proxima.faixa_global;
        }
        return atual.aula_numero - proxima.aula_numero;
    });
}

function criarConteudoCelulaGradeProfessor(item) {
    const conteudo = document.createElement("div");
    conteudo.className = "horario-professor-cell";

    const disciplina = document.createElement("strong");
    disciplina.className = "horario-professor-cell-disciplina";
    disciplina.innerText = String(item?.disciplina_nome || "Disciplina nao informada");
    conteudo.appendChild(disciplina);

    const turma = document.createElement("span");
    turma.className = "horario-professor-cell-turma";
    turma.innerText = String(item?.turma_nome || "").trim()
        ? `Turma ${item.turma_nome}`
        : "Turma nao informada";
    conteudo.appendChild(turma);

    return conteudo;
}

function renderizarGradeProfessorSemanal(grupo, { tituloCard = "", subtituloCard = "" } = {}) {
    const card = document.createElement("article");
    card.className = "horario-group-card horario-professor-grid-card";

    const header = document.createElement("div");
    header.className = "horario-group-header";

    const info = document.createElement("div");
    const titulo = document.createElement("h3");
    titulo.innerText = tituloCard || grupo.professor_nome || "Professor nao informado";
    info.appendChild(titulo);

    const anos = Array.from(
        new Set(
            (grupo.itens || [])
                .map((item) => Number(item.ano_letivo || 0))
                .filter((ano) => ano > 0)
        )
    ).sort((atual, proximo) => atual - proximo);

    const subtitulo = document.createElement("p");
    if (subtituloCard) {
        subtitulo.innerText = subtituloCard;
    } else {
        const email = String(grupo.professor_email || "").trim();
        subtitulo.innerText = anos.length === 1
            ? `${email || "Sem e-mail"} - Ano ${anos[0]}`
            : email || "Grade consolidada por dia, disciplina e turma.";
    }
    info.appendChild(subtitulo);
    header.appendChild(info);

    const count = document.createElement("span");
    count.className = "horario-group-count";
    count.innerText = `${(grupo.itens || []).length} aula(s)`;
    header.appendChild(count);
    card.appendChild(header);

    const dias = obterDiasGradeProfessor();
    const faixas = obterFaixasGradeProfessor(grupo.itens || []);
    if (dias.length === 0 || faixas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "horario-empty-state";
        vazio.innerText = "Nenhuma aula encontrada para montar essa grade.";
        card.appendChild(vazio);
        return card;
    }

    const mapa = new Map();
    (grupo.itens || []).forEach((item) => {
        mapa.set(
            `${String(item.dia_semana || "").toUpperCase()}:${Number(item.aula_numero || item.faixa_global || 0)}`,
            item
        );
    });

    const wrap = document.createElement("div");
    wrap.className = "horario-professor-grid-wrap";

    const table = document.createElement("table");
    table.className = "horario-professor-grid";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");

    const thHorario = document.createElement("th");
    thHorario.innerText = "Horario";
    headRow.appendChild(thHorario);

    dias.forEach((dia) => {
        const th = document.createElement("th");
        th.innerText = dia.label || dia.valor || "";
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    faixas.forEach((faixa) => {
        if (String(faixa?.tipo || "").trim().toUpperCase() === TIPO_GRADE_INTERVALO) {
            const trIntervalo = document.createElement("tr");
            trIntervalo.className = "weekly-turno-row";

            const thIntervalo = document.createElement("th");
            thIntervalo.scope = "colgroup";
            thIntervalo.colSpan = dias.length + 1;
            thIntervalo.innerText = String(faixa.label || faixa.nome || "Intervalo");
            trIntervalo.appendChild(thIntervalo);
            tbody.appendChild(trIntervalo);
            return;
        }

        const tr = document.createElement("tr");
        const aulaNumero = Number(faixa.aula_numero || faixa.faixa_global || 0);

        const thLinha = document.createElement("th");
        thLinha.innerText = faixa.label || `${aulaNumero}a aula`;
        tr.appendChild(thLinha);

        dias.forEach((dia) => {
            const td = document.createElement("td");
            const item = mapa.get(`${dia.valor}:${aulaNumero}`) || null;

            if (!item) {
                td.className = "is-empty";
                td.innerHTML = "<span>&nbsp;</span>";
            } else {
                td.classList.add(
                    itemEhDoProfessorLogado(item)
                        ? "is-own"
                        : "is-colleague"
                );
                td.appendChild(criarConteudoCelulaGradeProfessor(item));
            }

            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    card.appendChild(wrap);
    return card;
}

function renderizarMeuHorarioProfessor(itens) {
    return renderizarGradeProfessorSemanal(
        {
            professor_id: obterProfessorLogadoId(),
            professor_nome: "Meu horario semanal",
            professor_email: "",
            itens: itens || [],
        },
        {
            tituloCard: "Meu horario semanal",
            subtituloCard: "Grade consolidada por dia, disciplina e turma.",
        }
    );
}

function renderizarAgrupamentosHorario() {
    const listaTurmas = el("horarioListaTurmas");
    const resultadoFiltrado = obterResultadoHorarioFiltrado();
    listaTurmas.innerHTML = "";
    atualizarTitulosConsultaHorario();

    if (interfaceProfessorAtiva() && escopoProfessorHorario === "minhas") {
        if (resultadoFiltrado.itens.length === 0) {
            const vazio = document.createElement("p");
            vazio.className = "horario-empty-state";
            vazio.innerText = "Nenhuma aula encontrada para os filtros selecionados.";
            listaTurmas.appendChild(vazio);
        } else {
            listaTurmas.appendChild(renderizarMeuHorarioProfessor(resultadoFiltrado.itens));
        }
        return;
    }

    if (visualizacaoGestorPorProfessorAtiva()) {
        if (resultadoFiltrado.grupos_professor.length === 0) {
            const vazio = document.createElement("p");
            vazio.className = "horario-empty-state";
            vazio.innerText = "Nenhum professor com horario no recorte atual.";
            listaTurmas.appendChild(vazio);
        } else {
            resultadoFiltrado.grupos_professor.forEach((grupo) => {
                listaTurmas.appendChild(renderizarGradeProfessorSemanal(grupo));
            });
        }
        return;
    }

    if (resultadoFiltrado.grupos_turma.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "horario-empty-state";
        vazio.innerText = "Nenhum horario encontrado para os filtros selecionados.";
        listaTurmas.appendChild(vazio);
    } else {
        resultadoFiltrado.grupos_turma.forEach((grupo) => {
            listaTurmas.appendChild(
                renderizarGradeTurmaSemanal(grupo)
            );
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
    if (professorId && !interfaceProfessorAtiva()) params.set("professor_id", professorId);
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
    if (!container) return;
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
    if (!alvo) return;
    alvo.innerHTML = "";

    const totalDisponiveis = Array.isArray(cardsDisponiveis) ? cardsDisponiveis.length : 0;
    const totalPlanejado = (cardsResumo || []).reduce(
        (soma, item) => soma + Number(item.quantidade_total || 0),
        0
    );

    const resumo = document.createElement("p");
    resumo.className = "horario-pool-summary";
    resumo.innerText = `${totalDisponiveis} card(s) disponivel(is) de ${totalPlanejado} aula(s) planejada(s).`;
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
    if (!payload || !diaSemana || !aulaNumero || !permiteEdicaoHorario()) return;

    if (payload.source === "scheduled") {
        if (
            String(payload.dia_semana || "") === String(diaSemana) &&
            Number(payload.aula_numero || 0) === Number(aulaNumero)
        ) {
            return;
        }
        if (celulaOcupada) {
            setMensagemHorario("Esse campo ja possui uma aula. Remova ou reposicione a atual antes de continuar.", true);
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
            setMensagemHorario(err.message || "Nao foi possivel reposicionar a aula.", true);
        }
        return;
    }

    if (payload.source === "available") {
        if (celulaOcupada) {
            setMensagemHorario("Esse campo ja possui uma aula. Escolha outro horario vazio.", true);
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
            setMensagemHorario(err.message || "Nao foi possivel criar a aula.", true);
        }
    }
}

function criarCardVisualHorario(payload, { agendado = false } = {}) {
    const card = document.createElement("article");
    card.className = `horario-card-item${agendado ? " is-scheduled" : ""}`;
    if (itemEhDoProfessorLogado(payload)) {
        card.classList.add("is-own");
    }

    const topo = document.createElement("div");
    topo.className = "horario-card-top";

    const titulo = document.createElement("strong");
    titulo.innerText = payload.disciplina_nome || "Disciplina";
    topo.appendChild(titulo);

    const badge = document.createElement("span");
    badge.className = "horario-card-badge";
    badge.innerText = agendado ? "Alocada" : "Disponivel";
    topo.appendChild(badge);
    card.appendChild(topo);

    const professor = document.createElement("p");
    professor.className = "horario-card-professor";
    professor.innerText = payload.professor_nome || "Professor nao informado";
    card.appendChild(professor);

    const meta = document.createElement("small");
    meta.className = "horario-card-meta";
    meta.innerText = agendado
        ? `${payload.dia_semana_nome || payload.dia_semana || ""} - ${labelAulaHorario(payload)}`
        : `Card ${payload.indice_disponivel || 1} de ${payload.quantidade_total || 1}`;
    card.appendChild(meta);

    if (itemEhDoProfessorLogado(payload)) {
        const destaque = document.createElement("span");
        destaque.className = "horario-own-badge";
        destaque.innerText = "Minhas aulas";
        card.appendChild(destaque);
    }

    if (agendado && permiteEdicaoHorario()) {
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
    if (!container) return;
    container.innerHTML = "";

    if (!Array.isArray(cardsDisponiveis) || cardsDisponiveis.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "horario-empty-state";
        vazio.innerText = "Nenhum card disponivel para esta turma. Verifique a carga horaria ou as aulas ja alocadas.";
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
    if (!wrap) return;
    wrap.innerHTML = "";

    if (!estadoMatrizHorario || !estadoMatrizHorario.turma) {
        wrap.innerHTML =
            '<div class="horario-empty-state">Selecione uma turma para visualizar a matriz do horario.</div>';
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
        if (String(faixaInfo?.tipo || "").trim().toUpperCase() === TIPO_GRADE_INTERVALO) {
            const trIntervalo = document.createElement("tr");
            trIntervalo.className = "weekly-turno-row";

            const thIntervalo = document.createElement("th");
            thIntervalo.innerText = String(faixaInfo.label || faixaInfo.nome || "Intervalo");
            trIntervalo.appendChild(thIntervalo);

            const tdIntervalo = document.createElement("td");
            tdIntervalo.colSpan = (estadoMatrizHorario.dias_semana || []).length;
            tdIntervalo.innerText = [
                String(faixaInfo.horario_inicio || "").trim(),
                String(faixaInfo.horario_fim || "").trim()
            ].filter(Boolean).join(" - ") || "Pausa da grade";
            trIntervalo.appendChild(tdIntervalo);
            tbody.appendChild(trIntervalo);
            return;
        }

        const aulaNumero = Number(faixaInfo.aula_numero || 0);
        const aceitaLancamento = faixaInfo?.aceita_lancamento !== false;
        const tr = document.createElement("tr");
        if (faixaInfo?.fora_janela_turma) {
            tr.classList.add("is-recovery-row");
        }
        const th = document.createElement("th");
        th.innerText = faixaInfo.label || `${aulaNumero}a aula`;
        tr.appendChild(th);

        (estadoMatrizHorario.dias_semana || []).forEach((dia) => {
            const td = document.createElement("td");
            td.className = "horario-slot";
            if (!aceitaLancamento) {
                td.classList.add("is-locked");
            }
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
                hint.innerText = aceitaLancamento ? "Solte aqui" : "Fora da janela";
                td.appendChild(hint);
            }

            if (aceitaLancamento || registro) {
                configurarDropTarget(td, async (payload) => {
                    await processarDropNaCelula(payload, dia.valor, aulaNumero, Boolean(registro));
                });
            }
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    tabela.appendChild(tbody);
    wrap.appendChild(tabela);
}

async function carregarMatrizHorario() {
    if (!permiteEdicaoHorario()) return;

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
        setMensagemHorario(err.message || "Nao foi possivel carregar a matriz da turma.", true);
    }
}

function configurarDropPool() {
    const pool = el("horarioDropPool");
    if (!pool) return;
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
        document.querySelector('input[name="horarioEscopoProfessor"][value="geral"]')?.click();
        document.querySelector('input[name="horarioVisualizacaoGestor"][value="turmas"]')?.click();
        escopoProfessorHorario = "geral";
        modoVisualizacaoGestorHorario = "turmas";
        if (contextoHorario.ano_letivo_atual) {
            el("filtroHorarioAnoLetivo").value = String(contextoHorario.ano_letivo_atual);
        }
        await carregarRegistrosHorario();
    });

    document.querySelectorAll('input[name="horarioEscopoProfessor"]').forEach((input) => {
        input.addEventListener("change", async (event) => {
            escopoProfessorHorario = String(event.target?.value || "geral");
            atualizarResumoHorario();
            renderizarAgrupamentosHorario();
        });
    });

    document.querySelectorAll('input[name="horarioVisualizacaoGestor"]').forEach((input) => {
        input.addEventListener("change", (event) => {
            modoVisualizacaoGestorHorario = String(event.target?.value || "turmas");
            atualizarResumoHorario();
            renderizarAgrupamentosHorario();
        });
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
    aplicarModoPaginaHorario();
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
        if (permiteEdicaoHorario()) {
            await Promise.all([carregarMatrizHorario(), carregarRegistrosHorario()]);
            return;
        }
        await carregarRegistrosHorario();
    } catch (_err) {
        encerrarSessao();
    }
}

window.addEventListener("DOMContentLoaded", initHorarioEscolar);
