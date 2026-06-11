const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    encerrarSessao,
    usuarioPodeGerirImpressoes,
} = window.AppAuth;
const { fetchComAuth, obterMensagemErroResposta, lerJsonResposta } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);

let pdfDoc = null;
let folhaAtual = 1;
let renderTokenAtual = 0;
let resizeTimer = null;
let previewScrollRaf = null;
let previewAbortController = null;
let previewLoadSeq = 0;
let previewEmCarregamento = false;
let envioEmAndamento = false;
let filaPollingTimer = null;
let usuarioAtual = null;
let professoresImpressao = [];
let turmasImpressao = [];
let tagsImpressaoDisponiveis = [];
let arquivoSelecionadoAtual = null;
let jobHistoricoSelecionadoAtual = null;
let reusoHistoricoEmCarregamento = false;
let resolverModalAlertaConsumoAtual = null;
let statusImpressaoAtual = { sem_papel: false, mensagem: "", atualizado_em: "" };
let modalSemPapelExibido = false;
const QUALIDADE_MAX_DPR = 1.4;
const FOLHA_PADDING = 8;
const FOLHA_GAP = 6;
const LABEL_PREVIEW_RESERVA = 38;
const RESERVA_BORDA_PREVIEW = 24;
const BREAKPOINT_MOBILE_PREVIEW = 980;
const FILA_POLLING_MS = 6000;
const LIMITE_ALERTA_IMPRESSAO_PAGINAS = 30;
const LIMIAR_RE_RENDER_PREVIEW_MOBILE_PX = 24;
const EXTENSOES_SUPORTADAS = new Set(["pdf", "doc", "docx", "png", "jpg", "jpeg"]);
const IDS_LISTAS_JOBS_IMPRESSAO = ["lista-jobs", "lista-jobs-etapa-arquivo"];
const IDS_ESPELHOS_COTA_IMPRESSAO = ["cotaPainelEspelho", "cotaPainelEtapaArquivo"];
const IDS_TITULOS_COTA_IMPRESSAO = ["tituloCota", "tituloCotaEtapaArquivo"];
const IDS_TITULOS_JOBS_IMPRESSAO = ["tituloJobs", "tituloJobsEtapaArquivo"];
const STATUS_JOB_LABEL = {
    PENDENTE: "Na fila",
    IMPRIMINDO: "Imprimindo",
    CONCLUIDO: "Concluído",
    FINALIZADO: "Concluído",
    ERRO: "Erro",
    CANCELADO: "Cancelado"
};

const TAMANHO_FOLHA = {
    retrato: { largura: 794, altura: 1123 },
    paisagem: { largura: 1123, altura: 794 }
};

let ultimaGeometriaPreview = {
    larguraJanela: window.innerWidth || 0,
    alturaJanela: window.innerHeight || 0,
    mobile: (window.innerWidth || 0) <= BREAKPOINT_MOBILE_PREVIEW,
};

function impressaoBloqueadaSemPapel() {
    return Boolean(statusImpressaoAtual?.sem_papel);
}

function obterMensagemSemPapel() {
    const mensagem = String(statusImpressaoAtual?.mensagem || "").trim();
    return mensagem || "Impressao indisponivel no momento: a escola esta sem papel.";
}

function aplicarBloqueioSemPapelNosCampos() {
    const bloqueado = impressaoBloqueadaSemPapel();
    const ids = [
        "arquivo",
        "arquivoDropzone",
        "professorSolicitante",
        "turmaImpressao",
        "copias",
        "intervaloPaginas",
        "paginasPorFolha",
        "orientacao",
        "duplex",
    ];

    ids.forEach((id) => {
        const elemento = el(id);
        if (elemento) {
            elemento.disabled = bloqueado;
        }
    });

    document.querySelectorAll("#tagsImpressao input[type='checkbox']").forEach((input) => {
        input.disabled = bloqueado;
    });

    atualizarEstadoEnvio(false, bloqueado ? obterMensagemSemPapel() : "");
}

function aplicarStatusImpressaoNaTela({ mostrarModal = false } = {}) {
    const bloqueado = impressaoBloqueadaSemPapel();
    const mensagem = obterMensagemSemPapel();
    const banner = el("bannerSemPapelImpressao");
    const textoBanner = el("textoBannerSemPapelImpressao");
    const modal = el("modalSemPapelImpressao");
    const textoModal = el("textoSemPapelImpressao");

    if (banner) {
        banner.hidden = !bloqueado;
    }
    if (textoBanner) {
        textoBanner.innerText = mensagem;
    }
    if (textoModal) {
        textoModal.innerText = mensagem;
    }

    aplicarBloqueioSemPapelNosCampos();

    if (bloqueado) {
        el("msg").innerText = mensagem;
        if (mostrarModal && modal && !modalSemPapelExibido) {
            modal.hidden = false;
            document.body.classList.add("print-alert-modal-open");
            modalSemPapelExibido = true;
            window.requestAnimationFrame(() => el("painelSemPapelImpressao")?.focus());
        }
        if (!window.PrintingUI?.state?.getState?.()?.submit?.submitted) {
            limparCardJobRecente();
        }
        return [];
    }

    if (modal) {
        modal.hidden = true;
    }
    document.body.classList.remove("print-alert-modal-open");
    if (el("msg")?.innerText === mensagem) {
        el("msg").innerText = "";
    }
    modalSemPapelExibido = false;
}

function usuarioEhAdmin() {
    if (!usuarioAtual) {
        return false;
    }

    if (Boolean(usuarioAtual.eh_admin)) {
        return true;
    }

    const cargo = String(usuarioAtual.cargo || "").trim().toUpperCase();
    if (cargo === "ADMIN") {
        return true;
    }

    return String(usuarioAtual.perfil || "").trim().toLowerCase() === "admin";
}

function usuarioEhGestor() {
    if (!usuarioAtual) {
        return false;
    }

    const cargo = String(usuarioAtual.cargo || "").trim().toUpperCase();
    if (cargo === "ADMIN" || cargo === "COORDENADOR") {
        return true;
    }

    const perfil = String(usuarioAtual.perfil || "").trim().toLowerCase();
    return perfil === "admin" || perfil === "coordenador";
}

function usuarioPodeSelecionarProfessorImpressao() {
    return Boolean(usuarioAtual) && usuarioPodeGerirImpressoes(usuarioAtual);
}

function obterProfessorSolicitanteSelecionadoId() {
    return Number(el("professorSolicitante")?.value || 0);
}

function obterProfessorSelecionado() {
    const professorId = obterProfessorSolicitanteSelecionadoId();
    return professoresImpressao.find((professor) => Number(professor.id) === professorId) || null;
}

function professorSolicitanteEhObrigatorio() {
    return false;
}

function professorSolicitantePendente() {
    return professorSolicitanteEhObrigatorio() && obterProfessorSolicitanteSelecionadoId() <= 0;
}

function obterMensagemSelecaoProfessorImpressao() {
    return "Selecione um professor para consultar a cota, o historico e reaproveitar arquivos em nome dele.";
}

function obterListasJobsImpressao() {
    return IDS_LISTAS_JOBS_IMPRESSAO
        .map((id) => el(id))
        .filter(Boolean);
}

function atualizarEspelhosCotaImpressao(texto) {
    IDS_ESPELHOS_COTA_IMPRESSAO.forEach((id) => {
        definirTexto(id, texto);
    });
}

function montarUrlConsultaImpressao(urlBase) {
    const professorId = obterProfessorSolicitanteSelecionadoId();
    if (!(usuarioPodeSelecionarProfessorImpressao() && professorId > 0)) {
        return urlBase;
    }

    const params = new URLSearchParams({ professor_id: String(professorId) });
    return `${urlBase}?${params.toString()}`;
}

function atualizarTitulosContextoImpressao() {
    const contexto = el("contextoProfessorImpressao");

    if (!usuarioPodeSelecionarProfessorImpressao()) {
        IDS_TITULOS_COTA_IMPRESSAO.forEach((id) => definirTexto(id, "Sua cota"));
        IDS_TITULOS_JOBS_IMPRESSAO.forEach((id) => definirTexto(id, "Seus pedidos"));
        if (contexto) {
            contexto.innerText = "";
        }
        return;
    }

    const professor = obterProfessorSelecionado();
    if (!professor) {
        IDS_TITULOS_COTA_IMPRESSAO.forEach((id) => definirTexto(id, "Sua cota"));
        IDS_TITULOS_JOBS_IMPRESSAO.forEach((id) => definirTexto(id, "Seus pedidos"));
        if (contexto) {
            contexto.innerText = obterMensagemSelecaoProfessorImpressao();
        }
        return;
    }

    IDS_TITULOS_COTA_IMPRESSAO.forEach((id) => definirTexto(id, `Cota de ${professor.nome}`));
    IDS_TITULOS_JOBS_IMPRESSAO.forEach((id) => definirTexto(id, `Pedidos de ${professor.nome}`));
    if (contexto) {
        contexto.innerText = `A impressao sera contabilizada para ${professor.nome}.`;
    }
}

function atualizarTopbarUsuario() {
    const topbarUsuario = el("printTopbarUsuario");
    if (!topbarUsuario) {
        return;
    }

    if (!usuarioAtual) {
        topbarUsuario.innerText = "Usuario nao identificado";
        return;
    }

    const nome = String(
        usuarioAtual.nome
        || usuarioAtual.username
        || usuarioAtual.email
        || "Usuario"
    ).trim();

    const perfil = String(
        usuarioAtual.perfil
        || usuarioAtual.cargo
        || (usuarioAtual.eh_admin ? "Admin" : "Professor")
        || ""
    ).trim();

    topbarUsuario.innerText = perfil ? `${nome} • ${perfil}` : nome;
}

function renderFilaVazia(texto) {
    obterListasJobsImpressao().forEach((ul) => {
        ul.innerHTML = "";
        const li = document.createElement("li");
        li.classList.add("print-job-empty");
        li.innerText = texto;
        ul.appendChild(li);
    });
}

async function carregarUsuario() {
    const res = await fetchComAuth("/me", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar o usuário.");
    }

    usuarioAtual = await lerJsonResposta(res, "Não foi possível carregar o usuário.");
    atualizarTitulosContextoImpressao();
}

async function carregarStatusImpressao(mostrarModal = false) {
    const res = await fetchComAuth("/impressao/status", { headers });
    if (!res.ok) {
        throw new Error("Nao foi possivel verificar o status da impressora.");
    }

    statusImpressaoAtual = await lerJsonResposta(
        res,
        "Nao foi possivel verificar o status da impressora."
    );
    aplicarStatusImpressaoNaTela({ mostrarModal });
}

async function carregarProfessoresImpressaoAdmin() {
    const painel = el("painelProfessorEtapaArquivo");
    const grupo = el("grupoProfessorSolicitante");
    const select = el("professorSolicitante");

    if (!grupo || !select) {
        return;
    }

    if (!usuarioPodeSelecionarProfessorImpressao()) {
        if (painel) {
            painel.hidden = true;
        }
        grupo.style.display = "none";
        professoresImpressao = [];
        select.dataset.required = "false";
        select.dataset.previousProfessorId = "0";
        select.innerHTML = "";
        atualizarTitulosContextoImpressao();
        window.PrintingUI?.ui?.syncFromLegacyDom?.();
        return;
    }

    if (painel) {
        painel.hidden = false;
    }
    grupo.style.display = "block";
    select.dataset.required = "false";
    const res = await fetchComAuth("/agendamento/professores", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar os professores para impressão.");
    }

    professoresImpressao = await lerJsonResposta(
        res,
        "Não foi possível carregar os professores para impressão."
    );
    select.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.innerText = Array.isArray(professoresImpressao) && professoresImpressao.length > 0
        ? "Selecione um professor"
        : "Nenhum professor disponivel";
    placeholder.selected = true;
    select.appendChild(placeholder);

    if (!Array.isArray(professoresImpressao) || professoresImpressao.length === 0) {
        select.disabled = true;
        select.dataset.previousProfessorId = "0";
        atualizarTitulosContextoImpressao();
        window.PrintingUI?.ui?.syncFromLegacyDom?.();
        return;
    }

    professoresImpressao.forEach((professor) => {
        const option = document.createElement("option");
        option.value = String(professor.id);
        option.innerText = `${professor.nome}`;
        select.appendChild(option);
    });
    select.disabled = false;
    select.dataset.previousProfessorId = String(obterProfessorSolicitanteSelecionadoId() || 0);
    atualizarTitulosContextoImpressao();
    window.PrintingUI?.ui?.syncFromLegacyDom?.();
}

function obterTurmaImpressaoSelecionadaId() {
    return Number(el("turmaImpressao")?.value || 0);
}

function obterTurmaImpressaoSelecionada() {
    const turmaId = obterTurmaImpressaoSelecionadaId();
    return turmasImpressao.find((turma) => Number(turma.id) === turmaId) || null;
}

function obterQuantidadeCopiasTurma(turma) {
    const quantidade = Number(turma?.quantidade_estudantes || 0);
    if (!Number.isFinite(quantidade) || quantidade <= 0) {
        return 0;
    }
    return Math.floor(quantidade);
}

function atualizarResumoTurmaImpressao() {
    const resumo = el("resumoTurmaImpressao");
    if (!resumo) {
        return;
    }

    const turma = obterTurmaImpressaoSelecionada();
    if (!turma) {
        resumo.innerText = "Selecione uma turma para preencher as cópias automaticamente.";
        return;
    }

    const quantidade = obterQuantidadeCopiasTurma(turma);
    if (quantidade <= 0) {
        resumo.innerText = `${turma.nome} está sem quantidade de estudantes cadastrada. Ajuste as cópias manualmente.`;
        return;
    }

    const copiasAtuais = Number(el("copias")?.value || 0);
    if (copiasAtuais === quantidade) {
        resumo.innerText = `${turma.nome} possui ${quantidade} estudante(s). Serão feitas ${quantidade} cópia(s).`;
        return;
    }

    if (copiasAtuais > 0) {
        resumo.innerText = `${turma.nome} possui ${quantidade} estudante(s). Cópias ajustadas manualmente para ${copiasAtuais}.`;
        return;
    }

    resumo.innerText = `${turma.nome} possui ${quantidade} estudante(s).`;
}

function aplicarTurmaImpressaoSelecionada() {
    const turma = obterTurmaImpressaoSelecionada();
    const inputCopias = el("copias");
    const quantidade = obterQuantidadeCopiasTurma(turma);

    if (inputCopias && quantidade > 0) {
        inputCopias.value = String(quantidade);
    }

    atualizarResumoTurmaImpressao();
    calcularConsumo();
}

async function carregarTurmasImpressao() {
    const select = el("turmaImpressao");
    const resumo = el("resumoTurmaImpressao");
    if (!select) {
        return;
    }

    select.disabled = true;
    select.innerHTML = "";
    turmasImpressao = [];

    const optionCarregando = document.createElement("option");
    optionCarregando.value = "";
    optionCarregando.innerText = "Carregando turmas...";
    select.appendChild(optionCarregando);
    if (resumo) {
        resumo.innerText = "Carregando turmas cadastradas...";
    }

    const res = await fetchComAuth("/impressao/turmas", { headers });
    if (!res.ok) {
        throw new Error("Não foi possível carregar as turmas para impressão.");
    }

    const data = await lerJsonResposta(res, "Não foi possível carregar as turmas para impressão.");
    turmasImpressao = Array.isArray(data) ? data : [];

    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.innerText = turmasImpressao.length > 0
        ? "Selecione uma turma"
        : "Nenhuma turma ativa cadastrada";
    placeholder.selected = true;
    select.appendChild(placeholder);

    turmasImpressao.forEach((turma) => {
        const option = document.createElement("option");
        const quantidade = obterQuantidadeCopiasTurma(turma);
        option.value = String(turma.id);
        option.innerText = quantidade > 0
            ? `${turma.nome} (${quantidade} estudante(s))`
            : `${turma.nome} (sem quantidade)`;
        select.appendChild(option);
    });

    select.disabled = turmasImpressao.length === 0;
    if (turmasImpressao.length === 0 && resumo) {
        resumo.innerText = "Nenhuma turma ativa cadastrada para preenchimento automático.";
        return;
    }

    atualizarResumoTurmaImpressao();
}

function obterTagsImpressaoSelecionadas() {
    return Array.from(document.querySelectorAll("#tagsImpressao input[type='checkbox']:checked"))
        .map((input) => String(input.value || "").trim())
        .filter(Boolean);
}

function atualizarContadorTagsImpressao() {
    const contador = el("contadorTagsImpressao");
    if (!contador) {
        return;
    }
    const total = obterTagsImpressaoSelecionadas().length;
    contador.innerText = `${total} tag(s)`;
}

function aplicarTagsImpressaoSelecionadas(tags = []) {
    const selecionadas = new Set(
        (Array.isArray(tags) ? tags : [])
            .map((item) => String(item || "").trim().toLowerCase())
            .filter(Boolean)
    );

    document.querySelectorAll("#tagsImpressao input[type='checkbox']").forEach((input) => {
        input.checked = selecionadas.has(String(input.value || "").trim().toLowerCase());
    });
    atualizarContadorTagsImpressao();
}

function renderTagsImpressao() {
    const container = el("tagsImpressao");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (!Array.isArray(tagsImpressaoDisponiveis) || tagsImpressaoDisponiveis.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "print-file-hint";
        vazio.innerText = "Nenhuma tag cadastrada para impressao.";
        container.appendChild(vazio);
        atualizarContadorTagsImpressao();
        return;
    }

    tagsImpressaoDisponiveis.forEach((tag) => {
        const valor = String(tag?.id || tag?.label || "").trim();
        if (!valor) {
            return;
        }

        const label = document.createElement("label");
        label.className = "print-tag-chip";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = valor;

        const texto = document.createElement("span");
        texto.innerText = String(tag?.label || valor);

        label.appendChild(input);
        label.appendChild(texto);
        container.appendChild(label);
    });

    atualizarContadorTagsImpressao();
    aplicarBloqueioSemPapelNosCampos();
}

async function carregarTagsImpressao() {
    const res = await fetchComAuth("/impressao/tags", { headers });
    if (!res.ok) {
        throw new Error("NÃ£o foi possÃ­vel carregar as tags de impressÃ£o.");
    }

    const data = await lerJsonResposta(res, "NÃ£o foi possÃ­vel carregar as tags de impressÃ£o.");
    tagsImpressaoDisponiveis = Array.isArray(data) ? data : [];
    renderTagsImpressao();
}

function obterExtensaoArquivo(nomeArquivo) {
    if (!nomeArquivo || typeof nomeArquivo !== "string") {
        return "";
    }
    const indicePonto = nomeArquivo.lastIndexOf(".");
    if (indicePonto < 0) {
        return "";
    }
    return nomeArquivo.slice(indicePonto + 1).toLowerCase();
}

function obterArquivoSelecionado() {
    return arquivoSelecionadoAtual || el("arquivo")?.files?.[0] || null;
}

function atualizarEstadoArquivoSelecionado() {
    const dropzone = el("arquivoDropzone");
    const nomeArquivo = el("arquivoSelecionadoNome");
    const arquivo = obterArquivoSelecionado();

    if (dropzone) {
        dropzone.classList.toggle("has-file", Boolean(arquivo));
    }

    if (nomeArquivo) {
        nomeArquivo.innerText = arquivo
            ? (
                jobHistoricoSelecionadoAtual
                    ? `Histórico: ${arquivo.name}`
                    : `Selecionado: ${arquivo.name}`
            )
            : "Nenhum arquivo selecionado.";
    }
}

function sincronizarInputArquivo(file) {
    const input = el("arquivo");
    if (!input) {
        return;
    }

    if (!file) {
        input.value = "";
        return;
    }

    try {
        if (typeof DataTransfer === "function") {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            input.files = transfer.files;
        }
    } catch (_err) {
        // Alguns navegadores não permitem atribuir FileList manualmente.
    }
}

function obterExtensaoPorMime(tipoMime) {
    const tipo = String(tipoMime || "").trim().toLowerCase();
    if (!tipo) {
        return "";
    }
    if (tipo === "application/pdf") {
        return "pdf";
    }
    if (tipo === "image/png") {
        return "png";
    }
    if (tipo === "image/jpeg") {
        return "jpg";
    }
    if (
        tipo === "application/msword"
        || tipo === "application/x-ole-storage"
    ) {
        return "doc";
    }
    if (
        tipo === "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        || tipo === "application/zip"
    ) {
        return "docx";
    }
    return "";
}

function normalizarArquivoTransferido(file, prefixo = "arquivo") {
    if (!file) {
        return null;
    }

    if (file.name) {
        return file;
    }

    const extensao = obterExtensaoPorMime(file.type);
    if (!extensao || typeof File !== "function") {
        return file;
    }

    try {
        return new File(
            [file],
            `${prefixo}-${Date.now()}.${extensao}`,
            { type: file.type || "", lastModified: Date.now() }
        );
    } catch (_err) {
        return file;
    }
}

function dataTransferTemArquivo(dataTransfer) {
    if (!dataTransfer) {
        return false;
    }

    if (dataTransfer.files && dataTransfer.files.length > 0) {
        return true;
    }

    return Array.from(dataTransfer.items || []).some((item) => item.kind === "file");
}

function obterArquivoTransferido(dataTransfer) {
    if (!dataTransfer) {
        return null;
    }

    if (dataTransfer.files && dataTransfer.files.length > 0) {
        const arquivos = Array.from(dataTransfer.files);
        return arquivos.find((file) => arquivoSuportado(normalizarArquivoTransferido(file))) || arquivos[0];
    }

    const arquivos = [];
    for (const item of Array.from(dataTransfer.items || [])) {
        if (item.kind !== "file") {
            continue;
        }

        const file = item.getAsFile();
        if (file) {
            arquivos.push(file);
        }
    }

    return arquivos.find((file) => arquivoSuportado(normalizarArquivoTransferido(file))) || arquivos[0] || null;
}

async function selecionarArquivoParaImpressao(file, mensagemSucesso = "") {
    if (!file) {
        return false;
    }

    const arquivo = normalizarArquivoTransferido(file, "arquivo-colado");
    if (!arquivoSuportado(arquivo)) {
        el("msg").innerText = "Formato não suportado. Use PDF, DOCX, DOC, PNG, JPG ou JPEG.";
        return false;
    }

    jobHistoricoSelecionadoAtual = null;
    arquivoSelecionadoAtual = arquivo;
    sincronizarInputArquivo(arquivo);
    atualizarEstadoArquivoSelecionado();
    atualizarDestaqueJobSelecionado();

    await carregarPreview(arquivo);
    if (mensagemSucesso && !el("msg").innerText.trim()) {
        el("msg").innerText = mensagemSucesso;
    }
    return true;
}

function arquivoEhPdf(file) {
    return (
        obterExtensaoArquivo(file?.name || "") === "pdf"
        || String(file?.type || "").trim().toLowerCase() === "application/pdf"
    );
}

function arquivoSuportado(file) {
    const extensao = obterExtensaoArquivo(file?.name || "");
    return EXTENSOES_SUPORTADAS.has(extensao);
}

function obterMensagemPreviewVazio() {
    const arquivo = obterArquivoSelecionado();
    if (!arquivo) {
        return "Selecione um arquivo para visualizar as páginas.";
    }
    return "Não foi possível carregar a pré-visualização do arquivo.";
}

function isPreviewMobile() {
    return window.innerWidth <= BREAKPOINT_MOBILE_PREVIEW;
}

function atualizarModoNavegacaoPreview(isMobile) {
    const paginacao = document.querySelector(".print-pagination");
    if (!paginacao) {
        return;
    }
    paginacao.classList.toggle("is-desktop-scroll", false);
}

function ajustarPosicaoPainelMeta() {
    const metaCompact = document.querySelector(".print-meta-compact");
    const optionsPanel = document.querySelector(".print-options-panel");
    const metaPanel = document.querySelector(".print-meta-panel");
    if (!metaCompact || !optionsPanel || !metaPanel) {
        return;
    }

    const mobile = isPreviewMobile();
    if (mobile) {
        if (!optionsPanel.contains(metaCompact)) {
            optionsPanel.appendChild(metaCompact);
        }
        return;
    }

    if (!metaPanel.contains(metaCompact)) {
        metaPanel.appendChild(metaCompact);
    }
}

function obterConfigLayout(paginasPorFolha, orientacao = "retrato") {
    if (paginasPorFolha === 1) {
        return { colunas: 1, linhas: 1 };
    }
    if (paginasPorFolha === 2) {
        if (orientacao === "retrato") {
            return { colunas: 1, linhas: 2 };
        }
        return { colunas: 2, linhas: 1 };
    }
    return { colunas: 2, linhas: 2 };
}

function expandirPaginasParaFolha(paginasDaFolha, paginasPorFolha) {
    const paginas = Array.from(paginasDaFolha || []);
    if (paginas.length === 1 && (paginasPorFolha === 2 || paginasPorFolha === 4)) {
        while (paginas.length < paginasPorFolha) {
            paginas.push(paginas[0]);
        }
    }
    return paginas;
}

function obterDimensoesMiniatura(tamanhoFolha, isMobile) {
    const pane = document.querySelector(".print-preview-pane");

    const larguraDisponivel = pane
        ? Math.max(180, pane.clientWidth - RESERVA_BORDA_PREVIEW)
        : Math.max(180, window.innerWidth - 40);
    const alturaDisponivelBase = pane
        ? Math.max(220, pane.clientHeight - RESERVA_BORDA_PREVIEW)
        : Math.max(220, Math.floor(window.innerHeight * (isMobile ? 0.62 : 0.5)));

    const alturaDisponivel = isMobile
        ? Math.max(260, alturaDisponivelBase - Math.max(12, LABEL_PREVIEW_RESERVA - 24))
        : alturaDisponivelBase;
    const larguraAlvo = isMobile
        ? Math.max(
            180,
            Math.min(
                larguraDisponivel,
                window.innerWidth - 28,
                420
            )
        )
        : larguraDisponivel;
    const escala = Math.min(
        larguraAlvo / tamanhoFolha.largura,
        alturaDisponivel / tamanhoFolha.altura
    );

    return {
        largura: Math.max(isMobile ? 180 : 96, Math.round(tamanhoFolha.largura * escala)),
        altura: Math.max(isMobile ? 250 : 130, Math.round(tamanhoFolha.altura * escala))
    };
}

function obterDimensoesMiniaturaDesktop(tamanhoFolha, larguraTrilha) {
    const larguraDisponivel = Math.max(72, larguraTrilha - 28);
    const alturaMaxima = 170;
    const escala = Math.min(
        larguraDisponivel / tamanhoFolha.largura,
        alturaMaxima / tamanhoFolha.altura
    );

    return {
        largura: Math.max(72, Math.round(tamanhoFolha.largura * escala)),
        altura: Math.max(56, Math.round(tamanhoFolha.altura * escala))
    };
}

function obterPaginasPreview() {
    if (!pdfDoc) {
        return [];
    }

    try {
        return obterPaginasSelecionadas();
    } catch (err) {
        return [];
    }
}

function mostrarPreviewVazio(texto = obterMensagemPreviewVazio()) {
    const container = el("previewContainer");
    container.innerHTML = "";
    const isMobile = isPreviewMobile();
    container.classList.toggle("is-carousel", isMobile);
    container.classList.toggle("is-desktop-focus", !isMobile);
    atualizarModoNavegacaoPreview(isMobile);

    const msg = document.createElement("p");
    msg.className = "preview-empty";
    msg.innerText = texto;
    container.appendChild(msg);
}

function atualizarDestaqueFolha() {
    const thumbs = document.querySelectorAll("#previewContainer .print-sheet-thumb");
    thumbs.forEach((thumb) => {
        const numeroFolha = Number(thumb.dataset.folha);
        thumb.classList.toggle("is-active", numeroFolha === folhaAtual);
    });
}

function centralizarFolhaAtiva(suave = true) {
    const folhaAtiva = document.querySelector(`#previewContainer .print-sheet-thumb[data-folha="${folhaAtual}"]`);
    if (!folhaAtiva) {
        return;
    }
    const isMobile = isPreviewMobile();
    if (!isMobile) {
        return;
    }
    const previewPane = document.querySelector(".print-preview-pane");
    if (!previewPane) {
        return;
    }

    const scrollAlvo = Math.max(
        0,
        Math.min(
            folhaAtiva.offsetLeft - ((previewPane.clientWidth - folhaAtiva.offsetWidth) / 2),
            previewPane.scrollWidth - previewPane.clientWidth
        )
    );

    if (typeof previewPane.scrollTo === "function") {
        previewPane.scrollTo({
            left: scrollAlvo,
            behavior: suave ? "smooth" : "auto",
        });
        return;
    }

    previewPane.scrollLeft = scrollAlvo;
}

function obterOrientacaoPreview() {
    return el("orientacao").value;
}

function atualizarComportamentoOrientacao() {
    const orientacaoEl = el("orientacao");
    orientacaoEl.disabled = false;
    orientacaoEl.title = "";
}

function obterPaginasSelecionadas() {
    if (!pdfDoc) {
        return [];
    }

    const totalPaginas = pdfDoc.numPages;
    const texto = el("intervaloPaginas").value.trim();
    const infoEl = el("intervaloInfo");

    if (!texto) {
        infoEl.innerText = `Todas as páginas (${totalPaginas}).`;
        return Array.from({ length: totalPaginas }, (_, i) => i + 1);
    }

    const paginas = new Set();
    const partes = texto.split(",").map((p) => p.trim()).filter(Boolean);

    for (const parte of partes) {
        if (parte.includes("-")) {
            const [inicioTxt, fimTxt] = parte.split("-").map((n) => n.trim());
            const inicio = Number(inicioTxt);
            const fim = Number(fimTxt);

            if (!Number.isInteger(inicio) || !Number.isInteger(fim) || inicio <= 0 || fim <= 0 || inicio > fim) {
                throw new Error(`Intervalo inválido: "${parte}"`);
            }

            for (let pagina = inicio; pagina <= fim; pagina++) {
                if (pagina > totalPaginas) {
                    throw new Error(`Página ${pagina} não existe no documento`);
                }
                paginas.add(pagina);
            }
            continue;
        }

        const pagina = Number(parte);
        if (!Number.isInteger(pagina) || pagina <= 0) {
            throw new Error(`Página inválida: "${parte}"`);
        }
        if (pagina > totalPaginas) {
            throw new Error(`Página ${pagina} não existe no documento`);
        }
        paginas.add(pagina);
    }

    const resultado = Array.from(paginas).sort((a, b) => a - b);
    infoEl.innerText = `${resultado.length} página(s) selecionada(s).`;
    return resultado;
}

function gerarIntervaloApartirPaginas(paginasSelecionadas, totalPaginas) {
    const ordenadas = Array.from(new Set(paginasSelecionadas || []))
        .filter((pagina) => Number.isInteger(pagina) && pagina > 0 && pagina <= totalPaginas)
        .sort((a, b) => a - b);

    if (ordenadas.length === 0) {
        return "";
    }

    if (ordenadas.length === totalPaginas && ordenadas[0] === 1 && ordenadas[ordenadas.length - 1] === totalPaginas) {
        return "";
    }

    const partes = [];
    let inicio = ordenadas[0];
    let fim = ordenadas[0];

    for (let i = 1; i < ordenadas.length; i++) {
        const atual = ordenadas[i];
        if (atual === fim + 1) {
            fim = atual;
            continue;
        }

        partes.push(inicio === fim ? `${inicio}` : `${inicio}-${fim}`);
        inicio = atual;
        fim = atual;
    }
    partes.push(inicio === fim ? `${inicio}` : `${inicio}-${fim}`);
    return partes.join(", ");
}

function aplicarEstadoSelecaoWrapper(wrapper, paginaSelecionada, numeroPagina) {
    if (!wrapper) {
        return;
    }

    wrapper.classList.toggle("is-selected", paginaSelecionada);
    wrapper.classList.toggle("is-unchecked", !paginaSelecionada);
    wrapper.dataset.pageLabel = `Pg ${numeroPagina}`;
}

function atualizarEstadoVisualPagina(numeroPagina, paginaSelecionada) {
    const wrapper = document.querySelector(`#previewContainer .preview-cell[data-page="${numeroPagina}"]`);
    if (!wrapper) {
        return;
    }
    aplicarEstadoSelecaoWrapper(wrapper, paginaSelecionada, numeroPagina);
}

function alternarSelecaoPagina(numeroPagina) {
    if (!pdfDoc || !Number.isInteger(numeroPagina) || numeroPagina <= 0) {
        return;
    }

    let paginasSelecionadas;
    try {
        paginasSelecionadas = obterPaginasSelecionadas();
    } catch (err) {
        el("msg").innerText = err.message;
        return;
    }

    const selecionadas = new Set(paginasSelecionadas);
    if (selecionadas.has(numeroPagina)) {
        if (selecionadas.size === 1) {
            el("msg").innerText = "Mantenha ao menos uma página selecionada.";
            return;
        }
        selecionadas.delete(numeroPagina);
    } else {
        selecionadas.add(numeroPagina);
    }

    const resultado = Array.from(selecionadas).sort((a, b) => a - b);
    el("intervaloPaginas").value = gerarIntervaloApartirPaginas(resultado, pdfDoc.numPages);
    el("msg").innerText = "";
    atualizarEstadoVisualPagina(numeroPagina, selecionadas.has(numeroPagina));
    calcularConsumo();
}

function calcularResumoImpressao() {
    if (!pdfDoc) {
        const arquivo = obterArquivoSelecionado();
        if (arquivo && arquivoSuportado(arquivo) && !el("intervaloInfo").innerText.trim()) {
            el("intervaloInfo").innerText = "Aguardando pré-visualização do documento.";
        }
        el("consumo").innerText = "";
        return null;
    }

    try {
        const paginasSelecionadas = obterPaginasSelecionadas();
        const copias = Math.max(1, Number(el("copias").value) || 1);
        const paginasPorFolha = Number(el("paginasPorFolha").value);
        const duplex = el("duplex").checked;
        const paginasImpressas = paginasSelecionadas.length * copias;

        const facesPorCopia = Math.ceil(paginasSelecionadas.length / paginasPorFolha);
        const folhasPorCopia = duplex ? Math.ceil(facesPorCopia / 2) : facesPorCopia;
        const consumo = folhasPorCopia * copias;

        return {
            consumo,
            copias,
            paginasSelecionadas: paginasSelecionadas.length,
            paginasImpressas,
            paginasPorFolha,
            duplex,
        };
    } catch (err) {
        el("consumo").innerText = "";
        el("intervaloInfo").innerText = err.message;
        return null;
    }
}

function calcularConsumo() {
    const resumo = calcularResumoImpressao();
    if (!resumo) {
        return 0;
    }

    el("consumo").innerText = `Consumo estimado: ${resumo.consumo} folhas`;
    return resumo.consumo;
}

function modalAlertaConsumoAberto() {
    const modal = el("modalAlertaConsumoImpressao");
    return Boolean(modal) && !modal.hidden;
}

function fecharModalAlertaConsumo(confirmado) {
    const modal = el("modalAlertaConsumoImpressao");
    if (!modal || modal.hidden) {
        return;
    }

    modal.hidden = true;
    document.body.classList.remove("print-alert-modal-open");
    if (typeof resolverModalAlertaConsumoAtual === "function") {
        const resolver = resolverModalAlertaConsumoAtual;
        resolverModalAlertaConsumoAtual = null;
        resolver(Boolean(confirmado));
    }
}

function abrirModalAlertaConsumo({ consumo, paginasPorFolha, orientacao, copias, paginasImpressas, paginasSelecionadas }) {
    const modal = el("modalAlertaConsumoImpressao");
    const painel = el("painelAlertaConsumoImpressao");
    const texto = el("textoAlertaConsumoImpressao");
    const sugestao = el("sugestaoAlertaConsumoImpressao");

    if (!modal || !painel || !texto || !sugestao) {
        return Promise.resolve(window.confirm(
            `Essa impressão deve gerar ${paginasImpressas} páginas e consumir cerca de ${consumo} folhas. Deseja imprimir mesmo assim?`
        ));
    }

    const ajustes = [];
    if (paginasPorFolha < 2) {
        ajustes.push("alterar para 2 páginas por folha");
    }
    if (orientacao !== "paisagem") {
        ajustes.push("mudar a orientação para paisagem");
    }

    const facesPorCopiaComDuasPorFolha = Math.ceil(paginasSelecionadas / 2);
    const folhasPorCopiaComDuasPorFolha = el("duplex").checked
        ? Math.ceil(facesPorCopiaComDuasPorFolha / 2)
        : facesPorCopiaComDuasPorFolha;
    const consumoComDuasPorFolha = folhasPorCopiaComDuasPorFolha * copias;
    const economiaComDuasPorFolha = Math.max(consumo - consumoComDuasPorFolha, 0);

    if (paginasPorFolha < 2 && economiaComDuasPorFolha > 0) {
        texto.innerText = `Essa impressão vai gastar ao todo ${consumo} páginas. Você pode economizar ${economiaComDuasPorFolha} páginas se mudar para 2 páginas por folha.`;
    } else {
        texto.innerText = copias > 1
            ? `Essa impressão vai gastar ${consumo} páginas ao todo (${paginasSelecionadas} páginas por copia em ${copias} copia(s)).`
            : `Essa impressão vai gastar ${consumo} páginas.`;
    }

    sugestao.innerText = ajustes.length > 0
        ? `Sugestão: ${ajustes.join(" e ")} antes de enviar para economizar papel.`
        : "Esta configuracao já está otimizada, mas o consumo continua alto. Revise o intervalo e a quantidade de cópias se desejar.";

    modal.hidden = false;
    document.body.classList.add("print-alert-modal-open");

    return new Promise((resolve) => {
        resolverModalAlertaConsumoAtual = resolve;
        window.setTimeout(() => {
            painel.focus();
        }, 0);
    });
}

function normalizarStatusJob(status) {
    return String(status || "").trim().toUpperCase();
}

function obterRotuloStatusJob(status) {
    const statusNormalizado = normalizarStatusJob(status);
    return STATUS_JOB_LABEL[statusNormalizado] || statusNormalizado || "Desconhecido";
}

function obterClasseStatusJob(status) {
    const statusNormalizado = normalizarStatusJob(status);
    if (statusNormalizado === "PENDENTE") {
        return "status-pendente";
    }
    if (statusNormalizado === "IMPRIMINDO") {
        return "status-imprimindo";
    }
    if (statusNormalizado === "CONCLUIDO" || statusNormalizado === "FINALIZADO") {
        return "status-concluido";
    }
    if (statusNormalizado === "CANCELADO") {
        return "status-cancelado";
    }
    if (statusNormalizado === "ERRO") {
        return "status-erro";
    }
    return "status-desconhecido";
}

function jobPodeSerCancelado(job) {
    return normalizarStatusJob(job?.status) === "PENDENTE";
}

function jobPodeSerReutilizado(job) {
    if (typeof job?.pode_reutilizar === "boolean") {
        return job.pode_reutilizar;
    }

    const statusNormalizado = normalizarStatusJob(job?.status);
    return statusNormalizado === "CONCLUIDO" || statusNormalizado === "FINALIZADO";
}

function jobHistoricoEstaSelecionado(job) {
    return Number(jobHistoricoSelecionadoAtual?.id || 0) === Number(job?.id || 0);
}

function atualizarDestaqueJobSelecionado() {
    const items = document.querySelectorAll(
        "#lista-jobs .print-job-item[data-job-id], #lista-jobs-etapa-arquivo .print-job-item[data-job-id]"
    );
    items.forEach((item) => {
        const selecionado = Number(item.dataset.jobId || 0) === Number(jobHistoricoSelecionadoAtual?.id || 0);
        item.classList.toggle("is-selected-source", selecionado);

        const botao = item.querySelector(".print-job-reuse-btn");
        if (botao) {
            botao.innerText = selecionado ? "No preview" : "Usar novamente";
        }

        const dica = item.querySelector(".print-job-hint");
        if (dica) {
            dica.innerText = selecionado
                ? "Arquivo carregado no preview atual."
                : "Clique para abrir este arquivo novamente no preview.";
        }
    });
}

function atualizarCabecalhoCardJobRecente({
    badge = "Pedido enviado",
    titulo = "Acompanhar pedido",
    hint = "Enquanto o pedido estiver pendente, voce pode cancelar por aqui sem abrir o historico.",
} = {}) {
    definirTexto("painelJobRecenteBadge", badge);
    definirTexto("painelJobRecenteTitulo", titulo);
    definirTexto("painelJobRecenteHint", hint);
}

function jobEstaEmEstadoFinal(job) {
    const statusNormalizado = normalizarStatusJob(job?.status);
    return statusNormalizado === "CONCLUIDO"
        || statusNormalizado === "FINALIZADO"
        || statusNormalizado === "CANCELADO"
        || statusNormalizado === "ERRO";
}

function obterJobAcompanhamentoAtivoId() {
    const submitState = window.PrintingUI?.state?.getState?.()?.submit;
    if (!submitState?.submitted) {
        return 0;
    }
    return Number(submitState.activeJobId || 0);
}

function atualizarAcaoImprimirOutroArquivo(visivel = false) {
    const botao = el("btnImprimirOutroArquivo");
    if (!botao) {
        return;
    }
    botao.hidden = !visivel;
}

function obterContextoAcompanhamentoJob(job) {
    const statusNormalizado = normalizarStatusJob(job?.status);

    if (statusNormalizado === "IMPRIMINDO") {
        return {
            badge: "Em andamento",
            titulo: "A impressao ja esta em andamento",
            hint: "O pedido saiu da fila e a impressora esta processando o arquivo agora.",
            mostrarNovoArquivo: false,
        };
    }

    if (statusNormalizado === "CONCLUIDO" || statusNormalizado === "FINALIZADO") {
        return {
            badge: "Concluido",
            titulo: "Impressao concluida",
            hint: "Tudo certo com este pedido. Quando quiser, voce pode iniciar outro arquivo.",
            mostrarNovoArquivo: true,
        };
    }

    if (statusNormalizado === "CANCELADO") {
        return {
            badge: "Cancelado",
            titulo: "Pedido cancelado",
            hint: "O pedido foi cancelado e a cota ja foi atualizada. Voce pode iniciar outro arquivo.",
            mostrarNovoArquivo: true,
        };
    }

    if (statusNormalizado === "ERRO") {
        return {
            badge: "Falha no pedido",
            titulo: "O pedido encontrou um erro",
            hint: String(job?.erro_mensagem || "Houve um problema na impressao. Voce pode iniciar outro arquivo."),
            mostrarNovoArquivo: true,
        };
    }

    return {
        badge: "Pedido enviado",
        titulo: "Seu arquivo entrou na fila",
        hint: "Enquanto o pedido estiver pendente, voce pode cancelar por aqui sem abrir o historico.",
        mostrarNovoArquivo: false,
    };
}

function limparCardJobRecente() {
    const lista = el("lista-job-recente");
    if (lista) {
        lista.innerHTML = "";
        lista.hidden = true;
    }
    atualizarCabecalhoCardJobRecente();
    atualizarAcaoImprimirOutroArquivo(false);
}

function aplicarEstadoVisualCardJobRecente(item, job) {
    const statusNormalizado = normalizarStatusJob(job?.status);
    const concluido = statusNormalizado === "CONCLUIDO" || statusNormalizado === "FINALIZADO";
    const interrompido = statusNormalizado === "CANCELADO" || statusNormalizado === "ERRO";

    item.classList.toggle("is-progress-complete", concluido);
    item.classList.toggle("is-progress-stopped", interrompido);
}

function renderizarCardJobRecente(job) {
    const lista = el("lista-job-recente");
    if (!lista || !job) {
        limparCardJobRecente();
        return;
    }

    const contexto = obterContextoAcompanhamentoJob(job);
    const jobId = Number(job?.id || 0);
    const itemAtual = lista.querySelector("li.print-job-item");
    const manterItemAtual = itemAtual && Number(itemAtual.dataset.jobId || 0) === jobId;

    atualizarCabecalhoCardJobRecente(contexto);

    if (manterItemAtual) {
        preencherItemJob(itemAtual, job, { allowReuse: false });
        itemAtual.classList.add("is-inline-queue-card-item");
        aplicarEstadoVisualCardJobRecente(itemAtual, job);
    } else {
        lista.innerHTML = "";
        const item = criarItemJob(job, { allowReuse: false });
        item.classList.add("is-inline-queue-card-item");
        aplicarEstadoVisualCardJobRecente(item, job);
        lista.appendChild(item);
    }

    lista.hidden = false;
    atualizarAcaoImprimirOutroArquivo(contexto.mostrarNovoArquivo);
}

function abrirEtapaAcompanhamentoJob(job) {
    const jobId = Number(job?.id || 0);
    if (jobId <= 0) {
        return;
    }

    renderizarCardJobRecente(job);
    window.PrintingUI?.ui?.setWizardState?.(5, {
        submit: {
            submitted: true,
            activeJobId: jobId,
        },
    });
}

function encerrarEtapaAcompanhamentoJob() {
    limparCardJobRecente();
    window.PrintingUI?.ui?.setForcedStep?.(null);
    window.PrintingUI?.ui?.setWizardState?.(1, {
        submit: {
            submitted: false,
            activeJobId: null,
        },
    });
}

async function imprimirOutroArquivo() {
    encerrarEtapaAcompanhamentoJob();
    el("msg").innerText = "";
    await carregarPreview(null);
    window.requestAnimationFrame(() => {
        window.PrintingUI?.ui?.goToStep?.(1);
        el("arquivoDropzone")?.focus();
    });
}

function sincronizarCardJobRecenteComFila(jobs) {
    const jobAtualId = obterJobAcompanhamentoAtivoId();
    if (!jobAtualId) {
        return;
    }

    const jobAtualizado = Array.isArray(jobs)
        ? jobs.find((job) => Number(job?.id || 0) === jobAtualId)
        : null;

    if (!jobAtualizado) {
        return;
    }

    renderizarCardJobRecente(jobAtualizado);
}

function atualizarEstadoEnvio(ativo, mensagem = "") {
    const botao = el("btnEnviar");
    const estado = el("estadoEnvio");
    if (!botao || !estado) {
        return;
    }

    if (!botao.dataset.labelPadrao) {
        botao.dataset.labelPadrao = botao.innerText || "Imprimir";
    }

    const bloqueado = impressaoBloqueadaSemPapel();
    botao.disabled = ativo || bloqueado;
    botao.classList.toggle("is-loading", ativo);
    botao.setAttribute("aria-busy", ativo ? "true" : "false");
    botao.innerText = ativo
        ? "Enviando..."
        : (bloqueado ? "Impressao indisponivel" : botao.dataset.labelPadrao);

    const mensagemFinal = mensagem || (bloqueado ? obterMensagemSemPapel() : "");
    estado.classList.toggle("is-active", Boolean(mensagemFinal));
    estado.innerText = mensagemFinal;
}

async function enviarImpressao(confirmadoAlertaConsumo = false) {
    const envioConfirmado = confirmadoAlertaConsumo === true;
    if (envioEmAndamento) {
        return;
    }

    if (impressaoBloqueadaSemPapel()) {
        const mensagem = obterMensagemSemPapel();
        el("msg").innerText = mensagem;
        aplicarStatusImpressaoNaTela({ mostrarModal: true });
        return;
    }

    const arquivo = obterArquivoSelecionado();
    const jobHistoricoId = Number(jobHistoricoSelecionadoAtual?.id || 0);
    const copias = Number(el("copias").value);
    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const duplex = el("duplex").checked;
    const orientacao = obterOrientacaoPreview();
    const intervaloPaginas = el("intervaloPaginas").value.trim();
    const tagsSelecionadas = obterTagsImpressaoSelecionadas();
    const professorSolicitanteId = obterProfessorSolicitanteSelecionadoId();
    const usaHistorico = jobHistoricoId > 0;

    if (professorSolicitantePendente()) {
        el("msg").innerText = "Selecione o professor solicitante antes de continuar a impressao.";
        return;
    }

    if ((!arquivo && !usaHistorico) || !copias || copias < 1) {
        el("msg").innerText = "Selecione um arquivo e informe uma quantidade válida de cópias.";
        return;
    }

    if (arquivo && !arquivoSuportado(arquivo)) {
        el("msg").innerText = "Formato não suportado. Use PDF, DOCX, DOC, PNG, JPG ou JPEG.";
        return;
    }

    if (tagsSelecionadas.length === 0) {
        el("msg").innerText = "Selecione ao menos uma tag antes de imprimir.";
        return;
    }

    if (previewEmCarregamento) {
        el("msg").innerText = "Aguarde a prÃ©-visualizaÃ§Ã£o terminar para validar o volume da impressÃ£o.";
        return;
    }

    if (!usaHistorico && arquivo && !pdfDoc) {
        el("msg").innerText = "A prÃ©-visualizaÃ§Ã£o ainda nÃ£o ficou disponÃ­vel. Tente novamente em instantes.";
        return;
    }

    if (pdfDoc) {
        try {
            obterPaginasSelecionadas();
        } catch (err) {
            el("msg").innerText = err.message;
            return;
        }
    }

    const resumoImpressao = calcularResumoImpressao();
    if (!envioConfirmado && resumoImpressao && resumoImpressao.paginasImpressas > LIMITE_ALERTA_IMPRESSAO_PAGINAS) {
        const confirmar = await abrirModalAlertaConsumo({
            consumo: resumoImpressao.consumo,
            paginasPorFolha,
            orientacao,
            copias,
            paginasImpressas: resumoImpressao.paginasImpressas,
            paginasSelecionadas: resumoImpressao.paginasSelecionadas,
        });
        if (!confirmar) {
            el("msg").innerText = "Revise a configuracao antes de enviar a impressao.";
            return;
        }
    }

    envioEmAndamento = true;
    atualizarEstadoEnvio(
        true,
        usaHistorico
            ? "Reenviando arquivo do histórico para a fila..."
            : "Enviando para fila e validando consumo da cota..."
    );
    el("msg").innerText = "";

    try {
        const formData = new FormData();
        formData.append("copias", copias);
        formData.append("paginas_por_folha", paginasPorFolha);
        formData.append("duplex", duplex);
        formData.append("orientacao", orientacao);
        if (!usaHistorico) {
            formData.append("arquivo", arquivo);
        }
        if (intervaloPaginas) {
            formData.append("intervalo_paginas", intervaloPaginas);
        }
        if (professorSolicitanteId > 0) {
            formData.append("professor_id", professorSolicitanteId);
        }
        tagsSelecionadas.forEach((tag) => {
            formData.append("tags", tag);
        });

        const endpoint = usaHistorico ? `/jobs/${jobHistoricoId}/reimprimir` : "/imprimir";
        const res = await fetchComAuth(endpoint, {
            method: "POST",
            headers,
            body: formData
        });

        const data = await lerJsonResposta(
            res,
            "Não foi possível interpretar a resposta do servidor ao enviar a impressão."
        );
        if (!res.ok) {
            el("msg").innerText = data.detail || "Não foi possível enviar a impressão.";
            return;
        }

        const professorSelecionado = obterProfessorSelecionado();
        const sufixoDestino = professorSelecionado ? ` para ${professorSelecionado.nome}` : "";
        const verbo = usaHistorico ? "Reenviado" : "Enviado";
        el("msg").innerText = data.cota_ilimitada
            ? `${verbo}${sufixoDestino}! Cota ilimitada da gestao.`
            : `${verbo}${sufixoDestino}! Restam ${data.paginas_restantes} páginas`;
        const jobs = await carregarFila();
        const jobEnviadoId = Number(data?.job_id || data?.id || 0);
        const jobRecente = Array.isArray(jobs)
            ? (jobs.find((job) => Number(job?.id || 0) === jobEnviadoId) || jobs[0])
            : null;
        if (jobRecente) {
            abrirEtapaAcompanhamentoJob(jobRecente);
        }
        await carregarCota();
        calcularConsumo();
    } catch (err) {
        el("msg").innerText = err?.message || "Falha ao enviar impressão.";
    } finally {
        envioEmAndamento = false;
        atualizarEstadoEnvio(false, "");
    }
}

async function carregarCota() {
    atualizarTitulosContextoImpressao();

    if (professorSolicitantePendente()) {
        el("cota").innerText = "Selecione um professor para consultar a cota.";
        return;
    }

    const res = await fetchComAuth(montarUrlConsultaImpressao("/minha-cota"), { headers });
    if (!res.ok) {
        throw new Error(await obterMensagemErroResposta(res, "Não foi possível carregar a cota."));
    }

    const data = await lerJsonResposta(res, "Não foi possível carregar a cota.");
    if (data.ilimitada) {
        el("cota").innerText = "Cota ilimitada";
        return;
    }
    el("cota").innerText = `Cota restante: ${data.restante} páginas`;
}

async function cancelarJobProfessor(jobId, botaoCancelar) {
    if (!jobId || !botaoCancelar) {
        return;
    }

    const confirmar = window.confirm("Cancelar este job? A cota será estornada se ele ainda estiver pendente.");
    if (!confirmar) {
        return;
    }

    const textoOriginal = botaoCancelar.innerText;
    botaoCancelar.disabled = true;
    botaoCancelar.classList.add("is-loading");
    botaoCancelar.innerText = "Cancelando...";

    try {
        const res = await fetchComAuth(`/jobs/${jobId}/cancelar`, {
            method: "POST",
            headers
        });
        const data = await lerJsonResposta(res, "Não foi possível cancelar o pedido de impressão.");

        if (!res.ok) {
            el("msg").innerText = data.detail || "Não foi possível cancelar este job.";
            return;
        }

        const estornadas = Number(data.paginas_estornadas || 0);
        el("msg").innerText = estornadas > 0
            ? `Job cancelado. ${estornadas} página(s) estornada(s) na cota.`
            : "Job cancelado com sucesso.";

        if (typeof data.paginas_restantes === "number") {
            el("cota").innerText = `Restante: ${data.paginas_restantes} páginas`;
        } else {
            await carregarCota();
        }
        await carregarFila();
    } catch (err) {
        el("msg").innerText = err?.message || "Falha ao cancelar job.";
    } finally {
        botaoCancelar.disabled = false;
        botaoCancelar.classList.remove("is-loading");
        botaoCancelar.innerText = textoOriginal;
    }
}

function criarArquivoHistoricoVirtual(arrayBuffer, job) {
    const nomeArquivo = String(job?.arquivo || `job-${job?.id || Date.now()}.pdf`).trim()
        || `job-${job?.id || Date.now()}.pdf`;

    if (typeof File === "function") {
        return new File([arrayBuffer], nomeArquivo, {
            type: "application/pdf",
            lastModified: Date.now()
        });
    }

    const blob = new Blob([arrayBuffer], { type: "application/pdf" });
    blob.name = nomeArquivo;
    return blob;
}

async function carregarDocumentoPdfNoPreview(arrayBuffer, cargaAtual) {
    if (cargaAtual !== previewLoadSeq) {
        return;
    }

    pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    if (cargaAtual !== previewLoadSeq) {
        return;
    }

    folhaAtual = 1;
    el("intervaloInfo").innerText = "";
    previewEmCarregamento = false;
    atualizarPreview();
}

async function carregarJobHistoricoNoPreview(job) {
    if (!job?.id || !jobPodeSerReutilizado(job)) {
        return;
    }

    previewLoadSeq += 1;
    const cargaAtual = previewLoadSeq;
    if (previewAbortController) {
        previewAbortController.abort();
        previewAbortController = null;
    }

    previewEmCarregamento = true;
    pdfDoc = null;
    folhaAtual = 1;
    el("intervaloPaginas").value = "";
    el("msg").innerText = "";
    el("intervaloInfo").innerText = "Buscando arquivo do histórico...";
    renderTokenAtual += 1;
    mostrarPreviewVazio("Buscando arquivo do histórico...");
    calcularConsumo();
    atualizarContador();

    try {
        previewAbortController = new AbortController();
        const res = await fetchComAuth(`/jobs/${job.id}/preview`, {
            headers,
            signal: previewAbortController.signal
        });

        if (!res.ok) {
            const detalhe = await obterMensagemErroResposta(
                res,
                "Não foi possível carregar o arquivo deste histórico."
            );
            throw new Error(detalhe);
        }

        const arrayBuffer = await res.arrayBuffer();
        if (cargaAtual !== previewLoadSeq) {
            return;
        }

        const arquivoHistorico = criarArquivoHistoricoVirtual(arrayBuffer, job);
        jobHistoricoSelecionadoAtual = {
            id: Number(job.id),
            arquivo: String(job?.arquivo || "")
        };
        arquivoSelecionadoAtual = arquivoHistorico;
        aplicarTagsImpressaoSelecionadas(job?.tags || []);
        sincronizarInputArquivo(null);
        atualizarEstadoArquivoSelecionado();
        atualizarDestaqueJobSelecionado();

        await carregarDocumentoPdfNoPreview(arrayBuffer, cargaAtual);
        if (cargaAtual === previewLoadSeq && !el("msg").innerText.trim()) {
            el("msg").innerText = `Arquivo do job #${job.id} carregado novamente no preview.`;
        }
    } catch (err) {
        if (err && err.name === "AbortError") {
            return;
        }
        if (cargaAtual !== previewLoadSeq) {
            return;
        }

        jobHistoricoSelecionadoAtual = null;
        arquivoSelecionadoAtual = null;
        sincronizarInputArquivo(null);
        atualizarEstadoArquivoSelecionado();
        atualizarDestaqueJobSelecionado();
        pdfDoc = null;
        folhaAtual = 1;
        renderTokenAtual += 1;
        el("msg").innerText = err?.message || "Falha ao carregar o arquivo do histórico.";
        el("intervaloInfo").innerText = "";
        previewEmCarregamento = false;
        mostrarPreviewVazio("Não foi possível carregar o arquivo do histórico.");
        calcularConsumo();
        atualizarContador();
    } finally {
        if (cargaAtual === previewLoadSeq) {
            previewAbortController = null;
        }
    }
}

function preencherItemJob(li, job, { allowReuse = true } = {}) {
    li.replaceChildren();
    li.className = "print-job-item";
    li.dataset.jobId = String(job?.id || "");
    li.classList.toggle("is-selected-source", allowReuse && jobHistoricoEstaSelecionado(job));
    li.removeAttribute("role");
    li.removeAttribute("aria-label");
    li.removeAttribute("title");
    li.removeAttribute("tabindex");

    const topo = document.createElement("div");
    topo.classList.add("print-job-top");

    const nomeArquivo = document.createElement("p");
    nomeArquivo.classList.add("print-job-file");
    nomeArquivo.innerText = String(job?.arquivo || "Arquivo sem nome");

    const status = document.createElement("span");
    status.classList.add("print-job-status", obterClasseStatusJob(job?.status));
    status.innerText = obterRotuloStatusJob(job?.status);

    topo.appendChild(nomeArquivo);
    topo.appendChild(status);

    const meta = document.createElement("p");
    meta.classList.add("print-job-meta");
    const copias = Number(job?.copias || 1);
    const paginasTotais = Number(job?.paginas_totais || 0);
    meta.innerText = `#${job?.id || "-"} • ${copias} cópia(s) • ${paginasTotais} página(s)`;

    li.appendChild(topo);
    li.appendChild(meta);

    if (Array.isArray(job?.tags) && job.tags.length > 0) {
        const tags = document.createElement("p");
        tags.classList.add("print-job-tags");
        tags.innerText = `Tags: ${job.tags.join(", ")}`;
        li.appendChild(tags);
    }

    const podeReutilizar = allowReuse && jobPodeSerReutilizado(job);
    if (podeReutilizar) {
        li.classList.add("is-reusable");
        li.setAttribute("tabindex", "0");
        li.setAttribute("role", "button");
        li.setAttribute("aria-label", `Abrir novamente ${String(job?.arquivo || "este arquivo")} no preview`);
        li.title = "Clique para abrir este arquivo novamente no preview.";

        const dica = document.createElement("p");
        dica.classList.add("print-job-hint");
        dica.innerText = jobHistoricoEstaSelecionado(job)
            ? "Arquivo carregado no preview atual."
            : "Clique para abrir este arquivo novamente no preview.";
        li.appendChild(dica);

        const abrirNovamente = () => {
            carregarJobHistoricoNoPreview(job).catch((err) => {
                el("msg").innerText = err?.message || "Falha ao buscar o arquivo do histórico.";
            });
        };

        li.addEventListener("click", (event) => {
            if (event.target.closest("button")) {
                return;
            }
            abrirNovamente();
        });
        li.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" && event.key !== " ") {
                return;
            }
            event.preventDefault();
            abrirNovamente();
        });
    }

    const motivoReusoIndisponivel = String(job?.motivo_reuso_indisponivel || "").trim();
    if (
        allowReuse
        && !podeReutilizar
        && motivoReusoIndisponivel
        && ["CONCLUIDO", "FINALIZADO"].includes(normalizarStatusJob(job?.status))
    ) {
        const dicaIndisponivel = document.createElement("p");
        dicaIndisponivel.classList.add("print-job-hint", "is-unavailable");
        dicaIndisponivel.innerText = motivoReusoIndisponivel;
        li.appendChild(dicaIndisponivel);
    }

    if (job?.erro_mensagem) {
        const erro = document.createElement("p");
        erro.classList.add("print-job-error");
        erro.innerText = String(job.erro_mensagem);
        li.appendChild(erro);
    }

    if (podeReutilizar || jobPodeSerCancelado(job)) {
        const acoes = document.createElement("div");
        acoes.classList.add("print-job-actions");

        if (podeReutilizar) {
            const btnReutilizar = document.createElement("button");
            btnReutilizar.type = "button";
            btnReutilizar.classList.add("print-job-reuse-btn");
            btnReutilizar.innerText = jobHistoricoEstaSelecionado(job) ? "No preview" : "Usar novamente";
            btnReutilizar.addEventListener("click", (event) => {
                event.stopPropagation();
                carregarJobHistoricoNoPreview(job).catch((err) => {
                    el("msg").innerText = err?.message || "Falha ao buscar o arquivo do histórico.";
                });
            });
            acoes.appendChild(btnReutilizar);
        }

        if (jobPodeSerCancelado(job)) {
            const btnCancelar = document.createElement("button");
            btnCancelar.type = "button";
            btnCancelar.classList.add("print-job-cancel-btn");
            btnCancelar.innerText = "Cancelar";
            btnCancelar.addEventListener("click", (event) => {
                event.stopPropagation();
                cancelarJobProfessor(job.id, btnCancelar);
            });
            acoes.appendChild(btnCancelar);
        }

        li.appendChild(acoes);
    }

    return li;
}

function criarItemJob(job, options) {
    const li = document.createElement("li");
    preencherItemJob(li, job, options);
    return li;
}

function renderizarJobsHistorico(jobs = []) {
    obterListasJobsImpressao().forEach((ul) => {
        ul.innerHTML = "";
        jobs.forEach((job) => {
            ul.appendChild(criarItemJob(job));
        });
    });
}

async function carregarFila() {
    atualizarTitulosContextoImpressao();

    if (professorSolicitantePendente()) {
        sincronizarCardJobRecenteComFila([]);
        renderFilaVazia(obterMensagemSelecaoProfessorImpressao());
        return [];
    }

    const res = await fetchComAuth(montarUrlConsultaImpressao("/meus-jobs"), { headers });
    if (!res.ok) {
        throw new Error(await obterMensagemErroResposta(res, "Não foi possível carregar os pedidos de impressão."));
    }

    const jobs = await lerJsonResposta(res, "Não foi possível carregar os pedidos de impressão.");

    if (!Array.isArray(jobs) || jobs.length === 0) {
        sincronizarCardJobRecenteComFila([]);
        const professorSelecionado = obterProfessorSelecionado();
        renderFilaVazia(
            professorSelecionado
                ? `Nenhuma impressão enviada por ${professorSelecionado.nome} até o momento.`
                : "Nenhuma impressão enviada até o momento."
        );
        return;
    }

    renderizarJobsHistorico(jobs);
    atualizarDestaqueJobSelecionado();
    sincronizarCardJobRecenteComFila(jobs);
    return jobs;
}

function iniciarPollingFila() {
    if (filaPollingTimer) {
        clearInterval(filaPollingTimer);
    }

    filaPollingTimer = window.setInterval(() => {
        carregarStatusImpressao().catch(() => {
            // Evita poluir a UI com erros intermitentes durante polling.
        });
        carregarFila().catch(() => {
            // Evita poluir a UI com erros intermitentes durante polling.
        });
    }, FILA_POLLING_MS);
}

async function carregarPreview(file) {
    previewLoadSeq += 1;
    const cargaAtual = previewLoadSeq;
    if (previewAbortController) {
        previewAbortController.abort();
        previewAbortController = null;
    }

    if (!file) {
        previewEmCarregamento = false;
        jobHistoricoSelecionadoAtual = null;
        arquivoSelecionadoAtual = null;
        sincronizarInputArquivo(null);
        atualizarEstadoArquivoSelecionado();
        atualizarDestaqueJobSelecionado();
        pdfDoc = null;
        folhaAtual = 1;
        el("intervaloPaginas").value = "";
        el("intervaloInfo").innerText = "";
        renderTokenAtual += 1;
        mostrarPreviewVazio();
        calcularConsumo();
        atualizarContador();
        return;
    }

    if (!arquivoSuportado(file)) {
        previewEmCarregamento = false;
        jobHistoricoSelecionadoAtual = null;
        arquivoSelecionadoAtual = null;
        sincronizarInputArquivo(null);
        atualizarEstadoArquivoSelecionado();
        atualizarDestaqueJobSelecionado();
        pdfDoc = null;
        folhaAtual = 1;
        renderTokenAtual += 1;
        el("msg").innerText = "Formato não suportado. Use PDF, DOCX, DOC, PNG, JPG ou JPEG.";
        el("intervaloInfo").innerText = "";
        mostrarPreviewVazio("Formato não suportado para pré-visualização.");
        calcularConsumo();
        atualizarContador();
        return;
    }

    // Novo upload deve iniciar com todas as páginas selecionadas.
    previewEmCarregamento = true;
    pdfDoc = null;
    folhaAtual = 1;
    el("intervaloPaginas").value = "";
    el("msg").innerText = "";
    el("intervaloInfo").innerText = "Gerando pré-visualização...";
    renderTokenAtual += 1;
    mostrarPreviewVazio("Gerando pré-visualização do documento...");
    calcularConsumo();
    atualizarContador();

    try {
        let arrayBuffer;
        if (arquivoEhPdf(file)) {
            arrayBuffer = await file.arrayBuffer();
        } else {
            const formData = new FormData();
            formData.append("arquivo", file);

            previewAbortController = new AbortController();
            const res = await fetchComAuth("/impressao/preview", {
                method: "POST",
                headers,
                body: formData,
                signal: previewAbortController.signal
            });

            if (!res.ok) {
                const detalhe = await obterMensagemErroResposta(
                    res,
                    "Falha ao gerar pré-visualização do documento."
                );
                throw new Error(detalhe);
            }

            arrayBuffer = await res.arrayBuffer();
        }

        if (cargaAtual !== previewLoadSeq) {
            return;
        }

        await carregarDocumentoPdfNoPreview(arrayBuffer, cargaAtual);
    } catch (err) {
        if (err && err.name === "AbortError") {
            return;
        }
        if (cargaAtual !== previewLoadSeq) {
            return;
        }

        pdfDoc = null;
        folhaAtual = 1;
        renderTokenAtual += 1;
        el("msg").innerText = err?.message || "Falha ao carregar a pré-visualização do documento.";
        el("intervaloInfo").innerText = "";
        previewEmCarregamento = false;
        mostrarPreviewVazio("Não foi possível carregar a pré-visualização do documento.");
        calcularConsumo();
        atualizarContador();
    } finally {
        if (cargaAtual === previewLoadSeq) {
            previewAbortController = null;
        }
    }
}

function atualizarPreview() {
    atualizarComportamentoOrientacao();
    calcularConsumo();
    atualizarContador();
    renderFolha();
}

function totalFolhasVisualizacao() {
    if (!pdfDoc) {
        return 0;
    }

    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const paginasPreview = obterPaginasPreview();
    if (!paginasPreview.length) {
        return 0;
    }
    return Math.max(1, Math.ceil(paginasPreview.length / paginasPorFolha));
}

function atualizarContador() {
    if (!pdfDoc) {
        el("contadorFolha").innerText = "";
        return;
    }
    const total = totalFolhasVisualizacao();
    if (!total) {
        el("contadorFolha").innerText = "";
        return;
    }
    if (folhaAtual > total) {
        folhaAtual = total;
    }
    el("contadorFolha").innerText = `Página ${folhaAtual} de ${total}`;
}

function irParaFolha(indiceFolha) {
    if (!pdfDoc) {
        return;
    }
    const total = totalFolhasVisualizacao();
    if (!total) {
        return;
    }
    const destino = Math.min(Math.max(1, indiceFolha), total);
    if (destino === folhaAtual) {
        return;
    }

    folhaAtual = destino;
    if (!isPreviewMobile()) {
        renderFolha();
        return;
    }
    atualizarContador();
    atualizarDestaqueFolha();
    centralizarFolhaAtiva();
}

function atualizarFolhaAtualPorScroll() {
    if (!pdfDoc) {
        return;
    }

    const pane = document.querySelector(".print-preview-pane");
    const thumbs = Array.from(document.querySelectorAll("#previewContainer .print-sheet-thumb"));
    if (!pane || thumbs.length === 0) {
        return;
    }

    const paneRect = pane.getBoundingClientRect();
    const mobile = isPreviewMobile();
    let folhaDetectada = folhaAtual;
    let menorDistancia = Number.POSITIVE_INFINITY;

    thumbs.forEach((thumb) => {
        const rect = thumb.getBoundingClientRect();
        let distancia = Number.POSITIVE_INFINITY;

        if (mobile) {
            if (rect.right < paneRect.left || rect.left > paneRect.right) {
                return;
            }
            const referenciaX = paneRect.left + (paneRect.width / 2);
            const centroX = rect.left + (rect.width / 2);
            distancia = Math.abs(referenciaX - centroX);
        } else {
            if (rect.bottom < paneRect.top || rect.top > paneRect.bottom) {
                return;
            }
            const referenciaY = paneRect.top + Math.min(140, paneRect.height * 0.35);
            const dentroDaFaixa = referenciaY >= rect.top && referenciaY <= rect.bottom;
            distancia = dentroDaFaixa
                ? 0
                : Math.min(Math.abs(referenciaY - rect.top), Math.abs(referenciaY - rect.bottom));
        }

        if (distancia < menorDistancia) {
            menorDistancia = distancia;
            folhaDetectada = Number(thumb.dataset.folha) || folhaDetectada;
        }
    });

    if (folhaDetectada !== folhaAtual) {
        folhaAtual = folhaDetectada;
        atualizarContador();
        atualizarDestaqueFolha();
    }
}

function reagirScrollPreview() {
    if (previewScrollRaf) {
        return;
    }
    previewScrollRaf = requestAnimationFrame(() => {
        previewScrollRaf = null;
        atualizarFolhaAtualPorScroll();
    });
}

async function renderFolha() {
    const container = el("previewContainer");
    container.innerHTML = "";
    const isMobile = isPreviewMobile();
    container.classList.toggle("is-carousel", isMobile);
    container.classList.toggle("is-desktop-focus", !isMobile);
    atualizarModoNavegacaoPreview(isMobile);

    if (!pdfDoc) {
        mostrarPreviewVazio(obterMensagemPreviewVazio());
        return;
    }

    let paginasSelecionadas;
    try {
        paginasSelecionadas = obterPaginasSelecionadas();
    } catch (err) {
        el("intervaloInfo").innerText = err.message;
        mostrarPreviewVazio("Corrija o intervalo para visualizar as folhas.");
        return;
    }

    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const orientacao = obterOrientacaoPreview();
    const configLayout = obterConfigLayout(paginasPorFolha, orientacao);
    const tamanhoFolha = TAMANHO_FOLHA[orientacao];
    const paginasPreview = obterPaginasPreview();
    const paginasSelecionadasSet = new Set(paginasSelecionadas);
    const totalFolhas = Math.max(1, Math.ceil(paginasPreview.length / paginasPorFolha));

    if (folhaAtual > totalFolhas) {
        folhaAtual = totalFolhas;
    }

    const folhasParaRenderizar = Array.from({ length: totalFolhas }, (_, i) => i + 1);
    let tamanhoMiniatura = obterDimensoesMiniatura(tamanhoFolha, isMobile);
    const previewPane = document.querySelector(".print-preview-pane");
    let tamanhoPrincipal = tamanhoMiniatura;

    if (!isMobile) {
        const larguraPane = Math.max(320, previewPane?.clientWidth || 640);
        const alturaPane = Math.max(320, previewPane?.clientHeight || 640);
        const larguraTrilha = Math.min(132, Math.max(92, Math.round(larguraPane * 0.2)));
        tamanhoMiniatura = obterDimensoesMiniaturaDesktop(tamanhoFolha, larguraTrilha);
        const larguraPrincipalDisponivel = Math.max(220, larguraPane - larguraTrilha - 28);
        const alturaPrincipalDisponivel = Math.max(260, alturaPane - 20);
        const escalaPrincipal = Math.min(
            larguraPrincipalDisponivel / tamanhoFolha.largura,
            alturaPrincipalDisponivel / tamanhoFolha.altura
        );

        tamanhoPrincipal = {
            largura: Math.max(220, Math.round(tamanhoFolha.largura * escalaPrincipal)),
            altura: Math.max(260, Math.round(tamanhoFolha.altura * escalaPrincipal)),
        };
    }

    const areaLargura = tamanhoMiniatura.largura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.colunas - 1));
    const areaAltura = tamanhoMiniatura.altura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.linhas - 1));
    const larguraCelula = areaLargura / configLayout.colunas;
    const alturaCelula = areaAltura / configLayout.linhas;
    const areaPrincipalLargura = tamanhoPrincipal.largura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.colunas - 1));
    const areaPrincipalAltura = tamanhoPrincipal.altura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.linhas - 1));
    const larguraCelulaPrincipal = areaPrincipalLargura / configLayout.colunas;
    const alturaCelulaPrincipal = areaPrincipalAltura / configLayout.linhas;
    const dpr = Math.min(window.devicePixelRatio || 1, QUALIDADE_MAX_DPR);
    const token = ++renderTokenAtual;
    let faixaMiniaturas = null;
    let painelPrincipal = null;

    if (!isMobile) {
        painelPrincipal = document.createElement("section");
        painelPrincipal.classList.add("print-preview-featured");
        faixaMiniaturas = document.createElement("section");
        faixaMiniaturas.classList.add("print-preview-thumbs");
        container.appendChild(painelPrincipal);
        container.appendChild(faixaMiniaturas);
    }

    for (const indiceFolha of folhasParaRenderizar) {
        if (token !== renderTokenAtual) {
            return;
        }

        const inicio = (indiceFolha - 1) * paginasPorFolha;
        const paginasDaFolha = expandirPaginasParaFolha(
            paginasPreview.slice(inicio, inicio + paginasPorFolha),
            paginasPorFolha
        );

        const thumb = document.createElement("article");
        thumb.classList.add("print-sheet-thumb");
        thumb.dataset.folha = String(indiceFolha);
        thumb.dataset.sheetLabel = `Folha ${indiceFolha} de ${totalFolhas}`;
        if (indiceFolha === folhaAtual) {
            thumb.classList.add("is-active");
        }
        thumb.addEventListener("click", () => irParaFolha(indiceFolha));

        const folha = document.createElement("div");
        folha.classList.add("print-sheet");
        folha.style.display = "grid";
        folha.style.gap = `${FOLHA_GAP}px`;
        folha.style.padding = `${FOLHA_PADDING}px`;
        const tamanhoBase = !isMobile && indiceFolha === folhaAtual ? tamanhoPrincipal : tamanhoMiniatura;
        const larguraCelulaAtual = !isMobile && indiceFolha === folhaAtual ? larguraCelulaPrincipal : larguraCelula;
        const alturaCelulaAtual = !isMobile && indiceFolha === folhaAtual ? alturaCelulaPrincipal : alturaCelula;
        folha.style.width = `${tamanhoBase.largura}px`;
        folha.style.height = `${tamanhoBase.altura}px`;
        folha.style.gridTemplateColumns = `repeat(${configLayout.colunas}, minmax(0, 1fr))`;
        folha.style.gridTemplateRows = `repeat(${configLayout.linhas}, minmax(0, 1fr))`;

        thumb.appendChild(folha);

        if (isMobile) {
            container.appendChild(thumb);
        } else if (indiceFolha === folhaAtual) {
            painelPrincipal.appendChild(thumb);
        } else {
            faixaMiniaturas.appendChild(thumb);
        }

        for (const numeroPagina of paginasDaFolha) {
            if (token !== renderTokenAtual) {
                return;
            }

            const page = await pdfDoc.getPage(numeroPagina);
            const viewportBase = page.getViewport({ scale: 1 });
            const escalaAjuste = Math.min(
                larguraCelulaAtual / viewportBase.width,
                alturaCelulaAtual / viewportBase.height
            );
            const escalaRender = escalaAjuste * dpr;
            const viewport = page.getViewport({ scale: escalaRender });

            const wrapper = document.createElement("div");
            wrapper.classList.add("preview-cell");
            wrapper.dataset.page = String(numeroPagina);
            wrapper.dataset.pageLabel = `Pg ${numeroPagina}`;

            const paginaSelecionada = paginasSelecionadasSet.has(numeroPagina);

            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");

            canvas.width = Math.floor(viewport.width);
            canvas.height = Math.floor(viewport.height);
            canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
            canvas.style.height = `${Math.floor(viewport.height / dpr)}px`;
            canvas.style.maxWidth = "100%";
            canvas.style.maxHeight = "100%";
            aplicarEstadoSelecaoWrapper(wrapper, paginaSelecionada, numeroPagina);

            wrapper.appendChild(canvas);
            folha.appendChild(wrapper);

            wrapper.addEventListener("click", (event) => {
                event.stopPropagation();
                alternarSelecaoPagina(numeroPagina);
            });

            await page.render({
                canvasContext: ctx,
                viewport
            }).promise;
        }

        for (let i = paginasDaFolha.length; i < paginasPorFolha; i++) {
            const vazio = document.createElement("div");
            vazio.classList.add("preview-cell");
            vazio.style.border = "1px dashed #d1d5db";
            vazio.style.background = "#f8fafc";
            folha.appendChild(vazio);
        }
    }

    atualizarContador();
    atualizarDestaqueFolha();
    if (isMobile) {
        centralizarFolhaAtiva(false);
    }
}

function proximaFolha() {
    if (!pdfDoc) {
        return;
    }
    irParaFolha(folhaAtual + 1);
}

function folhaAnterior() {
    if (!pdfDoc) {
        return;
    }
    irParaFolha(folhaAtual - 1);
}

function atualizarEstadoDropzoneArraste(ativo) {
    const dropzone = el("arquivoDropzone");
    if (!dropzone) {
        return;
    }
    dropzone.classList.toggle("is-drag-over", Boolean(ativo));
}

async function lidarArquivoColado(event) {
    const arquivo = obterArquivoTransferido(event?.clipboardData);
    if (!arquivo) {
        return;
    }

    event.preventDefault();
    await selecionarArquivoParaImpressao(
        arquivo,
        "Arquivo colado da area de transferencia."
    );
}

async function lidarArquivoSolto(event) {
    if (!dataTransferTemArquivo(event?.dataTransfer)) {
        return;
    }

    event.preventDefault();
    atualizarEstadoDropzoneArraste(false);
    await selecionarArquivoParaImpressao(
        obterArquivoTransferido(event.dataTransfer),
        "Arquivo adicionado por arrastar e soltar."
    );
}

function reagendarRenderAposResize() {
    if (resizeTimer) {
        clearTimeout(resizeTimer);
    }
    resizeTimer = setTimeout(() => {
        const larguraAtual = window.innerWidth || 0;
        const alturaAtual = window.innerHeight || 0;
        const mobileAtual = isPreviewMobile();
        const breakpointMudou = mobileAtual !== ultimaGeometriaPreview.mobile;
        const larguraMudou = mobileAtual
            ? Math.abs(larguraAtual - ultimaGeometriaPreview.larguraJanela) >= LIMIAR_RE_RENDER_PREVIEW_MOBILE_PX
            : larguraAtual !== ultimaGeometriaPreview.larguraJanela;
        const alturaMudou = mobileAtual
            ? Math.abs(alturaAtual - ultimaGeometriaPreview.alturaJanela) >= LIMIAR_RE_RENDER_PREVIEW_MOBILE_PX
            : alturaAtual !== ultimaGeometriaPreview.alturaJanela;

        ultimaGeometriaPreview = {
            larguraJanela: larguraAtual,
            alturaJanela: alturaAtual,
            mobile: mobileAtual,
        };

        ajustarPosicaoPainelMeta();

        const deveRenderizarPreview = breakpointMudou || (mobileAtual ? larguraMudou : (larguraMudou || alturaMudou));
        if (!deveRenderizarPreview) {
            return;
        }

        if (!pdfDoc) {
            mostrarPreviewVazio(obterMensagemPreviewVazio());
            return;
        }
        renderFolha();
    }, 120);
}

function registrarEventos() {
    const previewPane = document.querySelector(".print-preview-pane");
    const inputArquivo = el("arquivo");
    const dropzoneArquivo = el("arquivoDropzone");
    ajustarPosicaoPainelMeta();

    if (inputArquivo) {
        inputArquivo.addEventListener("change", async (e) => {
            const file = e.target.files?.[0];
            if (!file) {
                return;
            }

            try {
                await selecionarArquivoParaImpressao(file);
            } catch (err) {
                el("msg").innerText = err?.message || "Falha ao carregar o arquivo.";
            }
        });
    }

    if (dropzoneArquivo) {
        dropzoneArquivo.addEventListener("click", () => {
            inputArquivo?.click();
        });
        dropzoneArquivo.addEventListener("dragenter", (event) => {
            if (!dataTransferTemArquivo(event.dataTransfer)) {
                return;
            }
            event.preventDefault();
            atualizarEstadoDropzoneArraste(true);
        });
        dropzoneArquivo.addEventListener("dragover", (event) => {
            if (!dataTransferTemArquivo(event.dataTransfer)) {
                return;
            }
            event.preventDefault();
            atualizarEstadoDropzoneArraste(true);
        });
        dropzoneArquivo.addEventListener("dragleave", (event) => {
            if (dropzoneArquivo.contains(event.relatedTarget)) {
                return;
            }
            atualizarEstadoDropzoneArraste(false);
        });
        dropzoneArquivo.addEventListener("drop", (event) => {
            lidarArquivoSolto(event).catch((err) => {
                el("msg").innerText = err?.message || "Falha ao processar o arquivo solto.";
            });
        });
    }

    window.addEventListener("paste", (event) => {
        lidarArquivoColado(event).catch((err) => {
            el("msg").innerText = err?.message || "Falha ao colar o arquivo.";
        });
    });
    window.addEventListener("dragover", (event) => {
        if (!dataTransferTemArquivo(event.dataTransfer)) {
            return;
        }
        event.preventDefault();
    });
    window.addEventListener("drop", (event) => {
        if (!dataTransferTemArquivo(event.dataTransfer)) {
            return;
        }
        if (dropzoneArquivo && dropzoneArquivo.contains(event.target)) {
            return;
        }
        event.preventDefault();
        atualizarEstadoDropzoneArraste(false);
    });

    el("orientacao").addEventListener("change", atualizarPreview);
    el("copias").addEventListener("input", () => {
        atualizarResumoTurmaImpressao();
        calcularConsumo();
    });
    el("turmaImpressao").addEventListener("change", aplicarTurmaImpressaoSelecionada);
    el("duplex").addEventListener("change", atualizarPreview);
    el("paginasPorFolha").addEventListener("change", () => {
        folhaAtual = 1;
        atualizarPreview();
    });
    el("intervaloPaginas").addEventListener("input", () => {
        if (pdfDoc) {
            folhaAtual = 1;
            atualizarPreview();
            return;
        }
        calcularConsumo();
    });
    const tagsImpressao = el("tagsImpressao");
    if (tagsImpressao) {
        tagsImpressao.addEventListener("change", (event) => {
            if (event.target instanceof HTMLInputElement && event.target.type === "checkbox") {
                atualizarContadorTagsImpressao();
            }
        });
    }
    const modalAlertaConsumo = el("modalAlertaConsumoImpressao");
    if (modalAlertaConsumo) {
        modalAlertaConsumo.addEventListener("click", (event) => {
            if (event.target === modalAlertaConsumo) {
                fecharModalAlertaConsumo(false);
            }
        });
    }
    const modalSemPapel = el("modalSemPapelImpressao");
    if (modalSemPapel) {
        modalSemPapel.addEventListener("click", (event) => {
            if (event.target === modalSemPapel) {
                modalSemPapel.hidden = true;
                document.body.classList.remove("print-alert-modal-open");
            }
        });
    }
    el("btnConfirmarAlertaConsumoImpressao")?.addEventListener("click", () => {
        fecharModalAlertaConsumo(true);
    });
    el("btnVoltarAjustarAlertaConsumoImpressao")?.addEventListener("click", () => {
        fecharModalAlertaConsumo(false);
    });
    el("btnFecharModalSemPapelImpressao")?.addEventListener("click", () => {
        el("modalSemPapelImpressao").hidden = true;
        document.body.classList.remove("print-alert-modal-open");
    });
    el("btnEnviar").addEventListener("click", () => {
        enviarImpressao(false);
    });
    el("btnAnterior").addEventListener("click", folhaAnterior);
    el("btnProxima").addEventListener("click", proximaFolha);
    window.addEventListener("resize", reagendarRenderAposResize);
    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && modalAlertaConsumoAberto()) {
            fecharModalAlertaConsumo(false);
            return;
        }
        if (event.key === "Escape" && !el("modalSemPapelImpressao")?.hidden) {
            el("modalSemPapelImpressao").hidden = true;
            document.body.classList.remove("print-alert-modal-open");
        }
    });

    const professorSolicitante = el("professorSolicitante");
    if (professorSolicitante) {
        professorSolicitante.addEventListener("change", async () => {
            const professorAnteriorId = Number(professorSolicitante.dataset.previousProfessorId || 0);
            const professorAtualId = obterProfessorSolicitanteSelecionadoId();
            professorSolicitante.dataset.previousProfessorId = String(professorAtualId || 0);
            atualizarTitulosContextoImpressao();
            el("msg").innerText = "";

            try {
                if (
                    professorAnteriorId !== professorAtualId
                    && Number(jobHistoricoSelecionadoAtual?.id || 0) > 0
                ) {
                    await carregarPreview(null);
                }
                await carregarCota();
                await carregarFila();
            } catch (err) {
                el("msg").innerText = err?.message || "Falha ao atualizar o professor solicitante.";
            }
        });
    }

    if (previewPane) {
        previewPane.addEventListener("scroll", reagirScrollPreview, { passive: true });
    }

    const btnVoltarServicos = el("btnVoltarServicos");
    const btnIrAgendamento = el("btnIrAgendamento");
    const btnSair = el("btnSair");

    if (btnVoltarServicos) {
        btnVoltarServicos.addEventListener("click", () => {
            window.location.href = "/servicos";
        });
    }

    if (btnIrAgendamento) {
        btnIrAgendamento.addEventListener("click", () => {
            window.location.href = "/agendamento";
        });
    }

    if (btnSair) {
        btnSair.addEventListener("click", () => {
            encerrarSessao();
        });
    }
}

function definirTextoResumoPadrao() {
    definirTexto("resumoArquivo", "Aguardando arquivo");
    definirTexto("resumoProfessor", "Sera preenchido automaticamente");
    definirTexto("resumoTurma", "Nao selecionada");
    definirTexto("resumoCopias", "1");
    definirTexto("resumoPaginas", "Todas");
    definirTexto("resumoPaginasEstimadas", "Aguardando preview");
    definirTexto("resumoLayout", "1 pagina por folha");
    definirTexto("resumoOrientacao", "Retrato");
    definirTexto("resumoDuplex", "Nao");
    definirTexto("resumoTags", "Nenhuma tag selecionada");
    definirTexto("resumoArquivoBarra", "Arquivo: -");
}

function possuiArquivoNoFluxo() {
    return Boolean(
        obterArquivoSelecionado()
        || Number(jobHistoricoSelecionadoAtual?.id || 0) > 0
        || reusoHistoricoEmCarregamento
    );
}

function definirTexto(elementId, texto) {
    const elemento = el(elementId);
    if (elemento) {
        elemento.innerText = texto;
    }
}

function obterTextoProfessorResumo() {
    const professorSelecionado = obterProfessorSelecionado();
    if (professorSelecionado?.nome) {
        return professorSelecionado.nome;
    }

    const usuario = usuarioAtual?.nome || usuarioAtual?.username || "";
    return usuario || "Sera definido no envio";
}

function obterTextoTurmaResumo() {
    const turma = obterTurmaImpressaoSelecionada();
    if (!turma) {
        return "Nao selecionada";
    }

    const quantidade = obterQuantidadeCopiasTurma(turma);
    return quantidade > 0 ? `${turma.nome} (${quantidade} estudante(s))` : turma.nome;
}

function obterTextoPaginasResumo() {
    if (!pdfDoc) {
        return previewEmCarregamento ? "Gerando preview" : "Aguardando preview";
    }

    try {
        const paginas = obterPaginasSelecionadas();
        if (paginas.length === pdfDoc.numPages) {
            return `Todas (${pdfDoc.numPages})`;
        }
        return gerarIntervaloApartirPaginas(paginas, pdfDoc.numPages) || `Todas (${pdfDoc.numPages})`;
    } catch (_err) {
        return "Intervalo invalido";
    }
}

function obterEstadoValidacaoImpressao() {
    const arquivo = obterArquivoSelecionado();
    const usaHistorico = Number(jobHistoricoSelecionadoAtual?.id || 0) > 0;
    const copias = Number(el("copias")?.value || 0);
    const tagsSelecionadas = obterTagsImpressaoSelecionadas();

    if (professorSolicitantePendente()) {
        return { valido: false, mensagem: "Selecione o professor solicitante para liberar as proximas etapas." };
    }

    if ((!arquivo && !usaHistorico) || copias < 1) {
        return { valido: false, mensagem: "Selecione um arquivo e informe uma quantidade valida de copias." };
    }

    if (arquivo && !arquivoSuportado(arquivo)) {
        return { valido: false, mensagem: "Formato nao suportado. Use PDF, DOCX, DOC, PNG, JPG ou JPEG." };
    }

    if (previewEmCarregamento) {
        return { valido: false, mensagem: "Aguarde a pre-visualizacao terminar para validar a solicitacao." };
    }

    if (!usaHistorico && arquivo && !pdfDoc) {
        return { valido: false, mensagem: "A pre-visualizacao ainda nao esta disponivel." };
    }

    if (tagsSelecionadas.length === 0) {
        return { valido: false, mensagem: "Selecione ao menos uma tag para liberar o envio." };
    }

    if (pdfDoc) {
        try {
            const paginasSelecionadas = obterPaginasSelecionadas();
            if (paginasSelecionadas.length === 0) {
                return { valido: false, mensagem: "Mantenha ao menos uma pagina selecionada." };
            }
        } catch (err) {
            return { valido: false, mensagem: err.message || "Revise o intervalo informado." };
        }
    }

    return { valido: true, mensagem: "Resumo pronto para confirmar a impressao." };
}

function atualizarResumoImpressaoPainel(resumoImpressao = calcularResumoImpressao()) {
    const arquivo = obterArquivoSelecionado();
    const paginasPorFolha = Number(el("paginasPorFolha")?.value || 1);

    if (!arquivo && !previewEmCarregamento) {
        definirTextoResumoPadrao();
        return;
    }

    definirTexto("resumoArquivo", arquivo?.name || "Aguardando arquivo");
    definirTexto("resumoProfessor", obterTextoProfessorResumo());
    definirTexto("resumoTurma", obterTextoTurmaResumo());
    definirTexto("resumoCopias", String(Math.max(1, Number(el("copias")?.value || 1))));
    definirTexto("resumoPaginas", obterTextoPaginasResumo());
    definirTexto("resumoArquivoBarra", `Arquivo: ${arquivo?.name || "-"}`);
    definirTexto(
        "resumoPaginasEstimadas",
        resumoImpressao
            ? `${resumoImpressao.consumo} ${resumoImpressao.consumo === 1 ? "folha estimada" : "folhas estimadas"}`
            : (previewEmCarregamento ? "Calculando..." : "Aguardando preview")
    );
    definirTexto(
        "resumoLayout",
        `${paginasPorFolha} ${paginasPorFolha === 1 ? "página" : "páginas"} por folha | ${el("orientacao")?.value || "retrato"} | ${el("duplex")?.checked ? "frente e verso" : "somente frente"}`
    );
    definirTexto(
        "resumoOrientacao",
        (el("orientacao")?.value || "retrato") === "paisagem" ? "Paisagem" : "Retrato"
    );
}

function sincronizarEstadoAcaoEnvio(mensagem = "") {
    const botao = el("btnEnviar");
    const estado = el("estadoEnvio");
    if (!botao || !estado) {
        return;
    }

    if (!botao.dataset.labelPadrao) {
        botao.dataset.labelPadrao = botao.innerText || "Confirmar impressao";
    }

    const bloqueado = impressaoBloqueadaSemPapel();
    const validacao = obterEstadoValidacaoImpressao();
    const deveMostrarValidacao = possuiArquivoNoFluxo() || previewEmCarregamento;
    const mensagemFinal = mensagem
        || (bloqueado
            ? obterMensagemSemPapel()
            : (deveMostrarValidacao ? validacao.mensagem : ""));

    botao.disabled = envioEmAndamento || bloqueado || !validacao.valido;
    botao.classList.toggle("is-loading", envioEmAndamento);
    botao.setAttribute("aria-busy", envioEmAndamento ? "true" : "false");
    botao.innerText = envioEmAndamento
        ? "Enviando..."
        : (bloqueado ? "Impressao indisponivel" : botao.dataset.labelPadrao);

    estado.classList.toggle("is-active", Boolean(mensagemFinal));
    estado.innerText = mensagemFinal;
}

function atualizarEstadoFluxoImpressao() {
    const resumoImpressao = calcularResumoImpressao();
    atualizarResumoImpressaoPainel(resumoImpressao);
    sincronizarEstadoAcaoEnvio(envioEmAndamento ? "Enviando..." : "");
    const btnAbrirPreviewMobile = el("btnAbrirPreviewMobile");
    if (btnAbrirPreviewMobile) {
        btnAbrirPreviewMobile.disabled = !pdfDoc || previewEmCarregamento;
    }

    const deveFixarEtapaSolicitacao = isPreviewMobile()
        && (reusoHistoricoEmCarregamento || Number(jobHistoricoSelecionadoAtual?.id || 0) > 0);

    window.PrintingUI?.ui?.syncFromLegacyDom?.({
        upload: {
            fileName: obterArquivoSelecionado()?.name || "",
            valid: possuiArquivoNoFluxo(),
            source: Number(jobHistoricoSelecionadoAtual?.id || 0) > 0 ? "history" : null,
            loading: reusoHistoricoEmCarregamento,
        },
        settings: {
            pageMode: document.querySelector("input[name='modoPaginas']:checked")?.value === "custom"
                ? "custom"
                : "all",
        },
        preview: {
            loading: previewEmCarregamento,
            ready: Boolean(pdfDoc),
            visible: document.body.classList.contains("print-preview-modal-open"),
        },
        submit: {
            sending: envioEmAndamento,
        },
        wizard: deveFixarEtapaSolicitacao
            ? {
                currentStep: 2,
            }
            : undefined,
    });
}

function abrirPainelHistorico() {
    const drawer = el("painelHistoricoImpressao");
    if (!drawer) {
        return;
    }
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("print-history-open");
}

function fecharPainelHistorico() {
    const drawer = el("painelHistoricoImpressao");
    if (!drawer) {
        return;
    }
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("print-history-open");
}

function abrirPreviewMobile() {
    if (isPreviewMobile()) {
        document.body.classList.add("print-preview-modal-open");
        window.requestAnimationFrame(() => {
            if (pdfDoc) {
                renderFolha();
                return;
            }
            mostrarPreviewVazio(obterMensagemPreviewVazio());
        });
    }
}

function fecharPreviewMobile() {
    document.body.classList.remove("print-preview-modal-open");
}

const ajustarPosicaoPainelMetaOriginal = ajustarPosicaoPainelMeta;
ajustarPosicaoPainelMeta = function ajustarPosicaoPainelMetaRefatorado() {
    return undefined;
};

const atualizarEstadoArquivoSelecionadoOriginal = atualizarEstadoArquivoSelecionado;
atualizarEstadoArquivoSelecionado = function atualizarEstadoArquivoSelecionadoRefatorado() {
    atualizarEstadoArquivoSelecionadoOriginal();
    atualizarEstadoFluxoImpressao();
};

const atualizarContadorTagsImpressaoOriginal = atualizarContadorTagsImpressao;
atualizarContadorTagsImpressao = function atualizarContadorTagsImpressaoRefatorado() {
    atualizarContadorTagsImpressaoOriginal();
    atualizarEstadoFluxoImpressao();
};

const aplicarTagsImpressaoSelecionadasOriginal = aplicarTagsImpressaoSelecionadas;
aplicarTagsImpressaoSelecionadas = function aplicarTagsImpressaoSelecionadasRefatorado(tags = []) {
    aplicarTagsImpressaoSelecionadasOriginal(tags);
    atualizarEstadoFluxoImpressao();
};

const mostrarPreviewVazioOriginal = mostrarPreviewVazio;
mostrarPreviewVazio = function mostrarPreviewVazioRefatorado(texto = obterMensagemPreviewVazio()) {
    mostrarPreviewVazioOriginal(texto);
    atualizarEstadoFluxoImpressao();
};

const calcularConsumoOriginal = calcularConsumo;
calcularConsumo = function calcularConsumoRefatorado() {
    const consumo = calcularConsumoOriginal();
    atualizarEstadoFluxoImpressao();
    return consumo;
};

const carregarDocumentoPdfNoPreviewOriginal = carregarDocumentoPdfNoPreview;
carregarDocumentoPdfNoPreview = async function carregarDocumentoPdfNoPreviewRefatorado(arrayBuffer, cargaAtual) {
    await carregarDocumentoPdfNoPreviewOriginal(arrayBuffer, cargaAtual);
    atualizarEstadoFluxoImpressao();
};

const selecionarArquivoParaImpressaoOriginal = selecionarArquivoParaImpressao;
selecionarArquivoParaImpressao = async function selecionarArquivoParaImpressaoRefatorado(file, mensagemSucesso = "") {
    window.PrintingUI?.ui?.setForcedStep?.(null);
    const resultado = await selecionarArquivoParaImpressaoOriginal(file, mensagemSucesso);
    atualizarEstadoFluxoImpressao();
    if (resultado && isPreviewMobile()) {
        window.PrintingUI?.ui?.goToStep?.(2);
    }
    return resultado;
};

const carregarJobHistoricoNoPreviewOriginal = carregarJobHistoricoNoPreview;
carregarJobHistoricoNoPreview = async function carregarJobHistoricoNoPreviewRefatorado(job) {
    const deveAvancarNoMobile = isPreviewMobile();
    reusoHistoricoEmCarregamento = true;
    fecharPainelHistorico();
    if (deveAvancarNoMobile) {
        window.PrintingUI?.ui?.setForcedStep?.(2);
        window.PrintingUI?.ui?.setWizardState?.(2, {
            upload: {
                fileName: String(job?.arquivo || ""),
                valid: true,
                source: "history",
                loading: true,
            },
        });
    }

    let historicoCarregado = false;
    try {
        await carregarJobHistoricoNoPreviewOriginal(job);
        historicoCarregado = Boolean(
            pdfDoc
            && Number(jobHistoricoSelecionadoAtual?.id || 0) === Number(job?.id || 0)
        );
    } finally {
        reusoHistoricoEmCarregamento = false;
        window.PrintingUI?.ui?.setForcedStep?.(null);
        atualizarEstadoFluxoImpressao();
    }

    if (historicoCarregado) {
        window.PrintingUI?.ui?.setWizardState?.(2, {
            upload: {
                fileName: String(job?.arquivo || obterArquivoSelecionado()?.name || ""),
                valid: true,
                source: "history",
                loading: false,
            },
        });
        window.PrintingUI?.ui?.goToStep?.(2);
    }
};

const carregarCotaOriginal = carregarCota;
carregarCota = async function carregarCotaRefatorado() {
    await carregarCotaOriginal();
    atualizarEspelhosCotaImpressao(el("cota")?.innerText || "Carregando...");
    atualizarEstadoFluxoImpressao();
};

atualizarEstadoEnvio = function atualizarEstadoEnvioRefatorado(ativo, mensagem = "") {
    envioEmAndamento = Boolean(ativo);
    sincronizarEstadoAcaoEnvio(mensagem);
};

const registrarEventosOriginal = registrarEventos;
registrarEventos = function registrarEventosRefatorado() {
    registrarEventosOriginal();

    [
        "btnAbrirHistorico",
        "btnAbrirHistoricoTopbar",
        "btnAbrirHistoricoMobile",
        "btnAbrirHistoricoResumo",
    ].forEach((id) => {
        el(id)?.addEventListener("click", abrirPainelHistorico);
    });

    el("btnFecharHistorico")?.addEventListener("click", fecharPainelHistorico);
    document.querySelector("[data-close-history='true']")?.addEventListener("click", fecharPainelHistorico);
    el("btnAbrirPreviewMobile")?.addEventListener("click", abrirPreviewMobile);
    el("btnImprimirOutroArquivo")?.addEventListener("click", () => {
        imprimirOutroArquivo().catch((err) => {
            el("msg").innerText = err?.message || "Falha ao reiniciar o fluxo de impressao.";
        });
    });

    window.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && document.body.classList.contains("print-history-open")) {
            fecharPainelHistorico();
        }
        if (event.key === "Escape" && document.body.classList.contains("print-preview-modal-open")) {
            fecharPreviewMobile();
        }
    });
};

window.atualizarPreview = atualizarPreview;
window.enviarImpressao = enviarImpressao;
window.proximaFolha = proximaFolha;
window.folhaAnterior = folhaAnterior;
window.obterPaginasSelecionadas = obterPaginasSelecionadas;

async function inicializarPagina() {
    registrarEventos();
    atualizarComportamentoOrientacao();
    atualizarEstadoArquivoSelecionado();
    mostrarPreviewVazio();

    try {
        await carregarUsuario();
        await carregarStatusImpressao(true);
        atualizarTopbarUsuario();
        await carregarProfessoresImpressaoAdmin();
        await carregarTurmasImpressao();
        await carregarTagsImpressao();
        await carregarCota();
        await carregarFila();
    } catch (err) {
        el("msg").innerText = err?.message || "Falha ao carregar os dados da impressao.";
    }

    iniciarPollingFila();
}

inicializarPagina();

window.addEventListener("beforeunload", () => {
    if (filaPollingTimer) {
        clearInterval(filaPollingTimer);
        filaPollingTimer = null;
    }
});
