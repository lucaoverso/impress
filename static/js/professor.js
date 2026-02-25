const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": "Bearer " + token
};

let pdfDoc = null;
let folhaAtual = 1;
let renderTokenAtual = 0;
let resizeTimer = null;
const QUALIDADE_MAX_DPR = 1.4;
const FOLHA_PADDING = 8;
const FOLHA_GAP = 6;
const LARGURA_MINIATURA_MOBILE = 164;
const LABEL_PREVIEW_RESERVA = 72;
const RESERVA_BORDA_PREVIEW = 24;

const TAMANHO_FOLHA = {
    retrato: { largura: 794, altura: 1123 },
    paisagem: { largura: 1123, altura: 794 }
};

function el(id) {
    return document.getElementById(id);
}

function obterConfigLayout(paginasPorFolha) {
    if (paginasPorFolha === 1) {
        return { colunas: 1, linhas: 1 };
    }
    if (paginasPorFolha === 2) {
        return { colunas: 2, linhas: 1 };
    }
    return { colunas: 2, linhas: 2 };
}

function obterDimensoesMiniatura(tamanhoFolha, isMobile) {
    const pane = document.querySelector(".print-preview-pane");

    const larguraDisponivel = pane
        ? Math.max(120, pane.clientWidth - RESERVA_BORDA_PREVIEW)
        : Math.max(120, window.innerWidth - 56);
    const alturaDisponivelBase = pane
        ? Math.max(120, pane.clientHeight - RESERVA_BORDA_PREVIEW)
        : Math.max(120, Math.floor(window.innerHeight * (isMobile ? 0.28 : 0.5)));

    const alturaDisponivel = isMobile
        ? Math.max(110, alturaDisponivelBase - LABEL_PREVIEW_RESERVA)
        : alturaDisponivelBase;
    const larguraAlvo = isMobile
        ? Math.min(LARGURA_MINIATURA_MOBILE, larguraDisponivel)
        : larguraDisponivel;
    const escala = Math.min(
        larguraAlvo / tamanhoFolha.largura,
        alturaDisponivel / tamanhoFolha.altura
    );

    return {
        largura: Math.max(96, Math.round(tamanhoFolha.largura * escala)),
        altura: Math.max(110, Math.round(tamanhoFolha.altura * escala))
    };
}

function mostrarPreviewVazio(texto = "Selecione um PDF para visualizar as páginas.") {
    const container = el("previewContainer");
    container.innerHTML = "";

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
    folhaAtiva.scrollIntoView({
        behavior: suave ? "smooth" : "auto",
        block: "nearest",
        inline: "center"
    });
}

function obterOrientacaoPreview() {
    const paginasPorFolha = Number(el("paginasPorFolha").value);
    if (paginasPorFolha === 2) {
        return "paisagem";
    }
    return el("orientacao").value;
}

function atualizarComportamentoOrientacao() {
    const orientacaoEl = el("orientacao");
    const paginasPorFolha = Number(el("paginasPorFolha").value);

    if (paginasPorFolha === 2) {
        orientacaoEl.value = "paisagem";
        orientacaoEl.disabled = true;
        orientacaoEl.title = "Com 2 páginas por folha, a visualização usa modo paisagem.";
    } else {
        orientacaoEl.disabled = false;
        orientacaoEl.title = "";
    }
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
                    throw new Error(`Página ${pagina} não existe no PDF`);
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
            throw new Error(`Página ${pagina} não existe no PDF`);
        }
        paginas.add(pagina);
    }

    const resultado = Array.from(paginas).sort((a, b) => a - b);
    infoEl.innerText = `${resultado.length} página(s) selecionada(s).`;
    return resultado;
}

function calcularConsumo() {
    if (!pdfDoc) {
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

async function enviarImpressao() {
    const arquivo = el("arquivo").files[0];
    const copias = Number(el("copias").value);
    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const duplex = el("duplex").checked;
    const orientacao = obterOrientacaoPreview();
    const intervaloPaginas = el("intervaloPaginas").value.trim();

    if (!arquivo || !copias || copias < 1) {
        alert("Preencha todos os campos");
        return;
    }

    try {
        obterPaginasSelecionadas();
    } catch (err) {
        el("msg").innerText = err.message;
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);
    formData.append("copias", copias);
    formData.append("paginas_por_folha", paginasPorFolha);
    formData.append("duplex", duplex);
    formData.append("orientacao", orientacao);
    if (intervaloPaginas) {
        formData.append("intervalo_paginas", intervaloPaginas);
    }

    const res = await fetch("/imprimir", {
        method: "POST",
        headers,
        body: formData
    });

    const data = await res.json();
    if (!res.ok) {
        el("msg").innerText = data.detail;
        return;
    }

    el("msg").innerText = `Enviado! Restam ${data.paginas_restantes} páginas`;
    carregarFila();
    carregarCota();
    calcularConsumo();
}

async function carregarCota() {
    const res = await fetch("/minha-cota", { headers });
    const data = await res.json();
    el("cota").innerText = `Restante: ${data.restante} páginas`;
}

async function carregarFila() {
    const res = await fetch("/meus-jobs", { headers });
    const jobs = await res.json();

    const ul = el("lista-jobs");
    ul.innerHTML = "";

    jobs.forEach((job) => {
        const li = document.createElement("li");
        li.innerText = `${job.arquivo} — ${job.status}`;
        ul.appendChild(li);
    });
}

async function carregarPreview(file) {
    if (!file) {
        pdfDoc = null;
        folhaAtual = 1;
        renderTokenAtual += 1;
        mostrarPreviewVazio();
        calcularConsumo();
        atualizarContador();
        return;
    }

    const arrayBuffer = await file.arrayBuffer();
    pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    folhaAtual = 1;
    atualizarPreview();
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
    try {
        const paginasPorFolha = Number(el("paginasPorFolha").value);
        const paginasSelecionadas = obterPaginasSelecionadas();
        return Math.max(1, Math.ceil(paginasSelecionadas.length / paginasPorFolha));
    } catch {
        return 0;
    }
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
    el("contadorFolha").innerText = `Folha ${folhaAtual} de ${total}`;
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
    const isMobile = window.innerWidth <= 980;
    if (isMobile) {
        atualizarDestaqueFolha();
        centralizarFolhaAtiva();
        return;
    }
    renderFolha();
}

async function renderFolha() {
    const container = el("previewContainer");
    container.innerHTML = "";
    const isMobile = window.innerWidth <= 980;
    container.classList.toggle("is-carousel", isMobile);

    if (!pdfDoc) {
        mostrarPreviewVazio();
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
    const configLayout = obterConfigLayout(paginasPorFolha);
    const tamanhoFolha = TAMANHO_FOLHA[orientacao];
    const totalFolhas = Math.max(1, Math.ceil(paginasSelecionadas.length / paginasPorFolha));

    if (folhaAtual > totalFolhas) {
        folhaAtual = totalFolhas;
    }

    const folhasParaRenderizar = isMobile
        ? Array.from({ length: totalFolhas }, (_, i) => i + 1)
        : [folhaAtual];
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
        const paginasDaFolha = paginasSelecionadas.slice(inicio, inicio + paginasPorFolha);

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

            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");

            canvas.width = Math.floor(viewport.width);
            canvas.height = Math.floor(viewport.height);
            canvas.style.width = `${Math.floor(viewport.width / dpr)}px`;
            canvas.style.height = `${Math.floor(viewport.height / dpr)}px`;
            canvas.style.maxWidth = "100%";
            canvas.style.maxHeight = "100%";

            wrapper.appendChild(canvas);
            folha.appendChild(wrapper);

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

function reagendarRenderAposResize() {
    if (!pdfDoc) {
        return;
    }
    if (resizeTimer) {
        clearTimeout(resizeTimer);
    }
    resizeTimer = setTimeout(() => {
        renderFolha();
    }, 120);
}

function registrarEventos() {
    el("arquivo").addEventListener("change", (e) => carregarPreview(e.target.files[0]));
    el("orientacao").addEventListener("change", atualizarPreview);
    el("copias").addEventListener("input", calcularConsumo);
    el("duplex").addEventListener("change", atualizarPreview);
    el("paginasPorFolha").addEventListener("change", () => {
        folhaAtual = 1;
        atualizarPreview();
    });
    el("intervaloPaginas").addEventListener("input", atualizarPreview);
    el("btnEnviar").addEventListener("click", enviarImpressao);
    el("btnAnterior").addEventListener("click", folhaAnterior);
    el("btnProxima").addEventListener("click", proximaFolha);
    window.addEventListener("resize", reagendarRenderAposResize);

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
            localStorage.removeItem("token");
            window.location.href = "/login-page";
        });
    }
}

window.atualizarPreview = atualizarPreview;
window.enviarImpressao = enviarImpressao;
window.proximaFolha = proximaFolha;
window.folhaAnterior = folhaAnterior;

registrarEventos();
atualizarComportamentoOrientacao();
carregarCota();
carregarFila();
mostrarPreviewVazio();
