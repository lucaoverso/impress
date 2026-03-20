const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": "Bearer " + token
};

function encerrarSessao() {
    localStorage.removeItem("token");
    localStorage.removeItem("token_expira_em");
    window.location.href = "/login-page";
}

async function fetchComAuth(url, options = {}) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        encerrarSessao();
        throw new Error("Sessão expirada.");
    }
    return res;
}

async function extrairMensagemErroResposta(res, fallback = "Falha na requisição.") {
    try {
        const data = await res.json();
        if (typeof data?.detail === "string" && data.detail.trim()) {
            return data.detail.trim();
        }
    } catch (_err) {
        // Sem payload JSON legível.
    }
    return fallback;
}

let pdfDoc = null;
let folhaAtual = 1;
let renderTokenAtual = 0;
let resizeTimer = null;
let previewScrollRaf = null;
let previewAbortController = null;
let previewLoadSeq = 0;
let envioEmAndamento = false;
let filaPollingTimer = null;
let usuarioAtual = null;
let professoresImpressao = [];
let arquivoSelecionadoAtual = null;
const QUALIDADE_MAX_DPR = 1.4;
const FOLHA_PADDING = 8;
const FOLHA_GAP = 6;
const LABEL_PREVIEW_RESERVA = 38;
const RESERVA_BORDA_PREVIEW = 24;
const BREAKPOINT_MOBILE_PREVIEW = 980;
const FILA_POLLING_MS = 6000;
const EXTENSOES_SUPORTADAS = new Set(["pdf", "doc", "docx", "png", "jpg", "jpeg"]);
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

function el(id) {
    return document.getElementById(id);
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

function obterProfessorSolicitanteSelecionadoId() {
    return Number(el("professorSolicitante")?.value || 0);
}

function obterProfessorSelecionado() {
    const professorId = obterProfessorSolicitanteSelecionadoId();
    return professoresImpressao.find((professor) => Number(professor.id) === professorId) || null;
}

function adminPrecisaSelecionarProfessor() {
    return usuarioEhAdmin() && !obterProfessorSolicitanteSelecionadoId();
}

function montarUrlConsultaImpressao(urlBase) {
    const professorId = obterProfessorSolicitanteSelecionadoId();
    if (!(usuarioEhAdmin() && professorId > 0)) {
        return urlBase;
    }

    const params = new URLSearchParams({ professor_id: String(professorId) });
    return `${urlBase}?${params.toString()}`;
}

function atualizarTitulosContextoImpressao() {
    const tituloCota = el("tituloCota");
    const tituloJobs = el("tituloJobs");
    const contexto = el("contextoProfessorImpressao");

    if (!tituloCota || !tituloJobs) {
        return;
    }

    if (!usuarioEhAdmin()) {
        tituloCota.innerText = "Sua cota";
        tituloJobs.innerText = "Seus pedidos";
        if (contexto) {
            contexto.innerText = "";
        }
        return;
    }

    const professor = obterProfessorSelecionado();
    tituloCota.innerText = professor ? `Cota de ${professor.nome}` : "Cota do professor";
    tituloJobs.innerText = professor ? `Pedidos de ${professor.nome}` : "Pedidos do professor";

    if (contexto) {
        contexto.innerText = professor
            ? `A impressao sera contabilizada para ${professor.nome}.`
            : "Selecione o professor solicitante para consultar cota, historico e imprimir.";
    }
}

function renderFilaVazia(texto) {
    const ul = el("lista-jobs");
    if (!ul) {
        return;
    }

    ul.innerHTML = "";
    const li = document.createElement("li");
    li.classList.add("print-job-empty");
    li.innerText = texto;
    ul.appendChild(li);
}

async function carregarUsuario() {
    const res = await fetchComAuth("/me", { headers });
    if (!res.ok) {
        throw new Error("Nao foi possivel carregar o usuario.");
    }

    usuarioAtual = await res.json();
    atualizarTitulosContextoImpressao();
}

async function carregarProfessoresImpressaoAdmin() {
    const grupo = el("grupoProfessorSolicitante");
    const select = el("professorSolicitante");

    if (!grupo || !select) {
        return;
    }

    if (!usuarioEhAdmin()) {
        grupo.style.display = "none";
        professoresImpressao = [];
        select.innerHTML = "";
        atualizarTitulosContextoImpressao();
        return;
    }

    grupo.style.display = "block";
    const res = await fetchComAuth("/agendamento/professores", { headers });
    if (!res.ok) {
        throw new Error("Nao foi possivel carregar os professores para impressao.");
    }

    professoresImpressao = await res.json();
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
        atualizarTitulosContextoImpressao();
        return;
    }

    professoresImpressao.forEach((professor) => {
        const option = document.createElement("option");
        option.value = String(professor.id);
        option.innerText = `${professor.nome} (${professor.email})`;
        select.appendChild(option);
    });
    select.disabled = false;
    atualizarTitulosContextoImpressao();
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
            ? `Selecionado: ${arquivo.name}`
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
        // Alguns navegadores nao permitem atribuir FileList manualmente.
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
        el("msg").innerText = "Formato nao suportado. Use PDF, DOCX, DOC, PNG, JPG ou JPEG.";
        return false;
    }

    arquivoSelecionadoAtual = arquivo;
    sincronizarInputArquivo(arquivo);
    atualizarEstadoArquivoSelecionado();

    await carregarPreview(arquivo);
    if (mensagemSucesso && !el("msg").innerText.trim()) {
        el("msg").innerText = mensagemSucesso;
    }
    return true;
}

function arquivoEhPdf(file) {
    return obterExtensaoArquivo(file?.name || "") === "pdf";
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
    paginacao.classList.toggle("is-desktop-scroll", !isMobile);
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
        ? Math.max(120, pane.clientWidth - RESERVA_BORDA_PREVIEW)
        : Math.max(120, window.innerWidth - 56);
    const alturaDisponivelBase = pane
        ? Math.max(120, pane.clientHeight - RESERVA_BORDA_PREVIEW)
        : Math.max(120, Math.floor(window.innerHeight * (isMobile ? 0.36 : 0.5)));

    const alturaDisponivel = isMobile
        ? Math.max(140, alturaDisponivelBase - LABEL_PREVIEW_RESERVA)
        : alturaDisponivelBase;
    const larguraAlvo = isMobile
        ? Math.max(170, larguraDisponivel)
        : larguraDisponivel;
    const escala = Math.min(
        larguraAlvo / tamanhoFolha.largura,
        alturaDisponivel / tamanhoFolha.altura
    );

    return {
        largura: Math.max(96, Math.round(tamanhoFolha.largura * escala)),
        altura: Math.max(130, Math.round(tamanhoFolha.altura * escala))
    };
}

function mostrarPreviewVazio(texto = obterMensagemPreviewVazio()) {
    const container = el("previewContainer");
    container.innerHTML = "";
    const isMobile = isPreviewMobile();
    container.classList.toggle("is-carousel", isMobile);
    container.classList.toggle("is-desktop-scroll", !isMobile);
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
    folhaAtiva.scrollIntoView({
        behavior: suave ? "smooth" : "auto",
        block: isMobile ? "nearest" : "start",
        inline: isMobile ? "center" : "nearest"
    });
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

    const marcador = wrapper.querySelector(".preview-page-tag");
    if (marcador) {
        marcador.innerText = `Pg ${numeroPagina}`;
    }
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

function calcularConsumo() {
    if (!pdfDoc) {
        const arquivo = obterArquivoSelecionado();
        if (arquivo && arquivoSuportado(arquivo) && !el("intervaloInfo").innerText.trim()) {
            el("intervaloInfo").innerText = "Aguardando pré-visualização do documento.";
        }
        el("consumo").innerText = "";
        return 0;
    }

    try {
        const paginasSelecionadas = obterPaginasSelecionadas();
        const copias = Math.max(1, Number(el("copias").value) || 1);
        const paginasPorFolha = Number(el("paginasPorFolha").value);
        const duplex = el("duplex").checked;

        const facesPorCopia = Math.ceil(paginasSelecionadas.length / paginasPorFolha);
        const folhasPorCopia = duplex ? Math.ceil(facesPorCopia / 2) : facesPorCopia;
        const consumo = folhasPorCopia * copias;

        el("consumo").innerText = `Consumo estimado: ${consumo} folha(s)`;
        return consumo;
    } catch (err) {
        el("consumo").innerText = "";
        el("intervaloInfo").innerText = err.message;
        return 0;
    }
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

function atualizarEstadoEnvio(ativo, mensagem = "") {
    const botao = el("btnEnviar");
    const estado = el("estadoEnvio");
    if (!botao || !estado) {
        return;
    }

    if (!botao.dataset.labelPadrao) {
        botao.dataset.labelPadrao = botao.innerText || "Imprimir";
    }

    botao.disabled = ativo;
    botao.classList.toggle("is-loading", ativo);
    botao.setAttribute("aria-busy", ativo ? "true" : "false");
    botao.innerText = ativo ? "Enviando..." : botao.dataset.labelPadrao;

    estado.classList.toggle("is-active", Boolean(mensagem));
    estado.innerText = mensagem || "";
}

async function enviarImpressao() {
    if (envioEmAndamento) {
        return;
    }

    const arquivo = obterArquivoSelecionado();
    const copias = Number(el("copias").value);
    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const duplex = el("duplex").checked;
    const orientacao = obterOrientacaoPreview();
    const intervaloPaginas = el("intervaloPaginas").value.trim();
    const professorSolicitanteId = obterProfessorSolicitanteSelecionadoId();

    if (usuarioEhAdmin() && !professorSolicitanteId) {
        el("msg").innerText = "Selecione o professor solicitante da impressao.";
        return;
    }

    if (!arquivo || !copias || copias < 1) {
        el("msg").innerText = "Selecione um arquivo e informe uma quantidade válida de cópias.";
        return;
    }

    if (!arquivoSuportado(arquivo)) {
        el("msg").innerText = "Formato não suportado. Use PDF, DOCX, DOC, PNG, JPG ou JPEG.";
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

    envioEmAndamento = true;
    atualizarEstadoEnvio(true, "Enviando para fila e validando consumo da cota...");
    el("msg").innerText = "";

    try {
        const formData = new FormData();
        formData.append("arquivo", arquivo);
        formData.append("copias", copias);
        formData.append("paginas_por_folha", paginasPorFolha);
        formData.append("duplex", duplex);
        formData.append("orientacao", orientacao);
        if (intervaloPaginas) {
            formData.append("intervalo_paginas", intervaloPaginas);
        }
        if (professorSolicitanteId > 0) {
            formData.append("professor_id", professorSolicitanteId);
        }

        const res = await fetchComAuth("/imprimir", {
            method: "POST",
            headers,
            body: formData
        });

        const data = await res.json();
        if (!res.ok) {
            el("msg").innerText = data.detail || "Não foi possível enviar a impressão.";
            return;
        }

        const professorSelecionado = obterProfessorSelecionado();
        const sufixoDestino = professorSelecionado ? ` para ${professorSelecionado.nome}` : "";
        el("msg").innerText = `Enviado${sufixoDestino}! Restam ${data.paginas_restantes} páginas`;
        await carregarFila();
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

    if (adminPrecisaSelecionarProfessor()) {
        el("cota").innerText = "Selecione um professor solicitante.";
        return;
    }

    const res = await fetchComAuth(montarUrlConsultaImpressao("/minha-cota"), { headers });
    if (!res.ok) {
        throw new Error(await extrairMensagemErroResposta(res, "Nao foi possivel carregar a cota."));
    }

    const data = await res.json();
    el("cota").innerText = `Restante: ${data.restante} páginas`;
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
        const data = await res.json();

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

function criarItemJob(job) {
    const li = document.createElement("li");
    li.classList.add("print-job-item");

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

    if (job?.erro_mensagem) {
        const erro = document.createElement("p");
        erro.classList.add("print-job-error");
        erro.innerText = String(job.erro_mensagem);
        li.appendChild(erro);
    }

    if (jobPodeSerCancelado(job)) {
        const acoes = document.createElement("div");
        acoes.classList.add("print-job-actions");

        const btnCancelar = document.createElement("button");
        btnCancelar.type = "button";
        btnCancelar.classList.add("print-job-cancel-btn");
        btnCancelar.innerText = "Cancelar";
        btnCancelar.addEventListener("click", () => cancelarJobProfessor(job.id, btnCancelar));

        acoes.appendChild(btnCancelar);
        li.appendChild(acoes);
    }

    return li;
}

async function carregarFila() {
    atualizarTitulosContextoImpressao();

    if (adminPrecisaSelecionarProfessor()) {
        renderFilaVazia("Selecione um professor solicitante para ver os pedidos.");
        return;
    }

    const res = await fetchComAuth(montarUrlConsultaImpressao("/meus-jobs"), { headers });
    if (!res.ok) {
        throw new Error(await extrairMensagemErroResposta(res, "Nao foi possivel carregar os pedidos de impressao."));
    }

    const jobs = await res.json();

    const ul = el("lista-jobs");
    ul.innerHTML = "";

    if (!Array.isArray(jobs) || jobs.length === 0) {
        const professorSelecionado = obterProfessorSelecionado();
        renderFilaVazia(
            professorSelecionado
                ? `Nenhuma impressão enviada por ${professorSelecionado.nome} até o momento.`
                : "Nenhuma impressão enviada até o momento."
        );
        return;
    }

    jobs.forEach((job) => {
        ul.appendChild(criarItemJob(job));
    });
}

function iniciarPollingFila() {
    if (filaPollingTimer) {
        clearInterval(filaPollingTimer);
    }

    filaPollingTimer = window.setInterval(() => {
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
        arquivoSelecionadoAtual = null;
        sincronizarInputArquivo(null);
        atualizarEstadoArquivoSelecionado();
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
        arquivoSelecionadoAtual = null;
        sincronizarInputArquivo(null);
        atualizarEstadoArquivoSelecionado();
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
                const detalhe = await extrairMensagemErroResposta(
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

        pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        if (cargaAtual !== previewLoadSeq) {
            return;
        }
        folhaAtual = 1;
        el("intervaloInfo").innerText = "";
        atualizarPreview();
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
    return Math.max(1, Math.ceil(pdfDoc.numPages / paginasPorFolha));
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
    container.classList.toggle("is-desktop-scroll", !isMobile);
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
    const paginasPreview = Array.from({ length: pdfDoc.numPages }, (_, i) => i + 1);
    const paginasSelecionadasSet = new Set(paginasSelecionadas);
    const totalFolhas = Math.max(1, Math.ceil(paginasPreview.length / paginasPorFolha));

    if (folhaAtual > totalFolhas) {
        folhaAtual = totalFolhas;
    }

    const folhasParaRenderizar = Array.from({ length: totalFolhas }, (_, i) => i + 1);
    const tamanhoMiniatura = obterDimensoesMiniatura(tamanhoFolha, isMobile);

    const areaLargura = tamanhoMiniatura.largura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.colunas - 1));
    const areaAltura = tamanhoMiniatura.altura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.linhas - 1));
    const larguraCelula = areaLargura / configLayout.colunas;
    const alturaCelula = areaAltura / configLayout.linhas;
    const dpr = Math.min(window.devicePixelRatio || 1, QUALIDADE_MAX_DPR);
    const token = ++renderTokenAtual;

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
        if (indiceFolha === folhaAtual) {
            thumb.classList.add("is-active");
        }
        if (isMobile) {
            thumb.addEventListener("click", () => irParaFolha(indiceFolha));
        }

        const folha = document.createElement("div");
        folha.classList.add("print-sheet");
        folha.style.display = "grid";
        folha.style.gap = `${FOLHA_GAP}px`;
        folha.style.padding = `${FOLHA_PADDING}px`;
        folha.style.width = `${tamanhoMiniatura.largura}px`;
        folha.style.height = `${tamanhoMiniatura.altura}px`;
        folha.style.gridTemplateColumns = `repeat(${configLayout.colunas}, minmax(0, 1fr))`;
        folha.style.gridTemplateRows = `repeat(${configLayout.linhas}, minmax(0, 1fr))`;

        thumb.appendChild(folha);

        const label = document.createElement("p");
        label.classList.add("sheet-label");
        label.innerText = `Folha ${indiceFolha} de ${totalFolhas}`;
        thumb.appendChild(label);

        container.appendChild(thumb);

        for (const numeroPagina of paginasDaFolha) {
            if (token !== renderTokenAtual) {
                return;
            }

            const page = await pdfDoc.getPage(numeroPagina);
            const viewportBase = page.getViewport({ scale: 1 });
            const escalaAjuste = Math.min(
                larguraCelula / viewportBase.width,
                alturaCelula / viewportBase.height
            );
            const escalaRender = escalaAjuste * dpr;
            const viewport = page.getViewport({ scale: escalaRender });

            const wrapper = document.createElement("div");
            wrapper.classList.add("preview-cell");
            wrapper.dataset.page = String(numeroPagina);

            const paginaSelecionada = paginasSelecionadasSet.has(numeroPagina);

            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");

            canvas.width = Math.floor(viewport.width);
            canvas.height = Math.floor(viewport.height);
            canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
            canvas.style.height = `${Math.floor(viewport.height / dpr)}px`;
            canvas.style.maxWidth = "100%";
            canvas.style.maxHeight = "100%";

            const marcador = document.createElement("span");
            marcador.classList.add("preview-page-tag");
            marcador.innerText = `Pg ${numeroPagina}`;
            wrapper.appendChild(marcador);
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
    } else {
        requestAnimationFrame(() => {
            atualizarFolhaAtualPorScroll();
        });
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
        ajustarPosicaoPainelMeta();
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
    el("copias").addEventListener("input", calcularConsumo);
    el("duplex").addEventListener("change", atualizarPreview);
    el("paginasPorFolha").addEventListener("change", () => {
        folhaAtual = 1;
        atualizarPreview();
    });
    el("intervaloPaginas").addEventListener("input", () => {
        if (pdfDoc) {
            atualizarPreview();
            return;
        }
        calcularConsumo();
    });
    el("btnEnviar").addEventListener("click", enviarImpressao);
    el("btnAnterior").addEventListener("click", folhaAnterior);
    el("btnProxima").addEventListener("click", proximaFolha);
    window.addEventListener("resize", reagendarRenderAposResize);

    const professorSolicitante = el("professorSolicitante");
    if (professorSolicitante) {
        professorSolicitante.addEventListener("change", async () => {
            atualizarTitulosContextoImpressao();
            el("msg").innerText = "";

            try {
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

window.atualizarPreview = atualizarPreview;
window.enviarImpressao = enviarImpressao;
window.proximaFolha = proximaFolha;
window.folhaAnterior = folhaAnterior;

async function inicializarPagina() {
    registrarEventos();
    atualizarComportamentoOrientacao();
    atualizarEstadoArquivoSelecionado();
    mostrarPreviewVazio();

    try {
        await carregarUsuario();
        await carregarProfessoresImpressaoAdmin();
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
