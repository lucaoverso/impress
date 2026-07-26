const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    encerrarSessao,
} = window.AppAuth;
const { fetchJson, fetchResposta } = window.AppApi;
const { paraIso, paraDataBr } = window.AppFormat;

const tokenApc = garantirToken();
const headersApc = criarHeadersAuth(tokenApc);
const headersJsonApc = criarHeadersJsonAuth(tokenApc);

const nomesMesesApc = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];
const nomesDiasSemanaApc = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"];

let usuarioApc = null;
let contextoApc = null;
let mesAtualApc = new Date();
let dataSelecionadaApc = paraIso(new Date());
let dataSelecionadaManualmenteApc = false;
let calendarioApc = { periodos: [] };
let periodoSelecionadoApcId = null;
let periodoEmEdicaoApcId = null;
let perfilApc = "docente";
let focoAntesModalApc = null;
let envioPreviewApc = null;
let envioPreviewApcId = null;
const professoresAbertosPorPeriodoApc = new Map();
let arquivoPreviewUrlApc = "";
let arquivoPreviewNomeApc = "";
let focoAntesPreviewApc = null;
let envioImpressaoApc = null;
let etapaImpressaoApc = 1;
let tagsImpressaoApc = [];
let turmasImpressaoApc = [];
let focoAntesPrintWizardApc = null;
let apcModalScrollLocks = 0;
let apcModalScrollY = 0;
let apcPrintPdfDoc = null;
let apcPrintPreviewUrl = "";
let apcPrintFolhaAtual = 1;
let apcPrintRenderToken = 0;
let painelAtividadeApc = null;
let focoAntesAtividadeApc = null;
let timerPreviewAtividadeApc = null;
let tokenPreviewAtividadeApc = 0;
let controllerPreviewAtividadeApc = null;
let timerFechamentoAtividadeApc = null;
let documentoPreviewAtividadeApc = null;
let paginaPreviewAtividadeApc = 1;
const cachePreviewAtividadeApc = new Map();
const LIMITE_CACHE_PREVIEW_APC = 6;
let opcoesDestinatariosApc = [];
let selecoesDestinatariosApc = new Set();

const APC_PRINT_A4 = {
    retrato: { largura: 794, altura: 1123 },
    paisagem: { largura: 1123, altura: 794 },
};

function hojeIsoApc() {
    return paraIso(new Date());
}

function setMensagemApc(texto, erro = false) {
    const msg = el("msgApc");
    if (!msg) return;
    msg.innerText = texto || "";
    msg.classList.toggle("is-error", Boolean(texto) && erro);
    msg.classList.toggle("is-success", Boolean(texto) && !erro);
}

function renderEstadoVazioApc(container, { icone, titulo, descricao, acao, aoClicar }) {
    if (!container) return;
    container.innerHTML = "";

    const estado = document.createElement("div");
    estado.className = "apc-empty-state";
    estado.innerHTML = `
        <span class="apc-empty-icon" aria-hidden="true"><i class="bi ${icone}"></i></span>
        <h3>${titulo}</h3>
        <p>${descricao}</p>
    `;

    if (acao && aoClicar) {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.innerText = acao;
        botao.addEventListener("click", aoClicar);
        estado.appendChild(botao);
    }
    container.appendChild(estado);
}

function mesIsoApc(data) {
    return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}`;
}

function formatarDataHoraApc(valor) {
    const texto = String(valor || "").trim().replace("T", " ");
    if (!texto) return "";
    const partes = texto.split(" ");
    if (partes.length < 2) {
        return partes[0].includes("-") ? paraDataBr(partes[0]) : texto;
    }
    const hora = String(partes[1] || "").slice(0, 5);
    return `${paraDataBr(partes[0])} ${hora}`;
}

function pluralizarApc(total, singular, plural) {
    return `${total} ${total === 1 ? singular : plural}`;
}

function obterPaginaApc() {
    return document.querySelector(".apc-page");
}

function usuarioPodeVerGestaoApc() {
    return Boolean(usuarioApc?.pode_gerir);
}

function modoDocenteAtivoApc() {
    return perfilApc === "docente";
}

function modoGestaoAtivoApc() {
    return perfilApc === "gestao";
}

function limparSelecaoDataGestaoApc() {
    if (!modoGestaoAtivoApc()) return;
    dataSelecionadaApc = "";
    dataSelecionadaManualmenteApc = false;
    periodoSelecionadoApcId = null;
}

function modalApcAberto() {
    return !el("apcModalBackdrop")?.hidden;
}

function previewArquivoApcAberto() {
    return !el("apcArquivoPreviewModal")?.hidden;
}

function printWizardApcAberto() {
    return !el("apcPrintWizardModal")?.hidden;
}

function activityModalApcAberto() {
    return !el("apcActivityModal")?.hidden;
}

function focarSemRolagemApc(elemento) {
    if (!(elemento instanceof HTMLElement) || !document.contains(elemento)) return;
    try {
        elemento.focus({ preventScroll: true });
    } catch (_err) {
        elemento.focus();
    }
}

function revogarPreviewArquivoApc() {
    if (arquivoPreviewUrlApc) {
        window.URL.revokeObjectURL(arquivoPreviewUrlApc);
        arquivoPreviewUrlApc = "";
    }
}

function bloquearScrollModalApc() {
    apcModalScrollLocks += 1;
    if (apcModalScrollLocks > 1) return;

    apcModalScrollY = window.scrollY || document.documentElement.scrollTop || 0;
    document.documentElement.classList.add("apc-modal-scroll-locked");
    document.body.style.position = "fixed";
    document.body.style.top = `-${apcModalScrollY}px`;
    document.body.style.left = "0";
    document.body.style.right = "0";
    document.body.style.width = "100%";
}

function liberarScrollModalApc() {
    if (apcModalScrollLocks <= 0) return;
    apcModalScrollLocks -= 1;
    if (apcModalScrollLocks > 0) return;

    const scrollRestaurado = apcModalScrollY;
    document.documentElement.classList.remove("apc-modal-scroll-locked");
    document.body.style.position = "";
    document.body.style.top = "";
    document.body.style.left = "";
    document.body.style.right = "";
    document.body.style.width = "";
    window.scrollTo(0, scrollRestaurado);
    window.requestAnimationFrame(() => window.scrollTo(0, scrollRestaurado));
    apcModalScrollY = 0;
}

function revogarPreviewPrintApc() {
    apcPrintRenderToken += 1;
    if (apcPrintPreviewUrl) {
        window.URL.revokeObjectURL(apcPrintPreviewUrl);
        apcPrintPreviewUrl = "";
    }
    apcPrintPdfDoc = null;
    apcPrintFolhaAtual = 1;
}

function definirEstadoPreviewPrintApc(texto = "") {
    const estado = el("apcPrintPreviewState");
    if (!estado) return;
    estado.hidden = !texto;
    estado.innerText = texto || "";
}

function obterLayoutPrintApc(paginasPorFolha, orientacao = "retrato") {
    if (paginasPorFolha === 2) {
        return orientacao === "paisagem"
            ? { colunas: 2, linhas: 1 }
            : { colunas: 1, linhas: 2 };
    }
    if (paginasPorFolha === 4) {
        return { colunas: 2, linhas: 2 };
    }
    return { colunas: 1, linhas: 1 };
}

function paginasSelecionadasPrintApc() {
    if (!apcPrintPdfDoc) return [];

    const total = apcPrintPdfDoc.numPages;
    const texto = String(el("apcPrintIntervalo")?.value || "").trim();
    const info = el("apcPrintIntervaloInfo");
    if (!texto) {
        if (info) info.innerText = `Todas as paginas (${total}).`;
        return Array.from({ length: total }, (_, indice) => indice + 1);
    }

    const paginas = new Set();
    texto.split(",").map((parte) => parte.trim()).filter(Boolean).forEach((parte) => {
        if (parte.includes("-")) {
            const [inicioTxt, fimTxt] = parte.split("-").map((valor) => valor.trim());
            const inicio = Number(inicioTxt);
            const fim = Number(fimTxt);
            if (!Number.isInteger(inicio) || !Number.isInteger(fim) || inicio <= 0 || fim <= 0 || inicio > fim) {
                throw new Error(`Intervalo invalido: "${parte}"`);
            }
            if (fim > total) {
                throw new Error(`Pagina ${fim} nao existe no documento.`);
            }
            for (let pagina = inicio; pagina <= fim; pagina += 1) {
                paginas.add(pagina);
            }
            return;
        }

        const pagina = Number(parte);
        if (!Number.isInteger(pagina) || pagina <= 0 || pagina > total) {
            throw new Error(`Pagina invalida: "${parte}"`);
        }
        paginas.add(pagina);
    });

    const resultado = Array.from(paginas).sort((a, b) => a - b);
    if (!resultado.length) {
        throw new Error("Nenhuma pagina valida informada.");
    }
    if (info) info.innerText = `${resultado.length} pagina(s) selecionada(s).`;
    return resultado;
}

function ajustarDimensoesPrintApc(tamanhoBase, larguraMaxima, alturaMaxima) {
    const escala = Math.min(
        Math.max(1, larguraMaxima) / tamanhoBase.largura,
        Math.max(1, alturaMaxima) / tamanhoBase.altura
    );
    const escalaSegura = Number.isFinite(escala) && escala > 0 ? escala : 1;
    return {
        largura: Math.max(1, Math.round(tamanhoBase.largura * escalaSegura)),
        altura: Math.max(1, Math.round(tamanhoBase.altura * escalaSegura)),
    };
}

function atualizarContadorPrintApc(totalFolhas = 0) {
    const contador = el("apcPrintPreviewContador");
    const anterior = el("btnApcPrintPreviewAnterior");
    const proxima = el("btnApcPrintPreviewProxima");
    if (contador) {
        contador.innerText = totalFolhas ? `Folha ${apcPrintFolhaAtual} de ${totalFolhas}` : "";
    }
    if (anterior) anterior.disabled = !totalFolhas || apcPrintFolhaAtual <= 1;
    if (proxima) proxima.disabled = !totalFolhas || apcPrintFolhaAtual >= totalFolhas;
}

async function renderPreviewPrintApc() {
    const container = el("apcPrintPreviewContainer");
    if (!container) return;
    container.innerHTML = "";

    if (!apcPrintPdfDoc) {
        atualizarContadorPrintApc(0);
        definirEstadoPreviewPrintApc("Preview indisponivel para este arquivo.");
        return;
    }

    let paginas;
    try {
        paginas = paginasSelecionadasPrintApc();
    } catch (err) {
        atualizarContadorPrintApc(0);
        definirEstadoPreviewPrintApc(err.message || "Revise o intervalo de paginas.");
        return;
    }

    const paginasPorFolha = Number(el("apcPrintPaginasFolha")?.value || 1);
    const orientacao = el("apcPrintOrientacao")?.value === "paisagem" ? "paisagem" : "retrato";
    const tamanhoFolha = APC_PRINT_A4[orientacao];
    const layout = obterLayoutPrintApc(paginasPorFolha, orientacao);
    const totalFolhas = Math.max(1, Math.ceil(paginas.length / paginasPorFolha));
    apcPrintFolhaAtual = Math.min(Math.max(1, apcPrintFolhaAtual), totalFolhas);
    atualizarContadorPrintApc(totalFolhas);
    definirEstadoPreviewPrintApc("");

    const inicio = (apcPrintFolhaAtual - 1) * paginasPorFolha;
    const paginasDaFolha = paginas.slice(inicio, inicio + paginasPorFolha);
    while (paginasDaFolha.length < paginasPorFolha) {
        paginasDaFolha.push(null);
    }

    const larguraDisponivel = Math.max(260, container.clientWidth || 420);
    const alturaDisponivel = Math.max(300, container.clientHeight || 520);
    const tamanho = ajustarDimensoesPrintApc(tamanhoFolha, larguraDisponivel - 24, alturaDisponivel - 24);
    const folha = document.createElement("div");
    folha.className = "apc-print-preview-sheet";
    folha.style.width = `${tamanho.largura}px`;
    folha.style.height = `${tamanho.altura}px`;
    folha.style.aspectRatio = `${tamanhoFolha.largura} / ${tamanhoFolha.altura}`;
    folha.style.gridTemplateColumns = `repeat(${layout.colunas}, minmax(0, 1fr))`;
    folha.style.gridTemplateRows = `repeat(${layout.linhas}, minmax(0, 1fr))`;
    container.appendChild(folha);

    const token = ++apcPrintRenderToken;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.35);
    for (const numeroPagina of paginasDaFolha) {
        if (token !== apcPrintRenderToken) return;
        if (!numeroPagina) {
            const cell = document.createElement("div");
            cell.className = "apc-print-preview-cell is-empty";
            folha.appendChild(cell);
            continue;
        }
        const page = await apcPrintPdfDoc.getPage(numeroPagina);
        const viewportBase = page.getViewport({ scale: 1 });
        const cellWidth = (tamanho.largura - 26 - (8 * (layout.colunas - 1))) / layout.colunas;
        const cellHeight = (tamanho.altura - 26 - (8 * (layout.linhas - 1))) / layout.linhas;
        const escala = Math.min(cellWidth / viewportBase.width, cellHeight / viewportBase.height);
        const viewport = page.getViewport({ scale: escala * dpr });

        const cell = document.createElement("div");
        cell.className = "apc-print-preview-cell";
        cell.dataset.pageLabel = `Pg ${numeroPagina}`;
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
        canvas.style.height = `${Math.floor(viewport.height / dpr)}px`;
        cell.appendChild(canvas);
        folha.appendChild(cell);
        await page.render({ canvasContext: ctx, viewport }).promise;
    }
}

async function carregarPreviewPrintApc(envio) {
    revogarPreviewPrintApc();
    const container = el("apcPrintPreviewContainer");
    if (container) container.innerHTML = "";
    atualizarContadorPrintApc(0);
    definirEstadoPreviewPrintApc("Preparando preview...");

    if (!window.pdfjsLib || !envio?.id) {
        definirEstadoPreviewPrintApc("Preview indisponivel neste navegador.");
        return;
    }

    const tipoPreview = tipoPreviewArquivoApc(envio);
    if (!["frame", "office"].includes(tipoPreview)) {
        definirEstadoPreviewPrintApc("Preview de impressao disponivel apenas para PDF, DOC e DOCX.");
        return;
    }

    try {
        const endpoint = tipoPreview === "office"
            ? `/apc/envios/${envio.id}/preview`
            : `/apc/envios/${envio.id}/arquivo`;
        const resposta = await fetchResposta(endpoint, { headers: headersApc });
        const blob = await resposta.blob();
        apcPrintPreviewUrl = window.URL.createObjectURL(blob);
        const buffer = await blob.arrayBuffer();
        apcPrintPdfDoc = await window.pdfjsLib.getDocument({ data: buffer }).promise;
        await renderPreviewPrintApc();
    } catch (err) {
        definirEstadoPreviewPrintApc(err.message || "Nao foi possivel preparar o preview.");
    }
}

function limparPreviewArquivoApc(mensagem = "Selecione um arquivo para visualizar.") {
    revogarPreviewArquivoApc();
    envioPreviewApc = null;
    const state = el("apcArquivoPreviewState");
    if (state) {
        state.hidden = false;
        state.innerHTML = "";
        const vazio = document.createElement("div");
        vazio.className = "booking-empty";
        vazio.innerText = mensagem;
        state.appendChild(vazio);
    }
    const frame = el("apcArquivoPreviewFrame");
    const imagem = el("apcArquivoPreviewImage");
    const texto = el("apcArquivoPreviewText");
    if (frame) {
        frame.src = "about:blank";
        frame.hidden = true;
    }
    if (imagem) {
        imagem.removeAttribute("src");
        imagem.hidden = true;
    }
    if (texto) {
        texto.textContent = "";
        texto.hidden = true;
    }
    if (el("btnApcBaixarArquivo")) {
        el("btnApcBaixarArquivo").hidden = true;
    }
    if (el("btnApcImprimirArquivo")) {
        el("btnApcImprimirArquivo").hidden = true;
    }
    if (el("apcReviewPanel")) {
        el("apcReviewPanel").hidden = true;
    }
    if (el("formApcReview")) {
        el("formApcReview").hidden = true;
        el("formApcReview").reset();
    }
    if (el("btnSalvarReviewApc")) {
        el("btnSalvarReviewApc").hidden = true;
    }
    if (el("apcReviewHistory")) {
        el("apcReviewHistory").innerHTML = "";
    }
    if (el("apcReviewMessageState")) {
        el("apcReviewMessageState").innerText = "";
    }
}

function tipoPreviewArquivoApc(envio) {
    const mime = String(envio?.arquivo_tipo || "").toLowerCase();
    const nome = nomeArquivoSistemaApc(envio).toLowerCase();
    if (mime.startsWith("image/") || /\.(png|jpe?g|gif|webp|bmp|svg)$/.test(nome)) return "image";
    if (mime.startsWith("text/") || /\.(txt|csv|md|json|xml|log)$/.test(nome)) return "text";
    if (mime === "application/pdf" || /\.pdf$/.test(nome)) return "frame";
    if (/\.(doc|docx)$/.test(nome)) return "office";
    return "unsupported";
}

function abrirModalPreviewApc(envio) {
    const modal = el("apcArquivoPreviewModal");
    const painel = el("apcArquivoPreviewPanel");
    if (!modal || !painel || !envio?.id) return;
    focoAntesPreviewApc = document.activeElement;
    modal.hidden = false;
    bloquearScrollModalApc();
    document.body.classList.add("apc-file-preview-open");
    window.requestAnimationFrame(() => {
        modal.classList.add("is-visible");
        focarSemRolagemApc(painel);
    });
    void carregarPreviewArquivoApc(envio);
}

function fecharModalPreviewApc({ devolverFoco = true, liberarScroll = true } = {}) {
    const modal = el("apcArquivoPreviewModal");
    if (!modal) return;
    const estavaAberto = !modal.hidden;
    modal.classList.remove("is-visible");
    document.body.classList.remove("apc-file-preview-open");
    window.setTimeout(() => {
        modal.hidden = true;
        limparPreviewArquivoApc();
    }, 220);
    if (estavaAberto && liberarScroll) liberarScrollModalApc();
    if (devolverFoco && focoAntesPreviewApc instanceof HTMLElement) {
        focarSemRolagemApc(focoAntesPreviewApc);
    }
    focoAntesPreviewApc = null;
}

function setMensagemPrintApc(texto, erro = false) {
    const mensagem = el("apcPrintMensagem");
    if (!mensagem) return;
    mensagem.innerText = texto || "";
    mensagem.classList.toggle("is-error", Boolean(texto) && erro);
    mensagem.classList.toggle("is-success", Boolean(texto) && !erro);
}

function tagsSelecionadasPrintApc() {
    return Array.from(
        document.querySelectorAll("#apcPrintTags input[type='checkbox']:checked")
    )
        .map((input) => String(input.value || "").trim())
        .filter(Boolean);
}

function renderTagsPrintApc() {
    const container = el("apcPrintTags");
    if (!container) return;
    container.innerHTML = "";

    if (!tagsImpressaoApc.length) {
        const vazio = document.createElement("p");
        vazio.className = "apc-inline-hint";
        vazio.innerText = "Nenhum tipo de material cadastrado.";
        container.appendChild(vazio);
        return;
    }

    tagsImpressaoApc.forEach((tag) => {
        const valor = String(tag?.id || tag?.label || "").trim();
        if (!valor) return;

        const label = document.createElement("label");
        label.className = "apc-print-tag";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = valor;
        const texto = document.createElement("span");
        texto.innerText = String(tag?.label || valor);
        label.append(input, texto);
        container.appendChild(label);
    });
}

async function carregarTagsPrintApc() {
    const dados = await fetchJson("/impressao/tags", { headers: headersApc });
    tagsImpressaoApc = Array.isArray(dados) ? dados : [];
    renderTagsPrintApc();
}

function rotuloTurmaPrintApc(turma) {
    const nome = String(turma?.nome || "").trim() || "Turma";
    const turno = String(turma?.turno || "").trim();
    const estudantes = Number(turma?.quantidade_estudantes || 0);
    const partes = [nome];
    if (turno) partes.push(turno);
    if (estudantes > 0) partes.push(pluralizarApc(estudantes, "estudante", "estudantes"));
    return partes.join(" - ");
}

function turmaPrintSelecionadaApc() {
    const turmaId = Number(el("apcPrintTurma")?.value || 0);
    if (!turmaId) return null;
    return turmasImpressaoApc.find((turma) => Number(turma.id || 0) === turmaId) || null;
}

function atualizarResumoTurmaPrintApc({ preencherCopias = true } = {}) {
    const resumo = el("apcPrintTurmaResumo");
    const turma = turmaPrintSelecionadaApc();
    if (!resumo) return;

    if (!turma) {
        resumo.innerText = "Selecione uma turma para preencher as copias.";
        return;
    }

    const estudantes = Number(turma.quantidade_estudantes || 0);
    if (estudantes > 0) {
        if (preencherCopias) {
            el("apcPrintCopias").value = String(estudantes);
        }
        resumo.innerText = `${rotuloTurmaPrintApc(turma)} selecionada. Copias sugeridas: ${estudantes}.`;
    } else {
        resumo.innerText = `${rotuloTurmaPrintApc(turma)} selecionada. Quantidade de estudantes nao informada.`;
    }

    if (etapaImpressaoApc === 3) atualizarResumoPrintApc();
}

function renderTurmasPrintApc(turmaIdPreferida = 0) {
    const select = el("apcPrintTurma");
    if (!select) return;
    select.innerHTML = "";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.innerText = turmasImpressaoApc.length
        ? "Selecione uma turma"
        : "Nenhuma turma cadastrada";
    select.appendChild(placeholder);

    turmasImpressaoApc.forEach((turma) => {
        const option = document.createElement("option");
        option.value = String(turma.id || "");
        option.innerText = rotuloTurmaPrintApc(turma);
        select.appendChild(option);
    });

    const preferidaExiste = turmasImpressaoApc.some(
        (turma) => Number(turma.id || 0) === Number(turmaIdPreferida || 0)
    );
    select.value = preferidaExiste ? String(turmaIdPreferida) : "";
    atualizarResumoTurmaPrintApc({ preencherCopias: preferidaExiste });
}

async function carregarTurmasPrintApc(turmaIdPreferida = 0) {
    const select = el("apcPrintTurma");
    if (select) {
        select.innerHTML = '<option value="">Carregando turmas...</option>';
    }
    const dados = await fetchJson("/impressao/turmas", { headers: headersApc });
    turmasImpressaoApc = Array.isArray(dados) ? dados : [];
    renderTurmasPrintApc(turmaIdPreferida);
}

function adicionarItemResumoPrintApc(resumo, titulo, valor) {
    const termo = document.createElement("dt");
    termo.innerText = titulo;
    const descricao = document.createElement("dd");
    descricao.innerText = valor;
    resumo.append(termo, descricao);
}

function atualizarResumoPrintApc() {
    const resumo = el("apcPrintResumo");
    if (!resumo) return;
    resumo.innerHTML = "";
    const paginasPorFolha = el("apcPrintPaginasFolha");
    const orientacao = el("apcPrintOrientacao");
    adicionarItemResumoPrintApc(
        resumo,
        "Arquivo",
        nomeArquivoPrincipalApc(envioImpressaoApc) || "Anexo"
    );
    const turma = turmaPrintSelecionadaApc();
    adicionarItemResumoPrintApc(
        resumo,
        "Turma",
        turma ? rotuloTurmaPrintApc(turma) : "Nao selecionada"
    );
    adicionarItemResumoPrintApc(resumo, "Copias", el("apcPrintCopias").value);
    adicionarItemResumoPrintApc(
        resumo,
        "Paginas",
        el("apcPrintIntervalo").value.trim() || "Todas"
    );
    adicionarItemResumoPrintApc(
        resumo,
        "Layout",
        paginasPorFolha.options[paginasPorFolha.selectedIndex].text
    );
    adicionarItemResumoPrintApc(
        resumo,
        "Orientacao",
        orientacao.options[orientacao.selectedIndex].text
    );
    adicionarItemResumoPrintApc(
        resumo,
        "Frente e verso",
        el("apcPrintDuplex").checked ? "Sim" : "Nao"
    );
    adicionarItemResumoPrintApc(
        resumo,
        "Tipo de material",
        tagsSelecionadasPrintApc().join(", ")
    );
}

function renderEtapaPrintApc(etapa) {
    etapaImpressaoApc = Math.max(1, Math.min(3, Number(etapa) || 1));
    document.querySelectorAll("[data-apc-print-step]").forEach((secao) => {
        secao.hidden = Number(secao.dataset.apcPrintStep) !== etapaImpressaoApc;
    });
    document.querySelectorAll("[data-apc-print-stepper]").forEach((item) => {
        const numero = Number(item.dataset.apcPrintStepper);
        item.classList.toggle("is-current", numero === etapaImpressaoApc);
        item.classList.toggle("is-complete", numero < etapaImpressaoApc);
        item.setAttribute("aria-current", numero === etapaImpressaoApc ? "step" : "false");
    });
    el("btnApcPrintVoltar").hidden = etapaImpressaoApc === 1;
    el("btnApcPrintContinuar").hidden = etapaImpressaoApc === 3;
    el("btnApcPrintConfirmar").hidden = etapaImpressaoApc !== 3;
    if (etapaImpressaoApc === 3) atualizarResumoPrintApc();
}

async function abrirPrintWizardApc(envio) {
    const modal = el("apcPrintWizardModal");
    const painel = el("apcPrintWizardPanel");
    if (!modal || !painel || !envio?.id || !modoGestaoAtivoApc()) return;

    const previewAberto = previewArquivoApcAberto();
    const focoRetorno = previewAberto ? focoAntesPreviewApc : document.activeElement;
    envioImpressaoApc = envio;
    focoAntesPrintWizardApc = focoRetorno;
    el("apcPrintWizardArquivo").innerText = nomeArquivoPrincipalApc(envio);
    el("apcPrintTurma").innerHTML = '<option value="">Carregando turmas...</option>';
    el("apcPrintTurmaResumo").innerText = "Carregando turmas...";
    el("apcPrintCopias").value = "1";
    el("apcPrintIntervalo").value = "";
    el("apcPrintPaginasFolha").value = "1";
    el("apcPrintOrientacao").value = "retrato";
    el("apcPrintDuplex").checked = false;
    el("btnApcPrintConfirmar").disabled = false;
    setMensagemPrintApc("");
    renderEtapaPrintApc(1);
    modal.hidden = false;
    if (!previewAberto) {
        bloquearScrollModalApc();
    }
    document.body.classList.add("apc-print-wizard-open");
    fecharModalPreviewApc({ devolverFoco: false, liberarScroll: !previewAberto });
    window.requestAnimationFrame(() => {
        modal.classList.add("is-visible");
        focarSemRolagemApc(painel);
        void carregarPreviewPrintApc(envio);
    });

    const errosCarregamento = [];
    try {
        await carregarTurmasPrintApc(Number(envio.turma_id || 0));
    } catch (err) {
        turmasImpressaoApc = [];
        renderTurmasPrintApc(0);
        errosCarregamento.push(err.message || "Nao foi possivel carregar as turmas.");
    }

    try {
        await carregarTagsPrintApc();
    } catch (err) {
        tagsImpressaoApc = [];
        renderTagsPrintApc();
        errosCarregamento.push(err.message || "Nao foi possivel carregar os tipos de material.");
    }

    if (errosCarregamento.length) {
        setMensagemPrintApc(errosCarregamento.join(" "), true);
    }
}

function fecharPrintWizardApc() {
    const modal = el("apcPrintWizardModal");
    if (!modal) return;
    const estavaAberto = !modal.hidden;
    modal.classList.remove("is-visible");
    document.body.classList.remove("apc-print-wizard-open");
    revogarPreviewPrintApc();
    const container = el("apcPrintPreviewContainer");
    if (container) container.innerHTML = "";
    atualizarContadorPrintApc(0);
    window.setTimeout(() => {
        modal.hidden = true;
        envioImpressaoApc = null;
        setMensagemPrintApc("");
    }, 220);
    if (estavaAberto) liberarScrollModalApc();
    if (focoAntesPrintWizardApc instanceof HTMLElement) {
        focarSemRolagemApc(focoAntesPrintWizardApc);
    }
    focoAntesPrintWizardApc = null;
}

function avancarPrintWizardApc() {
    setMensagemPrintApc("");
    if (etapaImpressaoApc === 1) {
        const copias = Number(el("apcPrintCopias").value);
        if (!Number.isInteger(copias) || copias < 1 || copias > 999) {
            setMensagemPrintApc("Informe uma quantidade de copias entre 1 e 999.", true);
            focarSemRolagemApc(el("apcPrintCopias"));
            return;
        }
    }
    if (etapaImpressaoApc === 2 && tagsSelecionadasPrintApc().length === 0) {
        setMensagemPrintApc("Selecione pelo menos um tipo de material.", true);
        return;
    }
    renderEtapaPrintApc(etapaImpressaoApc + 1);
}

async function enviarImpressaoApc(event) {
    event.preventDefault();
    if (!envioImpressaoApc?.id || etapaImpressaoApc !== 3) return;

    const botao = el("btnApcPrintConfirmar");
    const formData = new FormData();
    formData.append("copias", el("apcPrintCopias").value);
    formData.append("paginas_por_folha", el("apcPrintPaginasFolha").value);
    formData.append("duplex", el("apcPrintDuplex").checked ? "true" : "false");
    formData.append("orientacao", el("apcPrintOrientacao").value);
    formData.append("intervalo_paginas", el("apcPrintIntervalo").value.trim());
    tagsSelecionadasPrintApc().forEach((tag) => formData.append("tags", tag));

    botao.disabled = true;
    setMensagemPrintApc("Enviando o arquivo para a fila de impressao...");
    try {
        await fetchJson(`/apc/envios/${envioImpressaoApc.id}/imprimir`, {
            method: "POST",
            headers: headersApc,
            body: formData,
        });
        setMensagemPrintApc("Impressao enviada com sucesso.");
        botao.hidden = true;
        el("btnApcPrintVoltar").hidden = true;
    } catch (err) {
        botao.disabled = false;
        setMensagemPrintApc(err.message || "Nao foi possivel enviar a impressao.", true);
    }
}

function perfilInicialApc() {
    return usuarioPodeVerGestaoApc() ? "gestao" : "docente";
}

function descricaoUsuarioApc() {
    if (!usuarioApc) return "";
    const area = modoGestaoAtivoApc() ? "Gestao de anexos" : "Minhas entregas";
    return `${usuarioApc.nome} | ${area}`;
}

function visaoAtivaApc() {
    return modoGestaoAtivoApc() ? "gestao" : "docente";
}

function anoLetivoAtivoApc() {
    return Number(contextoApc?.ano_letivo_atual || new Date().getFullYear());
}

function preencherSelectPublicoApc() {
    const select = el("apcPublicoAlvo");
    if (!select) return;
    select.innerHTML = "";
    (contextoApc?.publicos_alvo || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item.valor || "");
        option.innerText = String(item.label || item.valor || "");
        select.appendChild(option);
    });
    if ((contextoApc?.publicos_alvo || []).length) {
        select.value = String(contextoApc.publicos_alvo[0].valor || "TODOS_PROFESSORES");
    }
}

function preencherSelectTiposEntregaApc() {
    const select = el("apcTipoEntrega");
    if (!select) return;
    select.innerHTML = "";
    (contextoApc?.tipos_entrega || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = String(item.valor || "");
        option.innerText = String(item.label || item.valor || "");
        select.appendChild(option);
    });
    if ((contextoApc?.tipos_entrega || []).length) {
        select.value = String(contextoApc.tipos_entrega[0].valor || "GERAL");
    }
}

function periodoResumoSelecionado(periodos) {
    const itens = Array.isArray(periodos) ? periodos : [];
    if (!itens.length) return null;
    if (periodoSelecionadoApcId) {
        const encontrado = itens.find((item) => Number(item.id) === Number(periodoSelecionadoApcId));
        if (encontrado) return encontrado;
    }
    return itens[0];
}

function aplicarVisibilidadeApc() {
    const podeGerir = usuarioPodeVerGestaoApc();
    const layoutProfessor = modoDocenteAtivoApc();
    const pagina = obterPaginaApc();
    const acoesGestao = el("apcGestaoActions");
    const detalheDocente = el("apcDocenteDetalhe");
    const detalheGestao = el("apcGestaoDetalhe");
    const filtrosGestao = el("apcGestaoFiltros");
    const tituloSolicitacoes = el("apcSolicitacoesTitulo");
    const descricaoSolicitacoes = el("apcSolicitacoesDescricao");
    const gestaoAtiva = podeGerir && modoGestaoAtivoApc();

    if (detalheDocente) {
        detalheDocente.hidden = !layoutProfessor;
    }
    if (detalheGestao) {
        detalheGestao.hidden = !gestaoAtiva;
    }
    if (filtrosGestao) {
        filtrosGestao.hidden = !gestaoAtiva;
    }
    if (tituloSolicitacoes) {
        tituloSolicitacoes.innerText = layoutProfessor ? "Minhas entregas" : "Solicitações";
    }
    if (descricaoSolicitacoes) {
        descricaoSolicitacoes.innerText = layoutProfessor
            ? "Pendências aparecem primeiro; a mais urgente já fica aberta."
            : "Selecione uma solicitação para acompanhar professores e anexos.";
    }
    if (acoesGestao) {
        acoesGestao.hidden = !gestaoAtiva;
    }
    if (el("btnAbrirEditarApc")) {
        el("btnAbrirEditarApc").hidden = !(gestaoAtiva && Boolean(periodoSelecionadoApcId));
    }
    const usuarioResumo = el("apcUsuario");
    if (usuarioResumo) {
        usuarioResumo.innerText = descricaoUsuarioApc();
    }

    if (!pagina) return;
    pagina.classList.toggle("is-manager", podeGerir);
    pagina.classList.toggle("is-professor", layoutProfessor);
    pagina.classList.toggle("is-docente-mode", modoDocenteAtivoApc());
    pagina.classList.toggle("is-gestao-mode", modoGestaoAtivoApc());
}

function preencherFormularioPeriodo(periodo) {
    const dataBase = periodo?.data_referencia || dataSelecionadaApc || hojeIsoApc();
    el("apcDataReferencia").value = dataBase;
    el("apcPrazoEnvio").value = periodo?.prazo_envio_input || `${dataBase}T23:59`;
    el("apcTitulo").value = periodo?.titulo || "Documento";
    el("apcObservacao").value = periodo?.observacao || "";
    el("apcPublicoAlvo").value = periodo?.publico_alvo || "TODOS_PROFESSORES";
    el("apcTipoEntrega").value = periodo?.tipo_entrega || "GERAL";
    el("btnExcluirApc").hidden = !Boolean(periodo?.id);
    if (!periodo) {
        selecoesDestinatariosApc = new Set();
        opcoesDestinatariosApc = [];
        void sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
    }
}

function atualizarCabecalhoModalApc(periodo = null) {
    const editando = Boolean(periodoEmEdicaoApcId && periodo);
    el("apcModalTitulo").innerText = editando
        ? "Editar solicitação de entrega"
        : "Nova solicitação de entrega";
    el("apcModalDescricao").innerText = editando
        ? "Ajuste o documento, o prazo e os responsáveis por esta entrega."
        : "Defina o documento, o prazo e quem deve realizar a entrega.";
}

function abrirModalFormularioApc(periodo = null) {
    focoAntesModalApc = document.activeElement;
    periodoEmEdicaoApcId = Number(periodo?.id || 0) || null;
    preencherFormularioPeriodo(periodo);
    atualizarCabecalhoModalApc(periodo);
    const backdrop = el("apcModalBackdrop");
    if (!backdrop) return;
    backdrop.hidden = false;
    document.body.classList.add("apc-modal-open");
    window.setTimeout(() => {
        focarSemRolagemApc(el("apcTitulo"));
    }, 0);
}

function fecharModalFormularioApc({ limpar = false } = {}) {
    const backdrop = el("apcModalBackdrop");
    if (backdrop) {
        backdrop.hidden = true;
    }
    document.body.classList.remove("apc-modal-open");
    if (focoAntesModalApc instanceof HTMLElement) {
        focarSemRolagemApc(focoAntesModalApc);
    }
    focoAntesModalApc = null;
    if (limpar) {
        periodoEmEdicaoApcId = null;
        preencherFormularioPeriodo(null);
        atualizarCabecalhoModalApc(null);
    }
}

function renderResumoCompactoApc(itens) {
    const wrap = document.createElement("div");
    wrap.className = "apc-resumo-compacto";
    itens.forEach((item) => {
        const card = document.createElement("div");
        card.className = "apc-resumo-compacto-item";
        card.innerHTML = `<span>${item.label}</span><strong>${item.valor}</strong>`;
        wrap.appendChild(card);
    });
    return wrap;
}

function criarStatusApc(texto, tipo = "pending") {
    const span = document.createElement("span");
    const classe = tipo === "ok"
        ? "is-ok"
        : tipo === "closed"
            ? "is-closed"
            : tipo === "adjustment"
                ? "is-adjustment"
                : tipo === "printed"
                    ? "is-printed"
                    : "is-pending";
    span.className = `apc-status ${classe}`;
    span.innerText = texto;
    return span;
}

function statusRevisaoEnvioApc(envio) {
    const status = String(envio?.review_status || "PENDENTE").toUpperCase();
    if (status === "APROVADO") {
        return { status, texto: "Aprovado", tipo: "ok" };
    }
    if (status === "IMPRESSO") {
        return { status, texto: "Impresso", tipo: "printed" };
    }
    if (status === "AJUSTE_SOLICITADO") {
        return { status, texto: "Realizar ajuste", tipo: "adjustment" };
    }
    return { status: "PENDENTE", texto: "Aguardando analise", tipo: "pending" };
}

function tituloHistoricoRevisaoApc(status) {
    const statusNormalizado = String(status || "").toUpperCase();
    if (statusNormalizado === "APROVADO") return "Aprovado";
    if (statusNormalizado === "AJUSTE_SOLICITADO") return "Ajuste solicitado";
    if (statusNormalizado === "IMPRESSO") return "Marcado como impresso";
    return "";
}

function nomeResponsavelRevisaoApc(envio) {
    const nome = String(envio?.reviewed_by_name || "").trim();
    const cargo = String(envio?.reviewed_by_cargo || "").trim().toUpperCase();
    const prefixo = cargo === "COORDENADOR"
        ? "Coord."
        : cargo === "ADMIN"
            ? "PCPI"
            : "";
    return [prefixo, nome].filter(Boolean).join(" ");
}

function criarEventoHistoricoApc(titulo, responsavel, dataHora) {
    const evento = document.createElement("div");
    evento.className = "apc-review-history-event";

    const acao = document.createElement("p");
    const destaque = document.createElement("strong");
    destaque.innerText = titulo;
    acao.appendChild(destaque);
    evento.appendChild(acao);

    if (responsavel) {
        const autor = document.createElement("p");
        autor.innerText = responsavel;
        evento.appendChild(autor);
    }

    if (dataHora) {
        const data = document.createElement("small");
        data.innerText = formatarDataHoraApc(dataHora);
        evento.appendChild(data);
    }

    return evento;
}

function criarOrientacaoRevisaoApc(envio) {
    const mensagem = String(envio?.review_message || "").trim();
    if (!mensagem) return null;
    const orientacao = document.createElement("p");
    orientacao.className = "apc-review-guidance";
    orientacao.innerText = mensagem;
    return orientacao;
}

function criarChipApc(texto) {
    const chip = document.createElement("span");
    chip.className = "apc-chip";
    chip.innerText = texto;
    return chip;
}

function criarMetaApc(texto) {
    const meta = document.createElement("span");
    meta.innerText = texto;
    return meta;
}

function nomeArquivoClienteApc(envio) {
    return String(envio?.arquivo_nome_cliente || envio?.arquivo_nome_original || "").trim();
}

function nomeArquivoSistemaApc(envio) {
    return String(envio?.arquivo_nome_original || "").trim();
}

function nomeArquivoPrincipalApc(envio) {
    return nomeArquivoClienteApc(envio) || "Arquivo enviado";
}

function nomeArquivoPadronizadoDivergeApc(envio) {
    const nomeCliente = nomeArquivoClienteApc(envio);
    const nomeSistema = nomeArquivoSistemaApc(envio);
    return Boolean(nomeCliente && nomeSistema && nomeCliente !== nomeSistema);
}

function chaveDestinatarioApc(item) {
    return [
        Number(item?.professor_id || 0),
        Number(item?.turma_id || 0),
        Number(item?.disciplina_id || 0),
    ].join(":");
}

function publicoSelecionadoManualApc() {
    return el("apcPublicoAlvo")?.value === "PROFESSORES_SELECIONADOS";
}

function coletarDestinatariosSelecionadosApc() {
    return Array.from(selecoesDestinatariosApc).map((chave) => {
        const [professorId, turmaId, disciplinaId] = String(chave).split(":").map((valor) => Number(valor || 0));
        return {
            professor_id: professorId,
            turma_id: turmaId,
            disciplina_id: disciplinaId,
        };
    });
}

function aplicarSelecoesDestinatariosApc(destinatarios) {
    selecoesDestinatariosApc = new Set(
        (destinatarios || []).map((item) => chaveDestinatarioApc(item))
    );
}

function atualizarResumoDestinatariosApc() {
    const resumo = el("apcDestinatariosResumo");
    if (!resumo) return;
    const total = selecoesDestinatariosApc.size;
    resumo.innerText = total
        ? `${pluralizarApc(total, "combinação selecionada", "combinações selecionadas")} para esta solicitação.`
        : "Nenhuma combinação selecionada ainda.";
}

async function carregarOpcoesDestinatariosApc(force = false) {
    if (!publicoSelecionadoManualApc()) return;
    if (opcoesDestinatariosApc.length && !force) {
        renderDestinatariosApc();
        return;
    }
    const anoLetivo = anoLetivoAtivoApc();
    if (!anoLetivo) {
        opcoesDestinatariosApc = [];
        renderDestinatariosApc();
        return;
    }
    const params = new URLSearchParams({ ano_letivo: String(anoLetivo) });
    if (periodoEmEdicaoApcId) {
        params.set("periodo_id", String(periodoEmEdicaoApcId));
    }
    const resposta = await fetchJson(`/apc/destinatarios/opcoes?${params.toString()}`, {
        headers: headersApc,
    });
    opcoesDestinatariosApc = Array.isArray(resposta?.professores) ? resposta.professores : [];
    renderDestinatariosApc();
}

function renderDestinatariosApc() {
    const lista = el("apcDestinatariosLista");
    if (!lista) return;
    lista.innerHTML = "";

    if (!publicoSelecionadoManualApc()) {
        atualizarResumoDestinatariosApc();
        return;
    }

    if (!opcoesDestinatariosApc.length) {
        lista.innerHTML = '<div class="booking-empty">Nenhum vinculo de professor, turma e disciplina foi encontrado para este ano letivo.</div>';
        atualizarResumoDestinatariosApc();
        return;
    }

    opcoesDestinatariosApc.forEach((professor) => {
        const card = document.createElement("article");
        card.className = "apc-destinatario-card";

        const topo = document.createElement("div");
        topo.className = "apc-destinatario-topo";
        topo.innerHTML = `
            <div>
                <h5>${professor.professor_nome || "Professor"}</h5>
                <p>${professor.professor_email || "Sem e-mail"}</p>
            </div>
        `;

        const acoes = document.createElement("div");
        acoes.className = "apc-inline-actions";

        const marcarTodos = document.createElement("button");
        marcarTodos.type = "button";
        marcarTodos.innerText = "Marcar professor";
        marcarTodos.addEventListener("click", () => {
            (professor.destinatarios || []).forEach((item) => {
                selecoesDestinatariosApc.add(chaveDestinatarioApc(item));
            });
            renderDestinatariosApc();
        });
        acoes.appendChild(marcarTodos);

        const limpar = document.createElement("button");
        limpar.type = "button";
        limpar.innerText = "Limpar professor";
        limpar.addEventListener("click", () => {
            (professor.destinatarios || []).forEach((item) => {
                selecoesDestinatariosApc.delete(chaveDestinatarioApc(item));
            });
            renderDestinatariosApc();
        });
        acoes.appendChild(limpar);
        topo.appendChild(acoes);
        card.appendChild(topo);

        const grid = document.createElement("div");
        grid.className = "apc-destinatario-opcoes";

        (professor.destinatarios || []).forEach((item) => {
            const chave = chaveDestinatarioApc(item);
            const label = document.createElement("label");
            label.className = "apc-destinatario-item";
            if (item.vinculo_ativo === false) {
                label.classList.add("is-inactive-link");
            }

            const input = document.createElement("input");
            input.type = "checkbox";
            input.checked = selecoesDestinatariosApc.has(chave);
            input.addEventListener("change", () => {
                if (input.checked) {
                    selecoesDestinatariosApc.add(chave);
                } else {
                    selecoesDestinatariosApc.delete(chave);
                }
                atualizarResumoDestinatariosApc();
            });

            const texto = document.createElement("span");
            texto.innerText = item.vinculo_ativo === false
                ? `${item.label || `${item.disciplina_nome} - ${item.turma_nome}`} · sem vinculo atual`
                : item.label || `${item.disciplina_nome} - ${item.turma_nome}`;

            label.appendChild(input);
            label.appendChild(texto);
            grid.appendChild(label);
        });

        card.appendChild(grid);
        lista.appendChild(card);
    });

    atualizarResumoDestinatariosApc();
}

async function sincronizarVisibilidadeDestinatariosApc({ recarregar = false } = {}) {
    const wrap = el("apcDestinatariosWrap");
    if (!wrap) return;
    const ativo = publicoSelecionadoManualApc();
    wrap.hidden = !ativo;
    if (!ativo) {
        atualizarResumoDestinatariosApc();
        return;
    }
    await carregarOpcoesDestinatariosApc(recarregar);
}

async function baixarArquivoApc(envio) {
    if (!envio?.id) return;
    try {
        const resposta = await fetchResposta(`/apc/envios/${envio.id}/arquivo`, {
            headers: headersApc,
        });
        const blob = await resposta.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = envio.arquivo_nome_original || "arquivo";
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => {
            window.URL.revokeObjectURL(url);
        }, 30000);
    } catch (err) {
        setMensagemApc(err.message || "Nao foi possivel baixar o arquivo.", true);
    }
}

function criarBotaoVisualizarApc(envio) {
    const visualizar = document.createElement("button");
    visualizar.type = "button";
    visualizar.className = "btn-destaque";
    visualizar.innerText = "Visualizar";
    visualizar.addEventListener("click", () => {
        abrirModalPreviewApc(envio);
    });
    return visualizar;
}

function agruparItensGestaoPorProfessor(itens) {
    const grupos = new Map();
    (itens || []).forEach((item) => {
        const professorId = Number(item.professor_id || 0);
        if (!grupos.has(professorId)) {
            grupos.set(professorId, {
                professor_id: professorId,
                professor_nome: item.professor_nome || "Professor",
                professor_email: item.professor_email || "",
                total_entregas: 0,
                total_enviadas: 0,
                total_pendentes: 0,
                total_aprovadas: 0,
                total_impressas: 0,
                total_ajustes: 0,
                total_aguardando_revisao: 0,
                turmas: [],
                disciplinas: [],
                entregas: [],
            });
        }
        const grupo = grupos.get(professorId);
        grupo.total_entregas += 1;
        grupo.total_enviadas += item.enviado ? 1 : 0;
        grupo.total_pendentes += item.enviado ? 0 : 1;
        const reviewStatus = String(item.envio?.review_status || "PENDENTE");
        grupo.total_aprovadas += reviewStatus === "APROVADO" ? 1 : 0;
        grupo.total_impressas += reviewStatus === "IMPRESSO" ? 1 : 0;
        grupo.total_ajustes += reviewStatus === "AJUSTE_SOLICITADO" ? 1 : 0;
        grupo.total_aguardando_revisao += item.enviado && reviewStatus === "PENDENTE" ? 1 : 0;
        if (item.turma_nome && !grupo.turmas.includes(item.turma_nome)) {
            grupo.turmas.push(item.turma_nome);
        }
        if (item.disciplina_nome && !grupo.disciplinas.includes(item.disciplina_nome)) {
            grupo.disciplinas.push(item.disciplina_nome);
        }
        grupo.entregas.push(item);
    });
    return Array.from(grupos.values()).sort((a, b) => (
        String(a.professor_nome || "").localeCompare(String(b.professor_nome || ""), "pt-BR")
    ));
}

function statusResumoPeriodoApc(item, modoGestao = false) {
    if (!item) {
        return { texto: "Sem dados", tipo: "pending" };
    }
    if (modoGestao) {
        if (Number(item.total_ajustes || 0) > 0) {
            return { texto: "Ajustes solicitados", tipo: "adjustment" };
        }
        if (
            Number(item.total_elegiveis || 0) > 0
            && Number(item.total_impressos || 0) === Number(item.total_elegiveis || 0)
        ) {
            return { texto: "Impresso", tipo: "printed" };
        }
        if (
            Number(item.total_elegiveis || 0) > 0
            && Number(item.total_aprovados || 0) === Number(item.total_elegiveis || 0)
        ) {
            return { texto: "Aprovado", tipo: "ok" };
        }
        if (Number(item.total_elegiveis || 0) > 0 && Number(item.total_pendentes || 0) === 0) {
            return { texto: "Revisao pendente", tipo: "pending" };
        }
        if (item.prazo_expirado) {
            return { texto: "Prazo encerrado", tipo: "closed" };
        }
        return {
            texto: pluralizarApc(Number(item.total_pendentes || 0), "pendência", "pendências"),
            tipo: "pending",
        };
    }
    if (Number(item.total_ajustes || 0) > 0) {
        return { texto: "Realizar ajuste", tipo: "adjustment" };
    }
    if (
        Number(item.total_entregas || 0) > 0
        && Number(item.total_impressos || 0) === Number(item.total_entregas || 0)
    ) {
        return { texto: "Impresso", tipo: "printed" };
    }
    if (
        Number(item.total_entregas || 0) > 0
        && Number(item.total_aprovados || 0) === Number(item.total_entregas || 0)
    ) {
        return { texto: "Aprovado", tipo: "ok" };
    }
    if (item.enviado) {
        return { texto: "Aguardando analise", tipo: "pending" };
    }
    if (item.prazo_expirado) {
        return { texto: "Prazo encerrado", tipo: "closed" };
    }
    return { texto: "Pendente", tipo: "pending" };
}

function criarCorpoResumoGestaoApc(periodo, detalhe) {
    const body = document.createElement("div");
    body.className = "apc-accordion-body";

    const chips = document.createElement("div");
    chips.className = "apc-chip-row";
    chips.appendChild(criarChipApc(periodo.publico_alvo_label || "Publico nao informado"));
    chips.appendChild(criarChipApc(periodo.tipo_entrega_label || "Solicitacao geral"));
    chips.appendChild(criarChipApc(`Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`));

    if (detalhe) {
        chips.appendChild(
            criarChipApc(
                `${detalhe.total_enviados || 0}/${detalhe.total_elegiveis || 0} enviados`
            )
        );
    } else {
        chips.appendChild(
            criarChipApc(
                `${periodo.total_enviados || 0}/${periodo.total_elegiveis || 0} enviados`
            )
        );
    }
    body.appendChild(chips);

    if (periodo.observacao) {
        const observacao = document.createElement("p");
        observacao.className = "apc-inline-observacao";
        observacao.innerText = periodo.observacao;
        body.appendChild(observacao);
    }

    const nota = document.createElement("p");
    nota.className = "apc-accordion-note";
    nota.innerText = "Os detalhes completos dos professores aparecem logo abaixo.";
    body.appendChild(nota);

    return body;
}

async function removerArquivoApc(event) {
    const botao = event.currentTarget;
    const envioId = Number(botao?.dataset?.envioId || 0);
    const periodoId = Number(botao?.dataset?.periodoId || 0);
    if (!envioId) return;

    if (!window.confirm("Deseja remover este arquivo para enviar uma nova versao?")) {
        return;
    }

    botao.disabled = true;
    try {
        await fetchJson(`/apc/envios/${envioId}`, {
            method: "DELETE",
            headers: headersApc,
        });
        periodoSelecionadoApcId = periodoId || periodoSelecionadoApcId;
        setMensagemApc("Arquivo removido. Voce pode enviar novamente enquanto o prazo estiver aberto.");
        await carregarCalendarioApc();
    } catch (err) {
        botao.disabled = false;
        setMensagemApc(err.message || "Nao foi possivel remover o arquivo.", true);
    }
}

function criarCardEnvioExistenteApc(periodo, item) {
    const envio = item?.envio;
    if (!envio?.id) return null;

    const envioCard = document.createElement("div");
    envioCard.className = "apc-envio-card";

    const arquivo = document.createElement("div");
    arquivo.className = "apc-envio-card-topo";
    const icone = document.createElement("span");
    icone.className = "apc-file-icon";
    icone.setAttribute("aria-hidden", "true");
    const copia = document.createElement("div");
    const nome = document.createElement("strong");
    nome.className = "apc-envio-nome";
    nome.innerText = nomeArquivoPrincipalApc(envio);
    const enviadoEm = document.createElement("p");
    enviadoEm.className = "apc-envio-meta";
    enviadoEm.innerText = `Enviado em ${formatarDataHoraApc(envio.enviado_em)}`;
    copia.append(nome, enviadoEm);
    arquivo.append(icone, copia);
    envioCard.appendChild(arquivo);

    const guidance = criarOrientacaoRevisaoApc(envio);
    if (guidance) {
        envioCard.appendChild(guidance);
    }

    const acoes = document.createElement("div");
    acoes.className = "apc-inline-actions apc-envio-actions";

    acoes.appendChild(criarBotaoVisualizarApc(envio));

    envioCard.appendChild(acoes);

    if (periodo?.prazo_expirado) {
        const aviso = document.createElement("p");
        aviso.className = "apc-inline-hint";
        aviso.innerText = "O prazo foi encerrado. Este anexo permanece apenas para consulta.";
        envioCard.appendChild(aviso);
    }

    return envioCard;
}

function criarCardEntregaProfessorApc(periodo, item, indice = 0, total = 1) {
    const card = document.createElement("article");
    card.className = "apc-professor-card";
    card.classList.add(
        item.enviado ? "is-enviado" : (periodo.prazo_expirado ? "is-fechado" : "is-pendente")
    );

    const topo = document.createElement("div");
    topo.className = "apc-professor-topo";
    const copia = document.createElement("div");
    copia.className = "apc-professor-topo-copy";
    const aulas = [...new Set((item.horarios || [])
        .map((horario) => Number(horario.aula_numero || 0))
        .filter(Boolean))].sort((a, b) => a - b);
    if (aulas.length) {
        const aula = document.createElement("p");
        aula.className = "apc-lesson-label";
        aula.innerText = aulas.map((numero) => `${numero}ª aula`).join(" · ");
        copia.appendChild(aula);
    }
    const titulo = document.createElement("h4");
    titulo.innerText = item.disciplina_nome || "Entrega geral";
    copia.appendChild(titulo);
    if (item.turma_nome) {
        const turma = document.createElement("p");
        turma.className = "apc-professor-turma";
        turma.innerText = item.turma_nome;
        copia.appendChild(turma);
    }
    topo.appendChild(copia);
    const review = statusRevisaoEnvioApc(item.envio);
    topo.appendChild(
        item.enviado
            ? criarStatusApc(review.texto, review.tipo)
            : (periodo.prazo_expirado ? criarStatusApc("Prazo encerrado", "closed") : criarStatusApc("Pendente"))
    );
    card.appendChild(topo);

    const envioExistente = item.envio?.id ? criarCardEnvioExistenteApc(periodo, item) : null;
    if (envioExistente) card.appendChild(envioExistente);

    if (periodo.prazo_expirado) {
        return card;
    }

    const form = document.createElement("form");
    form.className = "apc-form apc-inline-form";
    form.dataset.periodoId = String(periodo.id);
    form.dataset.turmaId = String(item.turma_id || 0);
    form.dataset.disciplinaId = String(item.disciplina_id || 0);
    form.setAttribute("aria-label", `Local de envio do anexo ${indice + 1} de ${total}`);
    form.hidden = Boolean(item.envio?.id);

    const inputId = `apcArquivo-${periodo.id}-${item.turma_id || 0}-${item.disciplina_id || 0}`;
    const input = document.createElement("input");
    input.id = inputId;
    input.type = "file";
    input.required = true;
    input.name = "arquivo";

    const dropzone = document.createElement("label");
    dropzone.className = "apc-upload-dropzone";
    dropzone.htmlFor = inputId;
    const icon = document.createElement("i");
    icon.className = "bi bi-paperclip apc-upload-icon";
    icon.setAttribute("aria-hidden", "true");
    const uploadTitle = document.createElement("strong");
    uploadTitle.className = "apc-upload-title";
    uploadTitle.innerText = item.envio?.id ? "Selecionar arquivo corrigido" : "Selecionar arquivo";
    const uploadCopy = document.createElement("span");
    uploadCopy.className = "apc-upload-copy";
    uploadCopy.innerText = "Arraste e solte ou clique para procurar";
    const fileName = document.createElement("span");
    fileName.className = "apc-upload-file-name";
    fileName.innerText = "Nenhum arquivo selecionado";
    dropzone.append(icon, uploadTitle, uploadCopy, fileName, input);
    form.appendChild(dropzone);

    input.addEventListener("change", () => {
        fileName.innerText = input.files?.[0]?.name || "Nenhum arquivo selecionado";
    });

    const dica = document.createElement("p");
    dica.className = "apc-inline-hint";
    dica.innerText = item.envio?.id
        ? "O novo arquivo substituirá o envio atual."
        : `Local de envio para ${item.disciplina_nome || "esta aula"}.`;
    form.appendChild(dica);

    const actions = document.createElement("div");
    actions.className = "apc-delivery-actions";

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "btn-destaque";
    submit.innerText = item.envio?.id ? "Substituir arquivo" : "Enviar arquivo";
    actions.appendChild(submit);

    const create = document.createElement("button");
    create.type = "button";
    create.className = "apc-create-activity-button";
    create.innerText = "Criar atividade";
    actions.appendChild(create);

    if (item.envio?.id) {
        const remover = document.createElement("button");
        remover.type = "button";
        remover.className = "btn-perigo apc-remove-file";
        remover.dataset.envioId = String(item.envio.id);
        remover.dataset.periodoId = String(periodo.id || 0);
        remover.innerText = "Remover envio atual";
        remover.addEventListener("click", removerArquivoApc);
        actions.appendChild(remover);
    }
    form.appendChild(actions);

    form.addEventListener("submit", enviarArquivoApc);
    card.appendChild(form);

    if (envioExistente && !periodo.prazo_expirado) {
        const alternar = document.createElement("button");
        alternar.type = "button";
        alternar.className = "apc-replace-toggle";
        alternar.innerText = "Corrigir envio";
        alternar.setAttribute("aria-expanded", "false");
        alternar.addEventListener("click", () => {
            form.hidden = !form.hidden;
            alternar.innerText = form.hidden ? "Corrigir envio" : "Cancelar correção";
            alternar.setAttribute("aria-expanded", form.hidden ? "false" : "true");
            if (!form.hidden) input.focus();
        });
        envioExistente.querySelector(".apc-envio-actions")?.appendChild(alternar);
    }
    create.addEventListener("click", () => {
        void abrirModalAtividadeApc(periodo, item, create);
    });
    return card;
}

function criarCampoEditorApc(rotulo, elemento) {
    const label = document.createElement("label");
    label.className = "apc-activity-field";
    const span = document.createElement("span");
    span.innerText = rotulo;
    label.appendChild(span);
    label.appendChild(elemento);
    return label;
}

function executarComandoEditorApc(editor, comando) {
    editor.focus();
    document.execCommand("styleWithCSS", false, false);
    document.execCommand(comando, false);
}

function imagemSelecionadaEditorApc(editor) {
    return editor.querySelector("img.is-selected");
}

function selecionarImagemEditorApc(editor, imagem) {
    editor.querySelectorAll("img.is-selected").forEach((item) => item.classList.remove("is-selected"));
    if (imagem) imagem.classList.add("is-selected");
    const controles = editor.parentElement?.querySelector(".apc-rich-image-controls");
    if (controles) controles.hidden = !imagem;
}

function notificarMudancaEditorApc(editor) {
    editor.dispatchEvent(new Event("input", { bubbles: true }));
}

async function enviarImagemEditorApc(arquivo) {
    const form = new FormData();
    form.append("arquivo", arquivo);
    return fetchJson("/apc/atividade/imagens", {
        method: "POST",
        headers: headersApc,
        body: form,
    });
}

async function carregarImagemProtegidaEditorApc(image) {
    const token = image?.dataset?.apcImage;
    if (!token) return;
    const response = await fetchResposta(`/apc/atividade/imagens/${encodeURIComponent(token)}`, {
        headers: headersApc,
    });
    const objectUrl = URL.createObjectURL(await response.blob());
    const previous = image.dataset.objectUrl;
    if (previous) URL.revokeObjectURL(previous);
    image.dataset.objectUrl = objectUrl;
    image.src = objectUrl;
}

function hidratarImagensEditorApc(editor) {
    editor.querySelectorAll("img[data-apc-image]").forEach((image) => {
        void carregarImagemProtegidaEditorApc(image).catch(() => {
            image.alt = "Imagem indisponivel";
            image.classList.add("is-unavailable");
        });
    });
}

function criarAreaRichTextApc(rotulo, placeholder) {
    const wrap = document.createElement("div");
    wrap.className = "apc-activity-field";
    const label = document.createElement("span");
    label.innerText = rotulo;
    wrap.appendChild(label);
    const toolbar = document.createElement("div");
    toolbar.className = "apc-rich-toolbar";
    toolbar.setAttribute("role", "toolbar");
    toolbar.setAttribute("aria-label", `Formatacao de ${rotulo.toLowerCase()}`);
    const editor = document.createElement("div");
    editor.className = "apc-rich-editor";
    editor.contentEditable = "true";
    editor.dataset.placeholder = placeholder;
    editor.setAttribute("role", "textbox");
    editor.setAttribute("aria-multiline", "true");
    let insertionRange = null;
    let enviandoImagens = false;
    [
        ["Negrito", "bold", "<strong>B</strong>"],
        ["Itálico", "italic", "<em>I</em>"],
        ["Sublinhado", "underline", "<u>U</u>"],
        ["Lista", "insertUnorderedList", '<i class="bi bi-list-ul" aria-hidden="true"></i>'],
        ["Numeração", "insertOrderedList", '<i class="bi bi-list-ol" aria-hidden="true"></i>'],
        ["Limpar", "removeFormat", '<i class="bi bi-eraser" aria-hidden="true"></i>'],
    ].forEach(([texto, comando, icone]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.innerHTML = icone;
        button.setAttribute("aria-label", texto);
        button.title = texto;
        button.addEventListener("mousedown", (event) => event.preventDefault());
        button.addEventListener("click", () => executarComandoEditorApc(editor, comando));
        toolbar.appendChild(button);
    });
    [
        ["Esquerda", "justifyLeft", "text-left"],
        ["Centro", "justifyCenter", "text-center"],
        ["Direita", "justifyRight", "text-right"],
        ["Justificar", "justifyFull", "justify"],
    ].forEach(([texto, comando, icone]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.innerHTML = `<i class="bi bi-${icone}" aria-hidden="true"></i>`;
        button.setAttribute("aria-label", texto);
        button.title = `${texto} o paragrafo selecionado`;
        button.addEventListener("mousedown", (event) => event.preventDefault());
        button.addEventListener("click", () => executarComandoEditorApc(editor, comando));
        toolbar.appendChild(button);
    });
    const imageInput = document.createElement("input");
    imageInput.type = "file";
    imageInput.accept = "image/jpeg,image/png,image/webp";
    imageInput.multiple = true;
    imageInput.hidden = true;
    const imageButton = document.createElement("button");
    imageButton.type = "button";
    imageButton.innerHTML = '<i class="bi bi-image" aria-hidden="true"></i> Imagem';
    imageButton.title = "Inserir imagem (PNG, JPEG ou WebP, ate 5 MB)";
    imageButton.addEventListener("mousedown", (event) => {
        event.preventDefault();
        const selection = window.getSelection();
        if (selection?.rangeCount && editor.contains(selection.anchorNode)) {
            insertionRange = selection.getRangeAt(0).cloneRange();
        }
    });
    imageButton.addEventListener("click", () => imageInput.click());

    async function inserirImagensNoEditorApc(arquivos) {
        if (enviandoImagens) {
            setMensagemActivityModalApc("Aguarde o envio das imagens atuais.", true);
            return;
        }
        const disponiveis = Math.max(
            0,
            10 - editor.querySelectorAll("img[data-apc-image]").length
        );
        const imagens = Array.from(arquivos || [])
            .filter((arquivo) => String(arquivo.type || "").startsWith("image/"))
            .slice(0, disponiveis);
        if (!imagens.length) {
            setMensagemActivityModalApc("A APC pode conter no maximo 10 imagens.", true);
            return;
        }
        enviandoImagens = true;
        imageButton.disabled = true;
        imageButton.innerText = "Enviando...";
        let inseridas = 0;
        let erroEnvio = "";
        try {
            for (const arquivo of imagens) {
                try {
                    const uploaded = await enviarImagemEditorApc(arquivo);
                    const image = document.createElement("img");
                    image.dataset.apcImage = uploaded.token;
                    image.alt = arquivo.name || "Imagem colada da area de transferencia";
                    image.dataset.width = "50";
                    image.dataset.align = "center";
                    image.draggable = false;
                    if (insertionRange && editor.contains(insertionRange.commonAncestorContainer)) {
                        insertionRange.deleteContents();
                        insertionRange.insertNode(image);
                        insertionRange.setStartAfter(image);
                        insertionRange.collapse(true);
                    } else {
                        editor.appendChild(image);
                    }
                    selecionarImagemEditorApc(editor, image);
                    await carregarImagemProtegidaEditorApc(image);
                    inseridas += 1;
                } catch (err) {
                    erroEnvio = err.message || "Uma das imagens nao pode ser inserida.";
                }
            }
            if (inseridas) notificarMudancaEditorApc(editor);
            const excedeuLimite = Array.from(arquivos || []).length > imagens.length;
            if (erroEnvio) {
                setMensagemActivityModalApc(erroEnvio, true);
            } else if (excedeuLimite) {
                setMensagemActivityModalApc(
                    `${inseridas} imagem(ns) inserida(s). O limite da APC e de 10 imagens.`,
                    true
                );
            } else {
                setMensagemActivityModalApc(`${inseridas} imagem(ns) inserida(s).`);
            }
        } finally {
            enviandoImagens = false;
            insertionRange = null;
            imageButton.disabled = false;
            imageButton.innerHTML = '<i class="bi bi-image" aria-hidden="true"></i> Imagem';
        }
    }

    imageInput.addEventListener("change", async () => {
        const arquivos = Array.from(imageInput.files || []);
        imageInput.value = "";
        if (arquivos.length) await inserirImagensNoEditorApc(arquivos);
    });
    editor.addEventListener("paste", (event) => {
        const imagens = Array.from(event.clipboardData?.items || [])
            .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
            .map((item) => item.getAsFile())
            .filter(Boolean);
        if (!imagens.length) return;
        event.preventDefault();
        const selection = window.getSelection();
        insertionRange = selection?.rangeCount && editor.contains(selection.anchorNode)
            ? selection.getRangeAt(0).cloneRange()
            : null;
        void inserirImagensNoEditorApc(imagens);
    });
    toolbar.append(imageButton, imageInput);

    const imageControls = document.createElement("span");
    imageControls.className = "apc-rich-image-controls";
    imageControls.hidden = true;
    [25, 50, 75, 100].forEach((width) => {
        const button = document.createElement("button");
        button.type = "button";
        button.innerText = `${width}%`;
        button.title = `Usar ${width}% da largura disponivel`;
        button.addEventListener("click", () => {
            const image = imagemSelecionadaEditorApc(editor);
            if (!image) return;
            image.dataset.width = String(width);
            notificarMudancaEditorApc(editor);
        });
        imageControls.appendChild(button);
    });
    [["Esq.", "left"], ["Centro", "center"], ["Dir.", "right"]].forEach(([labelText, align]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.innerText = labelText;
        button.addEventListener("click", () => {
            const image = imagemSelecionadaEditorApc(editor);
            if (!image) return;
            image.dataset.align = align;
            notificarMudancaEditorApc(editor);
        });
        imageControls.appendChild(button);
    });
    const removeImage = document.createElement("button");
    removeImage.type = "button";
    removeImage.innerText = "Remover imagem";
    removeImage.addEventListener("click", () => {
        const image = imagemSelecionadaEditorApc(editor);
        if (!image) return;
        if (image.dataset.objectUrl) URL.revokeObjectURL(image.dataset.objectUrl);
        image.remove();
        notificarMudancaEditorApc(editor);
    });
    imageControls.appendChild(removeImage);
    toolbar.appendChild(imageControls);
    editor.addEventListener("click", (event) => {
        const target = event.target instanceof Element ? event.target.closest("img") : null;
        selecionarImagemEditorApc(editor, target);
    });
    wrap.appendChild(toolbar);
    wrap.appendChild(editor);
    const imageHint = document.createElement("small");
    imageHint.className = "apc-rich-image-hint";
    imageHint.innerText = "Insira varias imagens pelo botao ou cole diretamente com Ctrl+V.";
    wrap.appendChild(imageHint);
    return { wrap, editor };
}

function payloadAtividadeApc(panel) {
    return {
        turma_id: Number(panel.dataset.turmaId || 0),
        disciplina_id: Number(panel.dataset.disciplinaId || 0),
        habilidade: panel.querySelector("[data-apc-activity-skill]")?.value || "",
        conteudo: panel.querySelector("[data-apc-activity-content]")?.value || "",
        corpo_html: panel.querySelector("[data-apc-activity-body]")?.innerHTML || "",
        activity_columns: Number(panel.querySelector("input[name='apcActivityColumns']:checked")?.value || 1),
    };
}

async function carregarAtividadeExistenteApc(panel) {
    const envioId = Number(panel.dataset.envioId || 0);
    if (!envioId || panel.dataset.activityLoaded === "true") return;
    panel.dataset.activityLoaded = "true";
    try {
        const activity = await fetchJson(`/apc/envios/${envioId}/atividade`, { headers: headersApc });
        const skillParts = [activity.habilidade_codigo_snapshot, activity.habilidade_descricao_snapshot].filter(Boolean);
        panel.querySelector("[data-apc-activity-skill]").value = skillParts.join(" - ");
        panel.querySelector("[data-apc-activity-content]").value = activity.conteudo_descricao_snapshot || "";
        panel.querySelector("[data-apc-activity-body]").innerHTML = [activity.introducao_html, activity.atividades_html].filter(Boolean).join("<p><br></p>");
        hidratarImagensEditorApc(panel.querySelector("[data-apc-activity-body]"));
        const columns = panel.querySelector(`input[name='apcActivityColumns'][value='${Number(activity.activity_columns || 1)}']`);
        if (columns) columns.checked = true;
    } catch (err) {
        if (Number(err?.status || 0) !== 404) {
            panel.dataset.activityLoaded = "false";
            setMensagemApc(err.message || "Nao foi possivel recuperar a APC gerada.", true);
        }
    }
}

function validarPayloadAtividadeApc(payload) {
    if (!String(payload.habilidade || "").trim()) return "Informe a habilidade da APC.";
    if (!String(payload.conteudo || "").trim()) return "Informe o conteudo relacionado.";
    const text = document.createElement("div");
    text.innerHTML = payload.corpo_html;
    if (!String(text.textContent || "").trim() && !text.querySelector("img")) {
        return "Informe o texto da APC ou insira uma imagem.";
    }
    return "";
}

function setEstadoPreviewAtividadeApc(texto = "", erro = false, discreto = false) {
    const state = el("apcActivityPreviewState");
    if (!state) return;
    state.innerText = texto;
    state.hidden = !texto;
    state.classList.toggle("is-error", Boolean(texto) && erro);
    state.classList.toggle("is-refreshing", Boolean(texto) && discreto && !erro);
}

function setMensagemActivityModalApc(texto = "", erro = false) {
    const message = el("apcActivityModalMessage");
    if (!message) return;
    message.innerText = texto;
    message.classList.toggle("is-error", Boolean(texto) && erro);
}

function setRotuloSalvarAtividadeApc(texto, icone = "stars") {
    const botao = el("btnSalvarActivityModalApc");
    if (!botao) return;
    botao.innerHTML = `<i class="bi bi-${icone}" aria-hidden="true"></i> ${texto}`;
}

function cancelarPreviewAtividadeApc() {
    window.clearTimeout(timerPreviewAtividadeApc);
    timerPreviewAtividadeApc = null;
    tokenPreviewAtividadeApc += 1;
    controllerPreviewAtividadeApc?.abort();
    controllerPreviewAtividadeApc = null;
}

async function renderizarPaginasAtividadeApc(pdfDocument, token) {
    const pages = el("apcActivityPreviewPages");
    const viewportElement = el("apcActivityPreviewViewport");
    if (!pages || !viewportElement || token !== tokenPreviewAtividadeApc) return;
    const total = Math.max(1, Number(pdfDocument.numPages || 1));
    paginaPreviewAtividadeApc = Math.min(Math.max(1, paginaPreviewAtividadeApc), total);
    const numero = paginaPreviewAtividadeApc;
    const page = await pdfDocument.getPage(numero);
    if (token !== tokenPreviewAtividadeApc) return;
    const availableWidth = Math.max(1, viewportElement.clientWidth - 36);
    const availableHeight = Math.max(1, viewportElement.clientHeight - 24);
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const base = page.getViewport({ scale: 1 });
    const cssScale = Math.min(availableWidth / base.width, availableHeight / base.height);
    const renderViewport = page.getViewport({ scale: cssScale * dpr });
    const figure = document.createElement("figure");
    figure.className = "apc-activity-preview-page";
    const canvas = document.createElement("canvas");
    canvas.width = Math.floor(renderViewport.width);
    canvas.height = Math.floor(renderViewport.height);
    canvas.style.width = `${Math.floor(renderViewport.width / dpr)}px`;
    canvas.style.height = `${Math.floor(renderViewport.height / dpr)}px`;
    canvas.setAttribute("aria-label", `Página ${numero} de ${total}`);
    const caption = document.createElement("figcaption");
    caption.innerText = `Página ${numero} de ${total}`;
    figure.append(canvas, caption);
    await page.render({ canvasContext: canvas.getContext("2d"), viewport: renderViewport }).promise;
    if (token === tokenPreviewAtividadeApc && numero === paginaPreviewAtividadeApc) {
        pages.replaceChildren(figure);
        el("apcActivityPageCount").innerText = `Página ${numero} de ${total} · A4`;
        el("btnApcActivityPreviewAnterior").disabled = numero <= 1;
        el("btnApcActivityPreviewProxima").disabled = numero >= total;
    }
}

function chaveCachePreviewAtividadeApc(panel, payload) {
    const body = document.createElement("div");
    body.innerHTML = payload.corpo_html || "";
    body.querySelectorAll("img[data-apc-image]").forEach((image) => {
        image.removeAttribute("src");
        image.removeAttribute("data-object-url");
        image.classList.remove("is-selected", "is-unavailable");
    });
    return JSON.stringify({
        periodo_id: Number(panel.dataset.periodoId || 0),
        ...payload,
        corpo_html: body.innerHTML,
    });
}

function armazenarCachePreviewAtividadeApc(chave, buffer) {
    cachePreviewAtividadeApc.delete(chave);
    cachePreviewAtividadeApc.set(chave, buffer.slice(0));
    while (cachePreviewAtividadeApc.size > LIMITE_CACHE_PREVIEW_APC) {
        cachePreviewAtividadeApc.delete(cachePreviewAtividadeApc.keys().next().value);
    }
}

async function atualizarPreviewAtividadeApc(panel) {
    const payload = payloadAtividadeApc(panel);
    if (!window.pdfjsLib) {
        setEstadoPreviewAtividadeApc("A pré-visualização não está disponível neste navegador.", true);
        return;
    }
    cancelarPreviewAtividadeApc();
    const token = tokenPreviewAtividadeApc;
    const chaveCache = chaveCachePreviewAtividadeApc(panel, payload);
    const paginasVisiveis = Boolean(el("apcActivityPreviewPages")?.children.length);
    setEstadoPreviewAtividadeApc("Atualizando...", false, paginasVisiveis);
    try {
        let buffer = cachePreviewAtividadeApc.get(chaveCache);
        if (buffer) {
            cachePreviewAtividadeApc.delete(chaveCache);
            cachePreviewAtividadeApc.set(chaveCache, buffer);
            buffer = buffer.slice(0);
        } else {
            controllerPreviewAtividadeApc = new AbortController();
            const response = await fetchResposta(`/apc/periodos/${panel.dataset.periodoId}/atividade/preview`, {
                method: "POST",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
                signal: controllerPreviewAtividadeApc.signal,
            });
            buffer = await (await response.blob()).arrayBuffer();
            armazenarCachePreviewAtividadeApc(chaveCache, buffer);
        }
        if (token !== tokenPreviewAtividadeApc) return;
        const pdfDocument = await window.pdfjsLib.getDocument({ data: buffer.slice(0) }).promise;
        if (token !== tokenPreviewAtividadeApc) return;
        documentoPreviewAtividadeApc = pdfDocument;
        await renderizarPaginasAtividadeApc(pdfDocument, token);
        if (token === tokenPreviewAtividadeApc) setEstadoPreviewAtividadeApc("");
    } catch (err) {
        if (err?.name !== "AbortError" && token === tokenPreviewAtividadeApc) {
            setEstadoPreviewAtividadeApc(err.message || "Não foi possível atualizar a prévia.", true);
        }
    } finally {
        if (token === tokenPreviewAtividadeApc) controllerPreviewAtividadeApc = null;
    }
}

function agendarPreviewAtividadeApc(panel, delay = 850) {
    cancelarPreviewAtividadeApc();
    timerPreviewAtividadeApc = window.setTimeout(() => void atualizarPreviewAtividadeApc(panel), delay);
}

async function abrirModalAtividadeApc(periodo, item, trigger) {
    const modal = el("apcActivityModal");
    const slot = el("apcActivityFormSlot");
    if (!modal || !slot) return;
    window.clearTimeout(timerFechamentoAtividadeApc);
    focoAntesAtividadeApc = trigger || document.activeElement;
    painelAtividadeApc = criarEditorAtividadeApc(periodo, item);
    documentoPreviewAtividadeApc = null;
    paginaPreviewAtividadeApc = 1;
    slot.replaceChildren(painelAtividadeApc);
    el("apcActivityModalTitle").innerText = item.envio?.id ? "Editar atividade" : "Geração de Atividades";
    const aulas = [...new Set((item.horarios || [])
        .map((horario) => Number(horario.aula_numero || 0))
        .filter(Boolean))].sort((a, b) => a - b);
    el("apcActivityModalDescription").innerText = [
        aulas.map((numero) => `${numero}ª aula`).join(" · "),
        item.disciplina_nome || "Disciplina",
        item.turma_nome || "Entrega geral",
    ].filter(Boolean).join(" · ");
    const saveButton = el("btnSalvarActivityModalApc");
    saveButton.disabled = false;
    setRotuloSalvarAtividadeApc(item.envio?.id ? "Salvar e substituir anexo" : "Gerar e anexar atividade");
    setMensagemActivityModalApc("O PDF será anexado automaticamente a esta entrega.");
    setEstadoPreviewAtividadeApc("Preparando a folha da atividade...");
    el("apcActivityPreviewPages").innerHTML = "";
    modal.hidden = false;
    bloquearScrollModalApc();
    window.requestAnimationFrame(() => {
        modal.classList.add("is-visible");
        focarSemRolagemApc(el("apcActivityModalPanel"));
    });
    await carregarAtividadeExistenteApc(painelAtividadeApc);
    agendarPreviewAtividadeApc(painelAtividadeApc, 0);
}

function fecharModalAtividadeApc() {
    const modal = el("apcActivityModal");
    if (!modal || modal.hidden) return;
    cancelarPreviewAtividadeApc();
    modal.classList.remove("is-visible");
    liberarScrollModalApc();
    timerFechamentoAtividadeApc = window.setTimeout(() => {
        modal.hidden = true;
        el("apcActivityFormSlot")?.replaceChildren();
        el("apcActivityPreviewPages")?.replaceChildren();
        documentoPreviewAtividadeApc = null;
        paginaPreviewAtividadeApc = 1;
        painelAtividadeApc = null;
        timerFechamentoAtividadeApc = null;
    }, 220);
    focarSemRolagemApc(focoAntesAtividadeApc);
    focoAntesAtividadeApc = null;
}

async function salvarAtividadeApc(event) {
    event.preventDefault();
    const panel = event.currentTarget;
    const payload = payloadAtividadeApc(panel);
    const error = validarPayloadAtividadeApc(payload);
    if (error) {
        setMensagemActivityModalApc(error, true);
        return;
    }
    if (panel.dataset.hasSubmission === "true" && !window.confirm("A APC gerada substituira o anexo atual desta disciplina. Deseja continuar?")) return;
    const submit = el("btnSalvarActivityModalApc");
    submit.disabled = true;
    setRotuloSalvarAtividadeApc("Salvando e anexando...", "arrow-repeat");
    try {
        await fetchJson(`/apc/periodos/${panel.dataset.periodoId}/atividade`, {
            method: "POST",
            headers: headersJsonApc,
            body: JSON.stringify(payload),
        });
        periodoSelecionadoApcId = Number(panel.dataset.periodoId);
        fecharModalAtividadeApc();
        setMensagemApc("APC gerada e anexada com sucesso.");
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemActivityModalApc(err.message || "Não foi possível gerar a APC.", true);
        submit.disabled = false;
        setRotuloSalvarAtividadeApc(panel.dataset.hasSubmission === "true" ? "Salvar e substituir anexo" : "Gerar e anexar atividade");
    }
}

function criarEditorAtividadeApc(periodo, item) {
    const panel = document.createElement("form");
    panel.className = "apc-activity-editor";
    panel.dataset.periodoId = String(periodo.id);
    panel.dataset.turmaId = String(item.turma_id || 0);
    panel.dataset.disciplinaId = String(item.disciplina_id || 0);
    panel.dataset.hasSubmission = String(Boolean(item.envio?.id));
    panel.dataset.envioId = String(item.envio?.id || 0);
    const skill = document.createElement("input");
    skill.type = "text";
    skill.maxLength = 2000;
    skill.required = true;
    skill.placeholder = "Selecione ou informe uma habilidade...";
    skill.dataset.apcActivitySkill = "true";
    panel.appendChild(criarCampoEditorApc("Habilidade", skill));
    const content = document.createElement("input");
    content.type = "text";
    content.maxLength = 1000;
    content.required = true;
    content.placeholder = "Ex.: Adição e subtração de números decimais";
    content.dataset.apcActivityContent = "true";
    panel.appendChild(criarCampoEditorApc("Conteúdo específico", content));
    const body = criarAreaRichTextApc("Corpo da atividade", "Organize livremente textos, leituras, pesquisas, orientações ou questões.");
    body.editor.dataset.apcActivityBody = "true";
    panel.appendChild(body.wrap);
    const layout = document.createElement("fieldset");
    layout.className = "apc-activity-layout";
    layout.innerHTML = `<legend>Layout do texto</legend><label><input type="radio" name="apcActivityColumns" value="1" checked><span>1 coluna<small>Leituras e textos longos</small></span></label><label><input type="radio" name="apcActivityColumns" value="2"><span>2 colunas<small>Blocos curtos e objetivos</small></span></label>`;
    panel.appendChild(layout);
    panel.addEventListener("input", () => agendarPreviewAtividadeApc(panel));
    panel.addEventListener("change", () => agendarPreviewAtividadeApc(panel, 150));
    panel.addEventListener("submit", salvarAtividadeApc);
    return panel;
}

function criarCorpoProfessorPeriodoApc(detalhe) {
    const body = document.createElement("div");
    body.className = "apc-accordion-body";

    if (!detalhe || !detalhe.periodo) {
        const vazio = document.createElement("p");
        vazio.className = "apc-accordion-note";
        vazio.innerText = "Abra esta pendencia para ver os detalhes e anexar o arquivo.";
        body.appendChild(vazio);
        return body;
    }

    const periodo = detalhe.periodo;

    if (periodo.observacao) {
        const observacao = document.createElement("div");
        observacao.className = "apc-inline-observacao";
        const titulo = document.createElement("strong");
        titulo.innerText = "Instruções da coordenação";
        const texto = document.createElement("p");
        texto.innerText = periodo.observacao;
        observacao.append(titulo, texto);
        body.appendChild(observacao);
    }

    if (!Array.isArray(detalhe.itens) || !detalhe.itens.length) {
        const vazio = document.createElement("p");
        vazio.className = "apc-accordion-note";
        vazio.innerText = periodo.publico_alvo === "PROFESSORES_SELECIONADOS"
            ? "Nenhuma disciplina foi vinculada a você nesta solicitação."
            : "Nenhuma disciplina vinculada a esta solicitação para o seu horário.";
        body.appendChild(vazio);
        return body;
    }

    const itensOrdenados = [...detalhe.itens].sort((a, b) => {
        const primeiraAula = (item) => Math.min(
            ...(item.horarios || []).map((horario) => Number(horario.aula_numero || 999))
        );
        return primeiraAula(a) - primeiraAula(b)
            || String(a.disciplina_nome || "").localeCompare(String(b.disciplina_nome || ""), "pt-BR");
    });

    const grid = document.createElement("div");
    grid.className = "apc-professor-card-grid";
    itensOrdenados.forEach((item, indice) => {
        grid.appendChild(criarCardEntregaProfessorApc(periodo, item, indice, itensOrdenados.length));
    });
    body.appendChild(grid);

    return body;
}

function ordenarSolicitacoesDocenteApc(periodos) {
    return [...(periodos || [])].sort((a, b) => {
        const aPendente = !a.enviado && !a.prazo_expirado ? 0 : 1;
        const bPendente = !b.enviado && !b.prazo_expirado ? 0 : 1;
        if (aPendente !== bPendente) return aPendente - bPendente;
        return String(a.prazo_envio || "").localeCompare(String(b.prazo_envio || ""));
    });
}

function renderSolicitacoesDocenteApc(periodos) {
    const wrap = el("apcSolicitacoesData");
    wrap.innerHTML = "";

    if (!Array.isArray(periodos) || !periodos.length) {
        renderEstadoVazioApc(wrap, {
            icone: "bi-inbox",
            titulo: "Nenhuma entrega por enquanto",
            descricao: "Quando uma nova solicitação for enviada a você, ela aparecerá nesta lista.",
        });
        return;
    }

    ordenarSolicitacoesDocenteApc(periodos).forEach((periodo) => {
        const selecionado = Number(periodo.id) === Number(periodoSelecionadoApcId);
        const card = document.createElement("article");
        card.className = "apc-pendencia-card";
        if (selecionado) card.classList.add("is-selected");

        const topo = document.createElement("div");
        topo.className = "apc-pendencia-card-topo";

        const copia = document.createElement("div");
        copia.className = "apc-pendencia-card-copy";
        const titulo = document.createElement("h3");
        titulo.innerText = periodo.titulo || "Documento";
        copia.appendChild(titulo);

        const resumo = document.createElement("p");
        resumo.innerText = `Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`;
        copia.appendChild(resumo);
        topo.appendChild(copia);

        const status = statusResumoPeriodoApc(periodo);
        topo.appendChild(criarStatusApc(status.texto, status.tipo));
        card.appendChild(topo);

        const abrir = document.createElement("button");
        abrir.type = "button";
        abrir.className = selecionado ? "btn-destaque" : "";
        abrir.innerText = selecionado ? "Anexos abertos" : "Ver anexos";
        abrir.setAttribute("aria-pressed", selecionado ? "true" : "false");
        abrir.addEventListener("click", async () => {
            periodoSelecionadoApcId = Number(periodo.id);
            dataSelecionadaApc = periodo.data_referencia;
            await carregarDetalheSelecionadoApc();
            if (window.matchMedia("(max-width: 1120px)").matches) {
                const comportamento = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
                el("apcDocenteDetalhe")?.scrollIntoView({ behavior: comportamento, block: "start" });
            }
        });
        card.appendChild(abrir);
        wrap.appendChild(card);
    });
}

function renderDetalheDocenteApc(detalhe) {
    const painel = el("apcDocenteDetalhe");
    if (!painel) return;
    painel.innerHTML = "";

    if (!detalhe?.periodo) {
        renderEstadoVazioApc(painel, {
            icone: "bi-paperclip",
            titulo: "Tudo em dia",
            descricao: "Não há uma entrega aberta para mostrar neste momento.",
        });
        return;
    }

    const periodo = detalhe.periodo;
    const header = document.createElement("header");
    header.className = "apc-docente-detalhe-header";

    const copia = document.createElement("div");
    const titulo = document.createElement("h2");
    titulo.innerText = periodo.titulo || "Documento";
    copia.appendChild(titulo);

    const prazo = document.createElement("p");
    prazo.innerText = `${pluralizarApc(detalhe.total_entregas || 0, "anexo", "anexos")} · Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`;
    copia.appendChild(prazo);
    header.appendChild(copia);

    const status = statusResumoPeriodoApc(
        Object.assign({}, periodo, {
            enviado: Number(detalhe.total_pendentes || 0) === 0 && Number(detalhe.total_entregas || 0) > 0,
        })
    );
    header.appendChild(criarStatusApc(status.texto, status.tipo));
    painel.appendChild(header);
    painel.appendChild(criarCorpoProfessorPeriodoApc(detalhe));
}

function normalizarBuscaApc(valor) {
    return String(valor || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

function preencherFiltroGestaoApc(id, valores, rotuloTodos) {
    const select = el(id);
    if (!select) return;
    const valorAtual = select.value;
    select.innerHTML = "";
    const todos = document.createElement("option");
    todos.value = "";
    todos.innerText = rotuloTodos;
    select.appendChild(todos);
    [...new Set(valores.filter(Boolean))]
        .sort((a, b) => String(a).localeCompare(String(b), "pt-BR"))
        .forEach((valor) => {
            const option = document.createElement("option");
            option.value = valor;
            option.innerText = valor;
            select.appendChild(option);
        });
    select.value = Array.from(select.options).some((option) => option.value === valorAtual)
        ? valorAtual
        : "";
}

function atualizarOpcoesFiltrosGestaoApc(periodos) {
    preencherFiltroGestaoApc(
        "apcFiltroProfessor",
        periodos.flatMap((item) => item.professores || []),
        "Todos"
    );
    preencherFiltroGestaoApc(
        "apcFiltroDisciplina",
        periodos.flatMap((item) => item.disciplinas || []),
        "Todas"
    );
    preencherFiltroGestaoApc(
        "apcFiltroTurma",
        periodos.flatMap((item) => item.turmas || []),
        "Todas"
    );
}

function solicitacoesGestaoFiltradasApc() {
    const busca = normalizarBuscaApc(el("apcFiltroBusca")?.value);
    const professor = el("apcFiltroProfessor")?.value || "";
    const disciplina = el("apcFiltroDisciplina")?.value || "";
    const turma = el("apcFiltroTurma")?.value || "";
    const status = el("apcFiltroStatus")?.value || "";
    const ordenacao = el("apcOrdenacaoGestao")?.value || "prazo";

    const itens = (calendarioApc.periodos || []).filter((periodo) => {
        const textoBusca = normalizarBuscaApc([
            periodo.titulo,
            periodo.observacao,
            ...(periodo.professores || []),
            ...(periodo.disciplinas || []),
            ...(periodo.turmas || []),
        ].join(" "));
        if (busca && !textoBusca.includes(busca)) return false;
        if (professor && !(periodo.professores || []).includes(professor)) return false;
        if (disciplina && !(periodo.disciplinas || []).includes(disciplina)) return false;
        if (turma && !(periodo.turmas || []).includes(turma)) return false;
        if (status === "pendente" && Number(periodo.total_pendentes || 0) === 0) return false;
        if (status === "concluida" && Number(periodo.total_pendentes || 0) !== 0) return false;
        if (status === "atrasada" && !periodo.prazo_expirado) return false;
        return true;
    });

    return itens.sort((a, b) => {
        if (ordenacao === "recentes") {
            return String(b.data_referencia || "").localeCompare(String(a.data_referencia || ""));
        }
        if (ordenacao === "antigas") {
            return String(a.data_referencia || "").localeCompare(String(b.data_referencia || ""));
        }
        if (ordenacao === "envios_recentes") {
            return String(b.ultimo_envio_em || "").localeCompare(String(a.ultimo_envio_em || ""));
        }
        if (ordenacao === "envios_antigos") {
            const dataA = a.ultimo_envio_em || "9999";
            const dataB = b.ultimo_envio_em || "9999";
            return String(dataA).localeCompare(String(dataB));
        }
        if (ordenacao === "pendencias") {
            return Number(b.total_pendentes || 0) - Number(a.total_pendentes || 0);
        }
        return String(a.prazo_envio || "").localeCompare(String(b.prazo_envio || ""));
    });
}

function renderSolicitacoesGestaoApc() {
    const wrap = el("apcSolicitacoesData");
    const periodos = solicitacoesGestaoFiltradasApc();
    atualizarFiltroMobileApc();
    wrap.innerHTML = "";

    if (!periodos.length) {
        const possuiSolicitacoes = Boolean((calendarioApc.periodos || []).length);
        renderEstadoVazioApc(wrap, possuiSolicitacoes
            ? {
                icone: "bi-search",
                titulo: "Nenhum resultado",
                descricao: "Revise a busca ou limpe os filtros para ver todas as solicitações.",
                acao: "Limpar filtros",
                aoClicar: limparFiltrosGestaoApc,
            }
            : {
                icone: "bi-file-earmark-plus",
                titulo: "Nenhuma solicitação criada",
                descricao: "Crie a primeira solicitação para começar a receber anexos dos professores.",
                acao: "Criar solicitação",
                aoClicar: () => el("btnAbrirNovaApc")?.click(),
            });
        return;
    }

    periodos.forEach((periodo) => {
        const selecionado = Number(periodo.id) === Number(periodoSelecionadoApcId);
        const card = document.createElement("article");
        card.className = "apc-pendencia-card apc-demanda-gestao-card";
        if (selecionado) card.classList.add("is-selected");

        const topo = document.createElement("div");
        topo.className = "apc-pendencia-card-topo";
        const copia = document.createElement("div");
        copia.className = "apc-pendencia-card-copy";
        const titulo = document.createElement("h3");
        titulo.innerText = periodo.titulo || "Documento";
        const resumo = document.createElement("p");
        resumo.innerText =
            `${periodo.total_enviados || 0}/${periodo.total_elegiveis || 0} entregas enviadas`;
        copia.append(titulo, resumo);
        topo.appendChild(copia);
        const status = statusResumoPeriodoApc(periodo, true);
        topo.appendChild(criarStatusApc(status.texto, status.tipo));
        card.appendChild(topo);

        const meta = document.createElement("div");
        meta.className = "apc-pendencia-card-meta";
        meta.appendChild(criarMetaApc(paraDataBr(periodo.data_referencia)));
        meta.appendChild(criarMetaApc(`Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`));
        meta.appendChild(criarMetaApc(
            pluralizarApc((periodo.professores || []).length, "professor", "professores")
        ));
        card.appendChild(meta);

        const abrir = document.createElement("button");
        abrir.type = "button";
        abrir.className = selecionado ? "btn-destaque" : "";
        abrir.innerText = selecionado ? "Demanda aberta" : "Analisar professores";
        abrir.addEventListener("click", async () => {
            periodoSelecionadoApcId = Number(periodo.id);
            dataSelecionadaApc = periodo.data_referencia;
            dataSelecionadaManualmenteApc = true;
            await carregarDetalheSelecionadoApc();
            if (window.matchMedia("(max-width: 1120px)").matches) {
                const comportamento = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
                el("apcGestaoDetalhe")?.scrollIntoView({ behavior: comportamento, block: "start" });
            }
        });
        card.appendChild(abrir);
        wrap.appendChild(card);
    });
}

function atualizarFiltroMobileApc() {
    const botao = el("btnAlternarFiltrosApc");
    const filtros = el("apcGestaoFiltros");
    if (!botao || !filtros) return;
    const ativos = [
        el("apcFiltroBusca")?.value,
        el("apcFiltroProfessor")?.value,
        el("apcFiltroDisciplina")?.value,
        el("apcFiltroTurma")?.value,
        el("apcFiltroStatus")?.value,
    ].filter(Boolean).length;
    botao.innerText = ativos ? `Filtros (${ativos})` : "Filtros";
    botao.setAttribute("aria-expanded", filtros.classList.contains("is-mobile-open") ? "true" : "false");
}

function limparFiltrosGestaoApc() {
    ["apcFiltroBusca", "apcFiltroProfessor", "apcFiltroDisciplina", "apcFiltroTurma", "apcFiltroStatus"]
        .forEach((id) => {
            const campo = el(id);
            if (campo) campo.value = "";
        });
    if (el("apcOrdenacaoGestao")) el("apcOrdenacaoGestao").value = "prazo";
    renderSolicitacoesGestaoApc();
    el("apcFiltroBusca")?.focus();
}

function renderSolicitacoesData(periodos, detalheSelecionado = null) {
    const wrap = el("apcSolicitacoesData");
    wrap.innerHTML = "";

    if (modoDocenteAtivoApc()) {
        renderSolicitacoesDocenteApc(periodos);
        return;
    }
    renderSolicitacoesGestaoApc();
}

function renderListaGestaoApc(detalhe) {
    const lista = el("apcListaPainel");
    lista.innerHTML = "";
    const periodo = detalhe?.periodo || null;
    if (el("apcGestaoDetalheTitulo")) {
        el("apcGestaoDetalheTitulo").innerText = periodo?.titulo || "Selecione uma demanda";
    }
    if (el("apcGestaoDetalheDescricao")) {
        el("apcGestaoDetalheDescricao").innerText = periodo
            ? `${paraDataBr(periodo.data_referencia)} · Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`
            : "Os professores e anexos da solicitação aparecerão aqui.";
    }

    if (!detalhe || !Array.isArray(detalhe.itens) || detalhe.itens.length === 0) {
        renderEstadoVazioApc(lista, {
            icone: "bi-people",
            titulo: "Nenhum professor vinculado",
            descricao: "Esta solicitação ainda não possui professores elegíveis para a entrega.",
        });
        return;
    }

    const grupos = agruparItensGestaoPorProfessor(detalhe.itens);
    const periodoId = Number(periodo?.id || periodoSelecionadoApcId || 0);
    const professoresAbertos = professoresAbertosPorPeriodoApc.get(periodoId) || new Set();
    const wrap = document.createElement("div");
    wrap.className = "apc-professor-group-list";

    grupos.forEach((grupo) => {
        const details = document.createElement("details");
        details.className = "apc-professor-group";
        details.open = professoresAbertos.has(Number(grupo.professor_id));
        details.addEventListener("toggle", () => {
            const abertos = professoresAbertosPorPeriodoApc.get(periodoId) || new Set();
            if (details.open) {
                abertos.add(Number(grupo.professor_id));
            } else {
                abertos.delete(Number(grupo.professor_id));
            }
            professoresAbertosPorPeriodoApc.set(periodoId, abertos);
        });

        const summary = document.createElement("summary");
        summary.className = "apc-professor-group-summary";

        const main = document.createElement("div");
        main.className = "apc-professor-group-main";
        main.innerHTML = `
            <h4>${grupo.professor_nome}</h4>
            <p>${grupo.professor_email || "Sem e-mail"}</p>
        `;
        const meta = document.createElement("div");
        meta.className = "apc-professor-group-meta";
        meta.innerText =
            `${grupo.total_enviadas}/${grupo.total_entregas} entregas enviadas | `
            + pluralizarApc(grupo.total_pendentes, "pendência", "pendências");
        main.appendChild(meta);
        summary.appendChild(main);

        const side = document.createElement("div");
        side.className = "apc-professor-group-side";
        if (grupo.total_ajustes > 0) {
            side.appendChild(criarStatusApc("Realizar ajuste", "adjustment"));
        } else if (
            grupo.total_entregas > 0
            && grupo.total_impressas === grupo.total_entregas
        ) {
            side.appendChild(criarStatusApc("Impresso", "printed"));
        } else if (
            grupo.total_entregas > 0
            && grupo.total_aprovadas === grupo.total_entregas
        ) {
            side.appendChild(criarStatusApc("Aprovado", "ok"));
        } else if (grupo.total_pendentes === 0) {
            side.appendChild(criarStatusApc("Aguardando analise"));
        } else {
            side.appendChild(criarStatusApc("Pendente"));
        }
       
        summary.appendChild(side);
        details.appendChild(summary);

        const body = document.createElement("div");
        body.className = "apc-professor-group-body";

        if (grupo.turmas.length || grupo.disciplinas.length) {
            const chips = document.createElement("div");
            chips.className = "apc-chip-row";
            grupo.turmas.forEach((turma) => chips.appendChild(criarChipApc(turma)));
            grupo.disciplinas.forEach((disciplina) => chips.appendChild(criarChipApc(disciplina)));
            body.appendChild(chips);
        }

        const entregas = document.createElement("div");
        entregas.className = "apc-professor-entrega-list";
        grupo.entregas.forEach((item) => {
            const card = document.createElement("article");
            card.className = "apc-entrega-item";

            const topo = document.createElement("div");
            topo.className = "apc-entrega-topo";
            const titulo = item.disciplina_nome
                ? `${item.disciplina_nome}${item.turma_nome ? ` - ${item.turma_nome}` : ""}`
                : "Entrega geral";
            topo.innerHTML = `<div><h5>${titulo}</h5></div>`;
            const review = statusRevisaoEnvioApc(item.envio);
            topo.appendChild(
                item.enviado
                    ? criarStatusApc(review.texto, review.tipo)
                    : criarStatusApc("Pendente")
            );
            card.appendChild(topo);


            if ((item.horarios || []).length) {
                const horarios = document.createElement("ul");
                horarios.className = "apc-horarios-lista";
                (item.horarios || []).forEach((horario) => {
                    const li = document.createElement("li");
                    li.innerText = `${horario.aula_numero}a aula - ${horario.turma_nome} - ${horario.disciplina_nome}`;
                    horarios.appendChild(li);
                });
                card.appendChild(horarios);
            }

            if (item.envio?.id) {
                const enviadoEm = document.createElement("p");
                enviadoEm.className = "apc-envio-meta";
                enviadoEm.innerText = `Enviado em ${formatarDataHoraApc(item.envio.enviado_em)}`;
                card.appendChild(enviadoEm);

                const guidance = criarOrientacaoRevisaoApc(item.envio);
                if (guidance) {
                    card.appendChild(guidance);
                }

                const acoes = document.createElement("div");
                acoes.className = "apc-inline-actions";
                acoes.appendChild(criarBotaoVisualizarApc(item.envio));
                const baixar = document.createElement("button");
                baixar.type = "button";
                baixar.innerText = "Baixar arquivo";
                baixar.addEventListener("click", async () => {
                    await baixarArquivoApc(item.envio);
                });
                acoes.appendChild(baixar);
                card.appendChild(acoes);
            }

            entregas.appendChild(card);
        });
        body.appendChild(entregas);
        details.appendChild(body);
        wrap.appendChild(details);
    });

    lista.appendChild(wrap);
}

function preencherMetaPreviewArquivoApc(envio) {
    const meta = el("apcArquivoPreviewMeta");
    meta.innerHTML = `
        <h4>${envio.arquivo_nome_original || "Arquivo enviado"}</h4>
        <p>${envio.professor_nome || "Professor"}${envio.professor_email ? ` • ${envio.professor_email}` : ""}</p>
        <p>${envio.disciplina_nome || "Entrega geral"}${envio.turma_nome ? ` • ${envio.turma_nome}` : ""}</p>
        <p>Enviado em ${formatarDataHoraApc(envio.enviado_em)}</p>
    `;
}

function preencherMetaPreviewArquivoApcClaro(envio) {
    const nomeSistema = nomeArquivoPadronizadoDivergeApc(envio)
        ? `<p>Salvo no sistema como: ${nomeArquivoSistemaApc(envio)}</p>`
        : "";
    const meta = el("apcArquivoPreviewMeta");
    meta.innerHTML = `
        <h4>${nomeArquivoPrincipalApc(envio)}</h4>
        ${nomeSistema}
        <p>${envio.professor_nome || "Professor"}${envio.professor_email ? ` • ${envio.professor_email}` : ""}</p>
        <p>${envio.disciplina_nome || "Entrega geral"}${envio.turma_nome ? ` • ${envio.turma_nome}` : ""}</p>
        <p>Enviado em ${formatarDataHoraApc(envio.enviado_em)}</p>
    `;
}

function preencherMetaModalPreviewApc(envio) {
    const meta = el("apcArquivoPreviewMeta");
    if (!meta) return;
    meta.innerHTML = "";

    const titulo = document.createElement("h2");
    titulo.id = "apcArquivoPreviewTitulo";
    titulo.innerText = nomeArquivoPrincipalApc(envio);
    meta.appendChild(titulo);

    const tamanho = Number(envio.arquivo_tamanho || 0);
    const tamanhoTexto = tamanho >= 1048576
        ? `${(tamanho / 1048576).toFixed(1)} MB`
        : tamanho >= 1024
            ? `${Math.ceil(tamanho / 1024)} KB`
            : `${tamanho} bytes`;
    const arquivoInfo = document.createElement("p");
    arquivoInfo.innerText = [tamanhoTexto, String(envio.arquivo_tipo || "Arquivo").split("/").pop()?.toUpperCase()].filter(Boolean).join(" · ");
    meta.appendChild(arquivoInfo);

    const historico = el("apcReviewHistory");
    if (historico) {
        historico.innerHTML = "";
        historico.appendChild(
            criarEventoHistoricoApc(
                "Envio realizado",
                `Professor: ${envio.professor_nome || "Professor"}`,
                envio.enviado_em
            )
        );

        const tituloRevisao = tituloHistoricoRevisaoApc(envio.review_status);
        if (tituloRevisao && envio.reviewed_at) {
            const responsavel = nomeResponsavelRevisaoApc(envio);
            historico.appendChild(
                criarEventoHistoricoApc(
                    tituloRevisao,
                    responsavel ? `Por ${responsavel}` : "",
                    envio.reviewed_at
                )
            );
        }
    }

    if (el("apcArquivoPreviewTopbarTitle")) {
        el("apcArquivoPreviewTopbarTitle").innerText = modoGestaoAtivoApc()
            ? "Revisar envio"
            : "Visualizar envio";
    }
    if (el("apcArquivoPreviewContext")) {
        el("apcArquivoPreviewContext").innerText = [
            envio.disciplina_nome || "Entrega geral",
            envio.turma_nome || "",
            envio.professor_nome || "",
        ].filter(Boolean).join(" · ");
    }
}

function setMensagemReviewApc(texto, erro = false) {
    const mensagem = el("apcReviewMessageState");
    if (!mensagem) return;
    mensagem.innerText = texto || "";
    mensagem.classList.toggle("is-error", Boolean(texto) && erro);
    mensagem.classList.toggle("is-success", Boolean(texto) && !erro);
}

function atualizarEstadoFormularioReviewApc() {
    const status = el("apcReviewStatus")?.value || "PENDENTE";
    const mensagem = el("apcReviewMessage");
    const submit = el("btnSalvarReviewApc");
    const solicitandoAjuste = status === "AJUSTE_SOLICITADO";
    if (mensagem) {
        mensagem.required = solicitandoAjuste;
        mensagem.disabled = !solicitandoAjuste;
    }
    if (!submit) return;
    const texto = solicitandoAjuste ? "Solicitar ajuste" : "Aprovar envio";
    const icone = solicitandoAjuste ? "flag" : "patch-check";
    submit.innerHTML = `<i class="bi bi-${icone}" aria-hidden="true"></i> ${texto}`;
    submit.classList.toggle("is-warning", solicitandoAjuste);
}

function renderReviewPanelApc(envio) {
    const panel = el("apcReviewPanel");
    const summary = el("apcReviewSummary");
    const form = el("formApcReview");
    if (!panel || !summary || !form || !envio?.id) return;

    const review = statusRevisaoEnvioApc(envio);
    panel.hidden = false;
    summary.innerHTML = "";
    const topbarStatus = el("apcArquivoPreviewTopbarStatus");
    if (topbarStatus) {
        const statusVisual = criarStatusApc(review.texto, review.tipo);
        topbarStatus.className = statusVisual.className;
        topbarStatus.innerText = review.texto;
    }

    const guidance = criarOrientacaoRevisaoApc(envio);
    if (guidance) {
        summary.appendChild(guidance);
    }

    const gestaoAtiva = modoGestaoAtivoApc();
    form.hidden = !gestaoAtiva;
    el("btnSalvarReviewApc").hidden = !gestaoAtiva;
    if (gestaoAtiva) {
        const decisao = ["APROVADO", "AJUSTE_SOLICITADO"].includes(review.status)
            ? review.status
            : "APROVADO";
        el("apcReviewStatus").value = decisao;
        const radio = form.querySelector(`input[name="apcReviewDecision"][value="${decisao}"]`);
        if (radio) radio.checked = true;
        el("apcReviewMessage").value = String(envio.review_message || "");
        atualizarEstadoFormularioReviewApc();
    }
    setMensagemReviewApc("");
}

async function salvarRevisaoApc(event) {
    event.preventDefault();
    if (!envioPreviewApc?.id || !modoGestaoAtivoApc()) return;

    const submit = el("btnSalvarReviewApc");
    if (submit) submit.disabled = true;
    setMensagemReviewApc("Salvando revisao...");
    try {
        const updated = await fetchJson(
            `/apc/envios/${envioPreviewApc.id}/revisao`,
            {
                method: "PUT",
                headers: headersJsonApc,
                body: JSON.stringify({
                    status: el("apcReviewStatus").value,
                    mensagem: el("apcReviewMessage").value.trim(),
                }),
            }
        );
        envioPreviewApc = updated;
        renderReviewPanelApc(updated);
        setMensagemReviewApc("Revisao salva com sucesso.");
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemReviewApc(err.message || "Nao foi possivel salvar a revisao.", true);
    } finally {
        if (submit) submit.disabled = false;
    }
}

async function carregarPreviewArquivoApc(envio) {
    if (!envio?.id) {
        limparPreviewArquivoApc();
        return;
    }

    revogarPreviewArquivoApc();
    envioPreviewApcId = Number(envio.id);
    arquivoPreviewNomeApc = String(
        nomeArquivoSistemaApc(envio) || nomeArquivoPrincipalApc(envio) || "arquivo"
    );
    envioPreviewApc = envio;
    preencherMetaModalPreviewApc(envio);
    renderReviewPanelApc(envio);
    el("apcArquivoPreviewState").hidden = false;
    el("apcArquivoPreviewState").innerHTML = '<div class="booking-empty">Carregando arquivo...</div>';
    el("apcArquivoPreviewFrame").hidden = true;
    el("apcArquivoPreviewImage").hidden = true;
    el("apcArquivoPreviewText").hidden = true;
    el("btnApcBaixarArquivo").hidden = true;
    el("btnApcImprimirArquivo").hidden = true;

    try {
        const tipoPreview = tipoPreviewArquivoApc(envio);
        const endpoint = tipoPreview === "office"
            ? `/apc/envios/${envio.id}/preview`
            : `/apc/envios/${envio.id}/arquivo`;
        const resposta = await fetchResposta(endpoint, {
            headers: headersApc,
        });
        const blob = await resposta.blob();
        arquivoPreviewUrlApc = window.URL.createObjectURL(blob);

        el("apcArquivoPreviewState").hidden = true;

        if (tipoPreview === "image") {
            const imagem = el("apcArquivoPreviewImage");
            imagem.src = arquivoPreviewUrlApc;
            imagem.hidden = false;
        } else if (tipoPreview === "text") {
            const texto = await blob.text();
            const pre = el("apcArquivoPreviewText");
            pre.textContent = texto;
            pre.hidden = false;
        } else if (tipoPreview === "frame" || tipoPreview === "office") {
            const frame = el("apcArquivoPreviewFrame");
            frame.src = arquivoPreviewUrlApc;
            frame.hidden = false;
        } else {
            el("apcArquivoPreviewState").hidden = false;
            el("apcArquivoPreviewState").innerHTML =
                '<div class="booking-empty">Este formato nao possui visualizacao no navegador. Use o botao "Baixar arquivo" para abrir o documento no aplicativo adequado.</div>';
        }

        el("btnApcBaixarArquivo").hidden = false;
        el("btnApcImprimirArquivo").hidden = !modoGestaoAtivoApc();
    } catch (err) {
        const state = el("apcArquivoPreviewState");
        state.hidden = false;
        state.innerHTML = "";
        const vazio = document.createElement("div");
        vazio.className = "booking-empty";
        vazio.innerText = err.message || "Não foi possível carregar a visualização do arquivo.";
        state.appendChild(vazio);
    }
}

function renderPainelSelecionadoVazio() {
    const modoGestao = modoGestaoAtivoApc();
    renderSolicitacoesData([]);
    if (modoGestao) {
        renderEstadoVazioApc(el("apcListaPainel"), {
            icone: "bi-paperclip",
            titulo: "Comece por uma solicitação",
            descricao: "Depois de criada, os professores e os anexos recebidos aparecerão aqui.",
        });
    } else {
        el("apcListaPainel").innerHTML = "";
    }
    renderDetalheDocenteApc(null);
    if (el("apcGestaoDetalheTitulo")) el("apcGestaoDetalheTitulo").innerText = "Selecione uma demanda";
    if (el("apcGestaoDetalheDescricao")) {
        el("apcGestaoDetalheDescricao").innerText =
            "Os professores e anexos da solicitação aparecerão aqui.";
    }
    preencherFormularioPeriodo(null);
    aplicarVisibilidadeApc();
}

function renderPainelSemSelecaoGestao() {
    renderEstadoVazioApc(el("apcListaPainel"), {
        icone: "bi-cursor",
        titulo: "Selecione uma solicitação",
        descricao: "Escolha um item da lista para analisar os professores e seus anexos.",
    });
    renderSolicitacoesData(calendarioApc.periodos || []);
    aplicarVisibilidadeApc();
}

async function carregarDetalheSelecionadoApc() {
    const periodosDisponiveis = modoGestaoAtivoApc()
        ? calendarioApc.periodos || []
        : ordenarSolicitacoesDocenteApc(calendarioApc.periodos || []);

    if (!periodosDisponiveis.length) {
        periodoSelecionadoApcId = null;
        renderPainelSelecionadoVazio();
        return;
    }

    const resumoSelecionado = periodoResumoSelecionado(periodosDisponiveis);
    periodoSelecionadoApcId = Number(resumoSelecionado?.id || 0);
    if (!periodoSelecionadoApcId) {
        renderPainelSelecionadoVazio();
        return;
    }
    aplicarVisibilidadeApc();

    const detalhe = await fetchJson(`/apc/periodos/${periodoSelecionadoApcId}?visao=${visaoAtivaApc()}`, {
        headers: headersApc,
    });
    const periodo = detalhe.periodo || detalhe;
    renderSolicitacoesData(periodosDisponiveis, detalhe);

    if (modoGestaoAtivoApc()) {
        renderListaGestaoApc(detalhe);
        preencherFormularioPeriodo(periodo);
        aplicarSelecoesDestinatariosApc(detalhe.destinatarios_configurados || []);
        await sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
        return;
    }

    renderDetalheDocenteApc(detalhe);
}

async function carregarCalendarioApc() {
    const anoLetivo = anoLetivoAtivoApc();
    if (modoGestaoAtivoApc()) {
        calendarioApc = await fetchJson(`/apc/solicitacoes?ano_letivo=${anoLetivo}`, {
            headers: headersApc,
        });
        atualizarOpcoesFiltrosGestaoApc(calendarioApc.periodos || []);
    } else {
        const mes = mesIsoApc(mesAtualApc);
        calendarioApc = await fetchJson(
            `/apc/calendario?mes=${mes}&ano_letivo=${anoLetivo}&visao=${visaoAtivaApc()}`,
            { headers: headersApc }
        );
    }

    const periodos = modoDocenteAtivoApc()
        ? ordenarSolicitacoesDocenteApc(calendarioApc.periodos || [])
        : calendarioApc.periodos || [];
    const atual = periodos.find(
        (item) => Number(item.id) === Number(periodoSelecionadoApcId)
    );
    const selecionado = atual || periodos[0] || null;
    periodoSelecionadoApcId = Number(selecionado?.id || 0) || null;
    if (selecionado?.data_referencia) {
        dataSelecionadaApc = selecionado.data_referencia;
    }

    await carregarDetalheSelecionadoApc();
}

async function salvarPeriodoApc(event) {
    event.preventDefault();
    const payload = {
        ano_letivo: anoLetivoAtivoApc(),
        data_referencia: el("apcDataReferencia").value,
        prazo_envio: el("apcPrazoEnvio").value,
        titulo: el("apcTitulo").value.trim(),
        observacao: el("apcObservacao").value.trim(),
        publico_alvo: el("apcPublicoAlvo").value,
        tipo_entrega: el("apcTipoEntrega").value,
        destinatarios: coletarDestinatariosSelecionadosApc(),
    };

    try {
        let salvo;
        if (periodoEmEdicaoApcId) {
            salvo = await fetchJson(`/apc/periodos/${periodoEmEdicaoApcId}`, {
                method: "PUT",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
            });
            setMensagemApc("Solicitação atualizada com sucesso.");
        } else {
            salvo = await fetchJson("/apc/periodos", {
                method: "POST",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
            });
            setMensagemApc("Solicitação cadastrada com sucesso.");
        }
        dataSelecionadaApc = payload.data_referencia;
        periodoSelecionadoApcId = Number(salvo?.id || 0) || null;
        periodoEmEdicaoApcId = Number(salvo?.id || 0) || null;
        fecharModalFormularioApc();
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "Não foi possível salvar a solicitação.", true);
    }
}

async function excluirPeriodoApc() {
    if (!periodoEmEdicaoApcId) return;
    if (!window.confirm("Deseja realmente excluir esta solicitação de entrega?")) return;

    try {
        await fetchJson(`/apc/periodos/${periodoEmEdicaoApcId}`, {
            method: "DELETE",
            headers: headersApc,
        });
        setMensagemApc("Solicitação removida com sucesso.");
        periodoSelecionadoApcId = null;
        periodoEmEdicaoApcId = null;
        fecharModalFormularioApc({ limpar: true });
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "Não foi possível excluir a solicitação.", true);
    }
}

async function enviarArquivoApc(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const periodoId = Number(form?.dataset?.periodoId || 0);
    const turmaId = Number(form?.dataset?.turmaId || 0);
    const disciplinaId = Number(form?.dataset?.disciplinaId || 0);
    const inputArquivo = form?.querySelector('input[type="file"][name="arquivo"]');
    const arquivo = inputArquivo?.files?.[0];

    if (!periodoId || !arquivo) {
        setMensagemApc("Selecione um arquivo para enviar nesta pendência.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);
    formData.append("turma_id", String(turmaId));
    formData.append("disciplina_id", String(disciplinaId));

    try {
        await fetchJson(`/apc/periodos/${periodoId}/envio`, {
            method: "POST",
            headers: headersApc,
            body: formData,
        });
        inputArquivo.value = "";
        periodoSelecionadoApcId = periodoId;
        setMensagemApc("Arquivo enviado com sucesso.");
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "Não foi possível enviar o arquivo.", true);
    }
}

function registrarEventosApc() {
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });
    el("btnAlternarFiltrosApc")?.addEventListener("click", () => {
        el("apcGestaoFiltros")?.classList.toggle("is-mobile-open");
        atualizarFiltroMobileApc();
    });
    el("btnLimparFiltrosApc")?.addEventListener("click", limparFiltrosGestaoApc);
    el("btnFecharPreviewApc")?.addEventListener("click", fecharModalPreviewApc);
    document.querySelectorAll("[data-apc-preview-close='true']").forEach((elemento) => {
        elemento.addEventListener("click", fecharModalPreviewApc);
    });
    el("btnApcBaixarArquivo")?.addEventListener("click", async () => {
        if (envioPreviewApc) {
            await baixarArquivoApc(envioPreviewApc);
        }
    });
    el("btnApcImprimirArquivo")?.addEventListener("click", (event) => {
        event.preventDefault();
        if (envioPreviewApc) {
            void abrirPrintWizardApc(envioPreviewApc);
        }
    });
    el("formApcReview")?.addEventListener("submit", salvarRevisaoApc);
    el("apcReviewStatus")?.addEventListener("change", atualizarEstadoFormularioReviewApc);
    document.querySelectorAll('input[name="apcReviewDecision"]').forEach((input) => {
        input.addEventListener("change", () => {
            if (!input.checked || !el("apcReviewStatus")) return;
            el("apcReviewStatus").value = input.value;
            atualizarEstadoFormularioReviewApc();
        });
    });
    el("btnFecharPrintWizardApc")?.addEventListener("click", fecharPrintWizardApc);
    document.querySelectorAll("[data-apc-print-close='true']").forEach((elemento) => {
        elemento.addEventListener("click", fecharPrintWizardApc);
    });
    el("btnApcPrintContinuar")?.addEventListener("click", avancarPrintWizardApc);
    el("btnApcPrintVoltar")?.addEventListener("click", () => {
        setMensagemPrintApc("");
        renderEtapaPrintApc(etapaImpressaoApc - 1);
    });
    el("btnApcPrintPreviewAnterior")?.addEventListener("click", () => {
        apcPrintFolhaAtual = Math.max(1, apcPrintFolhaAtual - 1);
        void renderPreviewPrintApc();
    });
    el("btnApcPrintPreviewProxima")?.addEventListener("click", () => {
        apcPrintFolhaAtual += 1;
        void renderPreviewPrintApc();
    });
    ["apcPrintIntervalo", "apcPrintPaginasFolha", "apcPrintOrientacao"].forEach((id) => {
        const evento = id === "apcPrintIntervalo" ? "input" : "change";
        el(id)?.addEventListener(evento, () => {
            apcPrintFolhaAtual = 1;
            if (etapaImpressaoApc === 3) atualizarResumoPrintApc();
            void renderPreviewPrintApc();
        });
    });
    el("apcPrintTurma")?.addEventListener("change", () => {
        atualizarResumoTurmaPrintApc({ preencherCopias: true });
    });
    ["apcPrintCopias", "apcPrintDuplex"].forEach((id) => {
        const evento = id === "apcPrintCopias" ? "input" : "change";
        el(id)?.addEventListener(evento, () => {
            if (etapaImpressaoApc === 3) atualizarResumoPrintApc();
        });
    });
    el("formApcImpressao")?.addEventListener("submit", enviarImpressaoApc);
    el("btnSalvarActivityModalApc")?.addEventListener("click", () => painelAtividadeApc?.requestSubmit());
    el("btnCancelarActivityModalApc")?.addEventListener("click", fecharModalAtividadeApc);
    el("btnFecharActivityModalApc")?.addEventListener("click", fecharModalAtividadeApc);
    el("btnApcActivityPreviewAnterior")?.addEventListener("click", () => {
        if (!documentoPreviewAtividadeApc || paginaPreviewAtividadeApc <= 1) return;
        paginaPreviewAtividadeApc -= 1;
        void renderizarPaginasAtividadeApc(documentoPreviewAtividadeApc, tokenPreviewAtividadeApc);
    });
    el("btnApcActivityPreviewProxima")?.addEventListener("click", () => {
        if (!documentoPreviewAtividadeApc || paginaPreviewAtividadeApc >= documentoPreviewAtividadeApc.numPages) return;
        paginaPreviewAtividadeApc += 1;
        void renderizarPaginasAtividadeApc(documentoPreviewAtividadeApc, tokenPreviewAtividadeApc);
    });
    document.querySelectorAll("[data-apc-activity-modal-close='true']").forEach((elemento) => {
        elemento.addEventListener("click", fecharModalAtividadeApc);
    });
    [
        "apcFiltroProfessor",
        "apcFiltroDisciplina",
        "apcFiltroTurma",
        "apcFiltroStatus",
        "apcOrdenacaoGestao",
    ].forEach((id) => {
        el(id)?.addEventListener("change", renderSolicitacoesGestaoApc);
    });
    el("apcFiltroBusca")?.addEventListener("input", renderSolicitacoesGestaoApc);

    el("apcPublicoAlvo")?.addEventListener("change", async () => {
        if (!publicoSelecionadoManualApc()) {
            selecoesDestinatariosApc = new Set();
        }
        await sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
    });

    el("formApcPeriodo")?.addEventListener("submit", salvarPeriodoApc);
    el("btnAbrirNovaApc")?.addEventListener("click", () => {
        setMensagemApc("");
        abrirModalFormularioApc(null);
    });
    el("btnAbrirEditarApc")?.addEventListener("click", async () => {
        if (!periodoSelecionadoApcId) return;
        try {
            const detalhe = await fetchJson(`/apc/periodos/${periodoSelecionadoApcId}?visao=gestao`, {
                headers: headersApc,
            });
            const periodo = detalhe?.periodo || null;
            aplicarSelecoesDestinatariosApc(detalhe?.destinatarios_configurados || []);
            abrirModalFormularioApc(periodo);
            void sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
        } catch (err) {
            setMensagemApc(err.message || "Não foi possivel abrir a solicitação selecionada.", true);
        }
    });
    el("btnCancelarApc")?.addEventListener("click", () => {
        fecharModalFormularioApc({ limpar: true });
    });
    el("btnFecharModalApc")?.addEventListener("click", () => {
        fecharModalFormularioApc({ limpar: true });
    });
    el("apcModalBackdrop")?.addEventListener("click", (event) => {
        if (event.target === el("apcModalBackdrop")) {
            fecharModalFormularioApc({ limpar: true });
        }
    });
    el("btnExcluirApc")?.addEventListener("click", excluirPeriodoApc);
    el("btnApcDestinatariosTodos")?.addEventListener("click", () => {
        opcoesDestinatariosApc.forEach((professor) => {
            (professor.destinatarios || []).forEach((item) => {
                selecoesDestinatariosApc.add(chaveDestinatarioApc(item));
            });
        });
        renderDestinatariosApc();
    });
    el("btnApcDestinatariosLimpar")?.addEventListener("click", () => {
        selecoesDestinatariosApc = new Set();
        renderDestinatariosApc();
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && activityModalApcAberto()) {
            fecharModalAtividadeApc();
            return;
        }
        if (event.key === "Escape" && printWizardApcAberto()) {
            fecharPrintWizardApc();
            return;
        }
        if (event.key === "Escape" && previewArquivoApcAberto()) {
            fecharModalPreviewApc();
            return;
        }
        if (event.key === "Escape" && modalApcAberto()) {
            fecharModalFormularioApc({ limpar: true });
        }
    });
    window.addEventListener("beforeunload", () => {
        revogarPreviewArquivoApc();
        revogarPreviewPrintApc();
        cancelarPreviewAtividadeApc();
    });
}

async function initApc() {
    try {
        const usuarioMe = await fetchJson("/me", { headers: headersApc });
        contextoApc = await fetchJson("/apc/contexto", { headers: headersApc });
        usuarioApc = Object.assign({}, usuarioMe || {}, contextoApc?.usuario || {});
        perfilApc = perfilInicialApc();
        if (modoGestaoAtivoApc()) {
            limparSelecaoDataGestaoApc();
        } else {
            dataSelecionadaApc = hojeIsoApc();
        }
        preencherSelectPublicoApc();
        preencherSelectTiposEntregaApc();
        atualizarResumoDestinatariosApc();
        aplicarVisibilidadeApc();
        registrarEventosApc();
        await sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
        await carregarCalendarioApc();
    } catch (_err) {
        encerrarSessao();
    }
}

window.addEventListener("DOMContentLoaded", initApc);
