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
let calendarioVisivelApc = false;
let calendarioDrawerTimerApc = null;
let focoAntesCalendarioApc = null;
let envioPreviewApc = null;
let envioPreviewApcId = null;
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

function calendarioDrawerAbertoApc() {
    return modoDocenteAtivoApc() && calendarioVisivelApc;
}

function abrirCalendarioApc() {
    const drawer = el("apcCalendarDrawer");
    const painel = el("apcCalendarCard");
    if (!drawer || !painel || !modoDocenteAtivoApc()) return;

    if (calendarioDrawerTimerApc) {
        window.clearTimeout(calendarioDrawerTimerApc);
        calendarioDrawerTimerApc = null;
    }

    focoAntesCalendarioApc = document.activeElement;
    calendarioVisivelApc = true;
    drawer.hidden = false;
    document.body.classList.add("apc-calendar-drawer-open");
    aplicarVisibilidadeApc();
    window.requestAnimationFrame(() => {
        drawer.classList.add("is-visible");
        focarSemRolagemApc(painel);
    });
}

function fecharCalendarioApc({ devolverFoco = true } = {}) {
    const drawer = el("apcCalendarDrawer");
    if (!drawer || !modoDocenteAtivoApc()) return;

    calendarioVisivelApc = false;
    drawer.classList.remove("is-visible");
    document.body.classList.remove("apc-calendar-drawer-open");
    aplicarVisibilidadeApc();
    calendarioDrawerTimerApc = window.setTimeout(() => {
        drawer.hidden = true;
        calendarioDrawerTimerApc = null;
    }, 260);

    if (devolverFoco && focoAntesCalendarioApc instanceof HTMLElement) {
        focarSemRolagemApc(focoAntesCalendarioApc);
    }
    focoAntesCalendarioApc = null;
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

function preencherSelectAnosApc() {
    const select = el("apcAnoLetivo");
    select.innerHTML = "";
    (contextoApc?.anos_letivos || []).forEach((ano) => {
        const option = document.createElement("option");
        option.value = String(ano);
        option.innerText = String(ano);
        select.appendChild(option);
    });
    if (contextoApc?.ano_letivo_atual) {
        select.value = String(contextoApc.ano_letivo_atual);
    }
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

function periodosResumoPorData(dataIso) {
    return (calendarioApc.periodos || []).filter((item) => item.data_referencia === dataIso);
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

function atualizarResumoMesApc() {
    const periodos = Array.isArray(calendarioApc.periodos) ? calendarioApc.periodos : [];
    if (modoGestaoAtivoApc()) {
        const totalSolicitacoes = periodos.length;
        const totalPendencias = periodos.reduce(
            (soma, item) => soma + Number(item.total_pendentes || 0),
            0
        );
        el("apcResumoMes").innerText =
            `${pluralizarApc(totalSolicitacoes, "solicitacao", "solicitacoes")} neste ano | `
            + `${pluralizarApc(totalPendencias, "pendencia", "pendencias")} de envio.`;
        return;
    }

    const totalSolicitacoes = periodos.length;
    const enviados = periodos.filter((item) => Boolean(item.enviado)).length;
    el("apcResumoMes").innerText =
        `${pluralizarApc(totalSolicitacoes, "entrega prevista", "entregas previstas")} para voce neste mes | `
        + `${pluralizarApc(enviados, "arquivo enviado", "arquivos enviados")}.`;
}

function aplicarVisibilidadeApc() {
    const podeGerir = usuarioPodeVerGestaoApc();
    const layoutProfessor = modoDocenteAtivoApc();
    const pagina = obterPaginaApc();
    const acoesGestao = el("apcGestaoActions");
    const calendarioDrawer = el("apcCalendarDrawer");
    const calendarioCard = el("apcCalendarCard");
    const botaoCalendario = el("btnAlternarCalendarioApc");
    const detalheDocente = el("apcDocenteDetalhe");
    const detalheGestao = el("apcGestaoDetalhe");
    const filtrosGestao = el("apcGestaoFiltros");
    const tituloSolicitacoes = el("apcSolicitacoesTitulo");
    const descricaoSolicitacoes = el("apcSolicitacoesDescricao");
    const gestaoAtiva = podeGerir && modoGestaoAtivoApc();

    if (calendarioDrawer && !layoutProfessor) {
        calendarioDrawer.hidden = true;
        calendarioDrawer.classList.remove("is-visible");
    }
    if (calendarioCard) {
        calendarioCard.setAttribute("role", layoutProfessor ? "dialog" : "region");
        calendarioCard.setAttribute("aria-modal", layoutProfessor ? "true" : "false");
    }
    if (botaoCalendario) {
        botaoCalendario.hidden = !layoutProfessor;
        botaoCalendario.innerText = calendarioVisivelApc ? "Ocultar calendario" : "Ver calendario";
        botaoCalendario.setAttribute("aria-expanded", calendarioVisivelApc ? "true" : "false");
    }
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
        tituloSolicitacoes.innerText = layoutProfessor ? "Entregas do mes" : "Demandas de entrega";
    }
    if (descricaoSolicitacoes) {
        descricaoSolicitacoes.innerText = layoutProfessor
            ? "As pendencias aparecem primeiro e a mais urgente ja fica aberta."
            : "Use os filtros e selecione uma demanda para acompanhar os professores.";
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
        ? "Editar solicitacao de entrega"
        : "Nova solicitacao de entrega";
    el("apcModalDescricao").innerText = editando
        ? "Ajuste o documento solicitado, o prazo e os destinatarios desta solicitacao."
        : "Defina o documento solicitado, o prazo e quem deve visualizar essa entrega.";
}

function abrirModalFormularioApc(periodo = null) {
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
        ? `${pluralizarApc(total, "combinacao selecionada", "combinacoes selecionadas")} para esta solicitacao.`
        : "Nenhuma combinacao selecionada ainda.";
}

async function carregarOpcoesDestinatariosApc(force = false) {
    if (!publicoSelecionadoManualApc()) return;
    if (opcoesDestinatariosApc.length && !force) {
        renderDestinatariosApc();
        return;
    }
    const anoLetivo = Number(el("apcAnoLetivo")?.value || 0);
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
        return { texto: "Aguardando envios", tipo: "pending" };
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

    const topo = document.createElement("div");
    topo.className = "apc-envio-card-topo";
    const review = statusRevisaoEnvioApc(envio);
    topo.appendChild(criarStatusApc(review.texto, review.tipo));

    const enviadoEm = document.createElement("p");
    enviadoEm.className = "apc-envio-meta";
    enviadoEm.innerText = `Enviado em ${formatarDataHoraApc(envio.enviado_em)}`;
    topo.appendChild(enviadoEm);
    envioCard.appendChild(topo);

    const nome = document.createElement("strong");
    nome.className = "apc-envio-nome";
    nome.innerText = nomeArquivoPrincipalApc(envio);
    envioCard.appendChild(nome);

    const guidance = criarOrientacaoRevisaoApc(envio);
    if (guidance) {
        envioCard.appendChild(guidance);
    }

    const acoes = document.createElement("div");
    acoes.className = "apc-inline-actions apc-envio-actions";

    acoes.appendChild(criarBotaoVisualizarApc(envio));

    const abrir = document.createElement("button");
    abrir.type = "button";
    abrir.innerText = "Baixar arquivo";
    abrir.addEventListener("click", async () => {
        await baixarArquivoApc(envio);
    });
    acoes.appendChild(abrir);

    if (!periodo?.prazo_expirado) {
        const remover = document.createElement("button");
        remover.type = "button";
        remover.className = "btn-perigo";
        remover.dataset.envioId = String(envio.id);
        remover.dataset.periodoId = String(periodo.id || 0);
        remover.innerText = "Remover arquivo";
        remover.addEventListener("click", removerArquivoApc);
        acoes.appendChild(remover);
    }

    envioCard.appendChild(acoes);

    if (periodo?.prazo_expirado) {
        const aviso = document.createElement("p");
        aviso.className = "apc-inline-hint";
        aviso.innerText = "O prazo foi encerrado. Este anexo permanece apenas para consulta.";
        envioCard.appendChild(aviso);
    }

    return envioCard;
}

function criarCardEntregaProfessorApc(periodo, item) {
    const card = document.createElement("article");
    card.className = "apc-professor-card";
    card.classList.add(
        item.enviado ? "is-enviado" : (periodo.prazo_expirado ? "is-fechado" : "is-pendente")
    );

    const topo = document.createElement("div");
    topo.className = "apc-professor-topo";
    const titulo = item.disciplina_nome
        ? `${item.disciplina_nome}${item.turma_nome ? ` - ${item.turma_nome}` : ""}`
        : "Entrega geral";
    topo.innerHTML = `<div><h4>${titulo}</h4></div>`;
    const review = statusRevisaoEnvioApc(item.envio);
    topo.appendChild(
        item.enviado
            ? criarStatusApc(review.texto, review.tipo)
            : (periodo.prazo_expirado ? criarStatusApc("Prazo encerrado", "closed") : criarStatusApc("Pendente"))
    );
    card.appendChild(topo);

    const resumo = document.createElement("div");
    resumo.className = "apc-professor-card-resumo";

    const turma = document.createElement("p");
    turma.className = "apc-inline-hint";
    turma.innerText = item.turma_nome
        ? `Turma: ${item.turma_nome}`
        : "Entrega sem turma vinculada.";
    resumo.appendChild(turma);

    if (item.envio?.id) {
        const envioExistente = criarCardEnvioExistenteApc(periodo, item);
        if (envioExistente) {
            card.appendChild(envioExistente);
        }
    }

    if (periodo.prazo_expirado) {
        return card;
    }

    const form = document.createElement("form");
    form.className = "apc-form apc-inline-form";
    form.dataset.periodoId = String(periodo.id);
    form.dataset.turmaId = String(item.turma_id || 0);
    form.dataset.disciplinaId = String(item.disciplina_id || 0);

    const label = document.createElement("label");
    label.innerText = "Arquivo";
    form.appendChild(label);

    const input = document.createElement("input");
    input.type = "file";
    input.required = true;
    input.name = "arquivo";
    form.appendChild(input);

    const dica = document.createElement("p");
    dica.className = "apc-inline-hint";
    dica.innerText = item.envio?.id
        ? "Se necessario, remova o arquivo atual ou envie uma nova versao para esta disciplina."
        : "Anexe o arquivo correspondente a esta disciplina.";
    form.appendChild(dica);

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "btn-destaque";
    submit.innerText = item.envio?.id ? "Substituir arquivo" : "Enviar arquivo";
    form.appendChild(submit);

    form.addEventListener("submit", enviarArquivoApc);
    card.appendChild(form);
    return card;
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

    if ((detalhe.turmas || []).length) {
        const chips = document.createElement("div");
        chips.className = "apc-chip-row";
        (detalhe.turmas || []).forEach((turma) => {
            chips.appendChild(criarChipApc(turma));
        });
        body.appendChild(chips);
    }

    const resumo = document.createElement("p");
    resumo.className = "apc-inline-hint";
    resumo.innerText = detalhe.total_entregas > 1
        ? `Voce possui ${detalhe.total_entregas} entregas nesta solicitacao. Cada disciplina precisa do seu proprio anexo.`
        : "Voce possui 1 entrega nesta solicitacao.";
    body.appendChild(resumo);

    if (periodo.observacao) {
        const observacao = document.createElement("p");
        observacao.className = "apc-inline-observacao";
        observacao.innerText = periodo.observacao;
        body.appendChild(observacao);
    }

    if (!Array.isArray(detalhe.itens) || !detalhe.itens.length) {
        const vazio = document.createElement("p");
        vazio.className = "apc-accordion-note";
        vazio.innerText = periodo.publico_alvo === "PROFESSORES_SELECIONADOS"
            ? "Nenhuma disciplina foi vinculada a voce nesta solicitacao."
            : "Nenhuma disciplina vinculada a esta solicitacao para o seu horario.";
        body.appendChild(vazio);
        return body;
    }

    const grid = document.createElement("div");
    grid.className = "apc-professor-card-grid";
    detalhe.itens.forEach((item) => {
        grid.appendChild(criarCardEntregaProfessorApc(periodo, item));
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
        wrap.innerHTML =
            '<div class="booking-empty">Nenhuma entrega foi encontrada neste mes.</div>';
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
        resumo.innerText = periodo.enviado
            ? "Todos os anexos desta solicitacao foram enviados."
            : `${periodo.total_pendentes || periodo.total_entregas || 0} anexo(s) pendente(s)`;
        copia.appendChild(resumo);
        topo.appendChild(copia);

        const status = statusResumoPeriodoApc(periodo);
        topo.appendChild(criarStatusApc(status.texto, status.tipo));
        card.appendChild(topo);

        const meta = document.createElement("div");
        meta.className = "apc-pendencia-card-meta";
        meta.appendChild(criarMetaApc(paraDataBr(periodo.data_referencia)));
        meta.appendChild(criarMetaApc(`Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`));
        if (periodo.tipo_entrega_label) {
            meta.appendChild(criarMetaApc(periodo.tipo_entrega_label));
        }
        card.appendChild(meta);

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
                el("apcDocenteDetalhe")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
        painel.innerHTML =
            '<div class="booking-empty">Nenhuma demanda pendente foi encontrada neste mes.</div>';
        return;
    }

    const periodo = detalhe.periodo;
    const header = document.createElement("header");
    header.className = "apc-docente-detalhe-header";

    const copia = document.createElement("div");
    const eyebrow = document.createElement("p");
    eyebrow.className = "apc-section-eyebrow";
    eyebrow.innerText = "Anexos necessarios";
    copia.appendChild(eyebrow);

    const titulo = document.createElement("h2");
    titulo.innerText = periodo.titulo || "Documento";
    copia.appendChild(titulo);

    const prazo = document.createElement("p");
    prazo.innerText =
        `Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`;
    copia.appendChild(prazo);
    header.appendChild(copia);

    const status = statusResumoPeriodoApc(
        Object.assign({}, periodo, {
            enviado: Number(detalhe.total_pendentes || 0) === 0 && Number(detalhe.total_entregas || 0) > 0,
        })
    );
    header.appendChild(criarStatusApc(status.texto, status.tipo));
    painel.appendChild(header);
    painel.appendChild(
        renderResumoCompactoApc([
            { label: "Pendentes", valor: String(detalhe.total_pendentes || 0) },
            { label: "Enviadas", valor: String(detalhe.total_enviadas || 0) },
            { label: "Impressas", valor: String(detalhe.total_impressos || 0) },
            { label: "Prazo", valor: periodo.prazo_expirado ? "Encerrado" : "Aberto" },
        ])
    );
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
    wrap.innerHTML = "";

    if (!periodos.length) {
        wrap.innerHTML =
            '<div class="booking-empty">Nenhuma demanda corresponde aos filtros selecionados.</div>';
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

        const dimensoes = document.createElement("div");
        dimensoes.className = "apc-demanda-dimensoes";
        (periodo.disciplinas || []).slice(0, 2).forEach(
            (item) => dimensoes.appendChild(criarChipApc(item))
        );
        (periodo.turmas || []).slice(0, 2).forEach(
            (item) => dimensoes.appendChild(criarChipApc(item))
        );
        if (dimensoes.childNodes.length) card.appendChild(dimensoes);

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
                el("apcGestaoDetalhe")?.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
        card.appendChild(abrir);
        wrap.appendChild(card);
    });
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
            ? `${paraDataBr(periodo.data_referencia)} | Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`
            : "Os professores e anexos da solicitacao aparecerao aqui.";
    }

    if (!detalhe || !Array.isArray(detalhe.itens) || detalhe.itens.length === 0) {
        lista.innerHTML = '<div class="booking-empty">Nenhum professor elegivel para esta solicitacao.</div>';
        return;
    }

    const grupos = agruparItensGestaoPorProfessor(detalhe.itens);
    const wrap = document.createElement("div");
    wrap.className = "apc-professor-group-list";

    grupos.forEach((grupo) => {
        const details = document.createElement("details");
        details.className = "apc-professor-group";
        details.open = false;

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
            + `${grupo.total_pendentes} pendencia(s)`;
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

    const eyebrow = document.createElement("p");
    eyebrow.className = "apc-section-eyebrow";
    eyebrow.innerText = "Visualizacao do anexo";
    meta.appendChild(eyebrow);

    const titulo = document.createElement("h2");
    titulo.id = "apcArquivoPreviewTitulo";
    titulo.innerText = nomeArquivoPrincipalApc(envio);
    meta.appendChild(titulo);

    const contexto = document.createElement("p");
    contexto.innerText = [
        envio.professor_nome || "",
        envio.disciplina_nome || "Entrega geral",
        envio.turma_nome || "",
    ].filter(Boolean).join(" | ");
    meta.appendChild(contexto);

    const data = document.createElement("p");
    data.innerText = `Enviado em ${formatarDataHoraApc(envio.enviado_em)}`;
    meta.appendChild(data);

    if (nomeArquivoPadronizadoDivergeApc(envio)) {
        const nomeSistema = document.createElement("p");
        nomeSistema.innerText = `Salvo no sistema como: ${nomeArquivoSistemaApc(envio)}`;
        meta.appendChild(nomeSistema);
    }
}

function setMensagemReviewApc(texto, erro = false) {
    const mensagem = el("apcReviewMessageState");
    if (!mensagem) return;
    mensagem.innerText = texto || "";
    mensagem.classList.toggle("is-error", Boolean(texto) && erro);
    mensagem.classList.toggle("is-success", Boolean(texto) && !erro);
}

function renderReviewPanelApc(envio) {
    const panel = el("apcReviewPanel");
    const summary = el("apcReviewSummary");
    const form = el("formApcReview");
    if (!panel || !summary || !form || !envio?.id) return;

    const review = statusRevisaoEnvioApc(envio);
    panel.hidden = false;
    summary.innerHTML = "";
    summary.appendChild(criarStatusApc(review.texto, review.tipo));

    const guidance = criarOrientacaoRevisaoApc(envio);
    if (guidance) {
        summary.appendChild(guidance);
    } else {
        const empty = document.createElement("p");
        empty.innerText = review.status === "PENDENTE"
            ? "Este anexo ainda nao foi analisado pela coordenacao."
            : "A coordenacao nao adicionou uma orientacao.";
        summary.appendChild(empty);
    }

    if (envio.reviewed_at) {
        const reviewedAt = document.createElement("small");
        reviewedAt.innerText = [
            `Revisado em ${formatarDataHoraApc(envio.reviewed_at)}`,
            envio.reviewed_by_name || "",
        ].filter(Boolean).join(" por ");
        summary.appendChild(reviewedAt);
    }

    form.hidden = !modoGestaoAtivoApc();
    if (modoGestaoAtivoApc()) {
        el("apcReviewStatus").value = review.status;
        el("apcReviewMessage").value = String(envio.review_message || "");
    }
    setMensagemReviewApc("");
}

async function salvarRevisaoApc(event) {
    event.preventDefault();
    if (!envioPreviewApc?.id || !modoGestaoAtivoApc()) return;

    const submit = event.currentTarget.querySelector("button[type='submit']");
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
        limparPreviewArquivoApc(err.message || "Nao foi possivel carregar o arquivo.");
    }
}

function renderPainelSelecionadoVazio() {
    const modoGestao = modoGestaoAtivoApc();
    renderSolicitacoesData([]);
    el("apcListaPainel").innerHTML = modoGestao
        ? '<div class="booking-empty">Abra o modal de nova solicitação para comecar a receber anexos dos professores.</div>'
        : "";
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
    el("apcListaPainel").innerHTML =
        '<div class="booking-empty">Selecione uma demanda para analisar os professores e seus anexos.</div>';
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

function renderCalendarioApc() {
    const ano = mesAtualApc.getFullYear();
    const mes = mesAtualApc.getMonth();
    el("apcMesAtual").innerText = `${nomesMesesApc[mes]} ${ano}`;

    const grid = el("apcCalendarioGrid");
    grid.innerHTML = "";

    nomesDiasSemanaApc.forEach((dia) => {
        const celula = document.createElement("div");
        celula.className = "calendar-weekday";
        celula.innerText = dia;
        grid.appendChild(celula);
    });

    const primeiroDiaSemana = new Date(ano, mes, 1).getDay();
    const totalDias = new Date(ano, mes + 1, 0).getDate();
    const hojeIso = paraIso(new Date());

    for (let i = 0; i < primeiroDiaSemana; i += 1) {
        const vazio = document.createElement("div");
        vazio.className = "calendar-empty";
        grid.appendChild(vazio);
    }

    for (let dia = 1; dia <= totalDias; dia += 1) {
        const dataIso = paraIso(new Date(ano, mes, dia));
        const periodos = periodosResumoPorData(dataIso);

        const btnDia = document.createElement(modoGestaoAtivoApc() ? "button" : "div");
        if (modoGestaoAtivoApc()) {
            btnDia.type = "button";
        }
        btnDia.className = "calendar-day apc-calendar-day";
        if (modoGestaoAtivoApc() && dataIso === dataSelecionadaApc && dataSelecionadaManualmenteApc) {
            btnDia.classList.add("is-selected");
        }
        if (modoDocenteAtivoApc()) {
            btnDia.classList.add("is-readonly");
            btnDia.setAttribute("aria-label", `${paraDataBr(dataIso)}: ${periodos.length} entrega(s)`);
        }
        if (dataIso === hojeIso) btnDia.classList.add("is-today");
        if (periodos.length) {
            btnDia.classList.add("has-apc");
            const todosConcluidos = modoGestaoAtivoApc()
                ? periodos.every(
                    (item) => (
                        Number(item.total_elegiveis || 0) > 0
                        && (
                            Number(item.total_aprovados || 0) === Number(item.total_elegiveis || 0)
                            || Number(item.total_impressos || 0) === Number(item.total_elegiveis || 0)
                        )
                    )
                )
                : periodos.every((item) => (
                    Number(item.total_entregas || 0) > 0
                    && (
                        Number(item.total_aprovados || 0) === Number(item.total_entregas || 0)
                        || Number(item.total_impressos || 0) === Number(item.total_entregas || 0)
                    )
                ));
            btnDia.classList.add(todosConcluidos ? "is-ok" : "is-pending");
        }

        const numero = document.createElement("span");
        numero.className = "calendar-number";
        numero.innerText = String(dia);
        btnDia.appendChild(numero);

        const resumo = document.createElement("small");
        resumo.className = "calendar-count";
        if (!periodos.length) {
            resumo.innerText = "Livre";
        } else if (modoGestaoAtivoApc()) {
            const totalElegiveis = periodos.reduce((soma, item) => soma + Number(item.total_elegiveis || 0), 0);
            const totalEnviados = periodos.reduce((soma, item) => soma + Number(item.total_enviados || 0), 0);
            resumo.innerText = `${totalEnviados}/${totalElegiveis}`;
        } else {
            const enviados = periodos.filter((item) => Boolean(item.enviado)).length;
            resumo.innerText = enviados === periodos.length ? "OK" : `${periodos.length} entrega(s)`;
        }
        btnDia.appendChild(resumo);

        if (periodos.length) {
            const flag = document.createElement("span");
            flag.className = "apc-calendar-flag";
            flag.innerText = periodos.length === 1
                ? (periodos[0].titulo || "Documento")
                : `${periodos.length} entregas`;
            btnDia.appendChild(flag);
        }

        if (modoGestaoAtivoApc()) {
            btnDia.addEventListener("click", async () => {
                dataSelecionadaApc = dataIso;
                dataSelecionadaManualmenteApc = true;
                const periodosDaData = periodosResumoPorData(dataIso);
                const atualNaData = periodosDaData.find(
                    (item) => Number(item.id) === Number(periodoSelecionadoApcId)
                );
                periodoSelecionadoApcId = atualNaData
                    ? Number(atualNaData.id)
                    : Number(periodosDaData[0]?.id || 0);
                aplicarVisibilidadeApc();
                renderCalendarioApc();
                await carregarDetalheSelecionadoApc();
            });
        }

        grid.appendChild(btnDia);
    }
}

async function carregarCalendarioApc() {
    const anoLetivo = el("apcAnoLetivo").value;
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
        renderCalendarioApc();
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

    atualizarResumoMesApc();
    await carregarDetalheSelecionadoApc();
}

async function salvarPeriodoApc(event) {
    event.preventDefault();
    const payload = {
        ano_letivo: Number(el("apcAnoLetivo").value || 0),
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
    el("btnAlternarCalendarioApc")?.addEventListener("click", () => {
        if (calendarioDrawerAbertoApc()) {
            fecharCalendarioApc();
        } else {
            abrirCalendarioApc();
        }
    });
    document.querySelectorAll("[data-apc-calendar-close='true']").forEach((elemento) => {
        elemento.addEventListener("click", () => {
            fecharCalendarioApc();
        });
    });
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

    el("apcAnoLetivo").addEventListener("change", async () => {
        limparSelecaoDataGestaoApc();
        opcoesDestinatariosApc = [];
        selecoesDestinatariosApc = new Set();
        aplicarVisibilidadeApc();
        await sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
        await carregarCalendarioApc();
    });

    el("apcPublicoAlvo")?.addEventListener("change", async () => {
        if (!publicoSelecionadoManualApc()) {
            selecoesDestinatariosApc = new Set();
        }
        await sincronizarVisibilidadeDestinatariosApc({ recarregar: true });
    });

    el("btnApcMesAnterior").addEventListener("click", async () => {
        mesAtualApc = new Date(mesAtualApc.getFullYear(), mesAtualApc.getMonth() - 1, 1);
        limparSelecaoDataGestaoApc();
        aplicarVisibilidadeApc();
        await carregarCalendarioApc();
    });
    el("btnApcMesProximo").addEventListener("click", async () => {
        mesAtualApc = new Date(mesAtualApc.getFullYear(), mesAtualApc.getMonth() + 1, 1);
        limparSelecaoDataGestaoApc();
        aplicarVisibilidadeApc();
        await carregarCalendarioApc();
    });
    el("btnApcMesHoje").addEventListener("click", async () => {
        const hoje = new Date();
        mesAtualApc = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        limparSelecaoDataGestaoApc();
        if (!modoGestaoAtivoApc()) {
            dataSelecionadaApc = paraIso(hoje);
        }
        aplicarVisibilidadeApc();
        await carregarCalendarioApc();
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
        if (event.key === "Escape" && printWizardApcAberto()) {
            fecharPrintWizardApc();
            return;
        }
        if (event.key === "Escape" && previewArquivoApcAberto()) {
            fecharModalPreviewApc();
            return;
        }
        if (event.key === "Escape" && calendarioDrawerAbertoApc()) {
            fecharCalendarioApc();
            return;
        }
        if (event.key === "Escape" && modalApcAberto()) {
            fecharModalFormularioApc({ limpar: true });
        }
    });
    window.addEventListener("beforeunload", () => {
        revogarPreviewArquivoApc();
        revogarPreviewPrintApc();
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
        preencherSelectAnosApc();
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
