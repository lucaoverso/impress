const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": "Bearer " + token
};

let pdfDoc = null;
let folhaAtual = 1;
const QUALIDADE_MAX_DPR = 2.5;
const FOLHA_PADDING = 12;
const FOLHA_GAP = 10;

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
        return;
    }

    const arrayBuffer = await file.arrayBuffer();
    pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    folhaAtual = 1;
    atualizarPreview();
}

function atualizarPreview() {
    atualizarComportamentoOrientacao();
    renderFolha();
    calcularConsumo();
    atualizarContador();
}

function totalFolhasVisualizacao() {
    if (!pdfDoc) {
        return 0;
    }
    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const paginasSelecionadas = obterPaginasSelecionadas();
    return Math.max(1, Math.ceil(paginasSelecionadas.length / paginasPorFolha));
}

function atualizarContador() {
    if (!pdfDoc) {
        el("contadorFolha").innerText = "";
        return;
    }
    const total = totalFolhasVisualizacao();
    if (folhaAtual > total) {
        folhaAtual = total;
    }
    el("contadorFolha").innerText = `Folha ${folhaAtual} de ${total}`;
}

async function renderFolha() {
    const container = el("previewContainer");
    container.innerHTML = "";

    if (!pdfDoc) {
        return;
    }

    let paginasSelecionadas;
    try {
        paginasSelecionadas = obterPaginasSelecionadas();
    } catch (err) {
        el("intervaloInfo").innerText = err.message;
        return;
    }

    const paginasPorFolha = Number(el("paginasPorFolha").value);
    const orientacao = obterOrientacaoPreview();
    const configLayout = obterConfigLayout(paginasPorFolha);
    const tamanhoFolha = TAMANHO_FOLHA[orientacao];
    const inicio = (folhaAtual - 1) * paginasPorFolha;
    const paginasDaFolha = paginasSelecionadas.slice(inicio, inicio + paginasPorFolha);

    const folha = document.createElement("div");
    folha.classList.add("print-sheet");
    folha.style.display = "grid";
    folha.style.gap = `${FOLHA_GAP}px`;
    folha.style.padding = `${FOLHA_PADDING}px`;
    folha.style.background = "#fff";
    folha.style.margin = "20px auto";
    folha.style.boxShadow = "0 0 10px rgba(0,0,0,0.2)";
    folha.style.width = `${tamanhoFolha.largura}px`;
    folha.style.height = `${tamanhoFolha.altura}px`;
    folha.style.gridTemplateColumns = `repeat(${configLayout.colunas}, minmax(0, 1fr))`;
    folha.style.gridTemplateRows = `repeat(${configLayout.linhas}, minmax(0, 1fr))`;

    container.appendChild(folha);

    const areaLargura = tamanhoFolha.largura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.colunas - 1));
    const areaAltura = tamanhoFolha.altura - (FOLHA_PADDING * 2) - (FOLHA_GAP * (configLayout.linhas - 1));
    const larguraCelula = areaLargura / configLayout.colunas;
    const alturaCelula = areaAltura / configLayout.linhas;
    const dpr = Math.min(window.devicePixelRatio || 1, QUALIDADE_MAX_DPR);

    for (const numeroPagina of paginasDaFolha) {
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
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";
        wrapper.style.justifyContent = "center";
        wrapper.style.overflow = "hidden";
        wrapper.style.background = "#fff";
        wrapper.style.border = "1px solid #e5e7eb";

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

function proximaFolha() {
    if (!pdfDoc) {
        return;
    }
    const total = totalFolhasVisualizacao();
    if (folhaAtual < total) {
        folhaAtual += 1;
        atualizarPreview();
    }
}

function folhaAnterior() {
    if (!pdfDoc) {
        return;
    }
    if (folhaAtual > 1) {
        folhaAtual -= 1;
        atualizarPreview();
    }
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
