const { garantirToken, criarHeadersAuth, encerrarSessao } = window.AppAuth;
const { fetchJson, fetchResposta } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);

const elementos = {
    secaoFormulario: document.getElementById("secaoFormulario"),
    secaoDetalhes: document.getElementById("secaoDetalhes"),
    campoUrl: document.getElementById("campoYoutubeUrl"),
    formYoutube: document.getElementById("formYoutube"),
    mensagemFormulario: document.getElementById("mensagemFormulario"),
    mensagemDetalhes: document.getElementById("mensagemDetalhes"),
    previewMiniatura: document.getElementById("previewMiniatura"),
    previewTitulo: document.getElementById("previewTitulo"),
    previewDuracao: document.getElementById("previewDuracao"),
    previewAutor: document.getElementById("previewAutor"),
    previewResolucao: document.getElementById("previewResolucao"),
    opcoesMp4: Array.from(document.querySelectorAll("[data-qualidade-opcao]")),
    radiosMp4: Array.from(document.querySelectorAll("input[name='qualidadeMp4']")),
    btnBaixarMp4: document.getElementById("btnBaixarMp4"),
    btnBaixarMp3: document.getElementById("btnBaixarMp3"),
    btnVoltarServicos: document.getElementById("btnVoltarServicos"),
    btnSair: document.getElementById("btnSair"),
};

let infoAtual = null;

function obterUrlAtual() {
    return new URLSearchParams(window.location.search).get("url") || "";
}

function exibirMensagem(elemento, mensagem, esconder = false) {
    if (!elemento) return;
    if (esconder || !mensagem) {
        elemento.hidden = true;
        elemento.textContent = "";
        return;
    }

    elemento.hidden = false;
    elemento.textContent = mensagem;
}

function ativarPainel() {
    const painel = document.querySelector(".download-details");
    painel.style.display = "grid";
}

function alternarEstadoCarregando(botao, carregando, textoNormal, textoCarregando) {
    if (!botao) return;
    botao.disabled = carregando;
    botao.textContent = carregando ? textoCarregando : textoNormal;
}

function definirBotaoDesabilitado(botao, desabilitado, textoNormal) {
    if (!botao) return;
    botao.disabled = desabilitado;
    botao.textContent = textoNormal;
}

function obterQualidadeMp4Selecionada() {
    const radioSelecionado = elementos.radiosMp4.find((radio) => radio.checked);
    return radioSelecionado?.value || null;
}

function atualizarResumoMp4() {
    const qualidadeSelecionada = obterQualidadeMp4Selecionada();
    const opcoes = Array.isArray(infoAtual?.qualidades_mp4) ? infoAtual.qualidades_mp4 : [];
    const opcaoSelecionada = opcoes.find((item) => item.valor === qualidadeSelecionada);

    if (!qualidadeSelecionada || !opcaoSelecionada) {
        definirBotaoDesabilitado(elementos.btnBaixarMp4, true, "Baixar Vídeo");
        return;
    }

    definirBotaoDesabilitado(elementos.btnBaixarMp4, false, `Baixar Vídeo em ${opcaoSelecionada.rotulo}`);
}

function configurarOpcoesMp4(opcoes = []) {
    const mapa = new Map(opcoes.map((item) => [item.valor, item]));
    const qualidadeAnterior = obterQualidadeMp4Selecionada();
    let primeiraHabilitada = null;

    elementos.opcoesMp4.forEach((opcaoElemento) => {
        const qualidade = opcaoElemento.dataset.qualidadeOpcao;
        const opcao = mapa.get(qualidade);
        const rotulo = opcao?.rotulo || qualidade;
        const radio = opcaoElemento.querySelector("input[name='qualidadeMp4']");
        const rotuloElemento = opcaoElemento.querySelector("[data-qualidade-rotulo]");
        const detalheElemento = opcaoElemento.querySelector("[data-qualidade-detalhe]");

        if (rotuloElemento) {
            rotuloElemento.textContent = rotulo;
        }
        if (detalheElemento) {
            detalheElemento.textContent = opcao?.detalhe || "Qualidade indisponível.";
        }
        if (radio) {
            radio.disabled = !opcao?.habilitado;
            radio.checked = false;
        }

        opcaoElemento.classList.toggle("is-disabled", !opcao?.habilitado);
        opcaoElemento.title = opcao?.detalhe || "Qualidade indisponível.";

        if (!primeiraHabilitada && opcao?.habilitado) {
            primeiraHabilitada = qualidade;
        }
    });

    const qualidadeParaMarcar = mapa.get(qualidadeAnterior)?.habilitado
        ? qualidadeAnterior
        : primeiraHabilitada;
    const radioParaMarcar = elementos.radiosMp4.find((radio) => radio.value === qualidadeParaMarcar);
    if (radioParaMarcar) {
        radioParaMarcar.checked = true;
    }

    atualizarResumoMp4();
}

function bloquearOpcoesMp4(texto = "Carregando...") {
    elementos.opcoesMp4.forEach((opcaoElemento) => {
        const radio = opcaoElemento.querySelector("input[name='qualidadeMp4']");
        const detalheElemento = opcaoElemento.querySelector("[data-qualidade-detalhe]");
        if (radio) {
            radio.checked = false;
            radio.disabled = true;
        }
        if (detalheElemento) {
            detalheElemento.textContent = texto;
        }
        opcaoElemento.classList.add("is-disabled");
    });
    definirBotaoDesabilitado(elementos.btnBaixarMp4, true, "Baixar MP4");
}

function preencherDetalhes(info) {
    infoAtual = info;
    elementos.previewMiniatura.src = info.miniatura_url || "";
    elementos.previewMiniatura.alt = `Miniatura de ${info.titulo}`;
    elementos.previewTitulo.textContent = info.titulo || "Vídeo sem título";
    elementos.previewDuracao.textContent = info.duracao_texto || "--:--";
    elementos.previewAutor.textContent = info.autor || "Canal não informado";
    elementos.previewResolucao.textContent = info.resolucao_maxima_video || "Qualidade não informada";
    configurarOpcoesMp4(info.qualidades_mp4 || []);
    elementos.btnBaixarMp3.disabled = !info.mp3_disponivel;
}

async function carregarDetalhes(url) {
    bloquearOpcoesMp4("Carregando...");
    alternarEstadoCarregando(elementos.btnBaixarMp3, true, "Salvar em MP3", "Carregando...");
    exibirMensagem(elementos.mensagemDetalhes, "");

    try {
        const info = await fetchJson("/download/info", {
            method: "POST",
            headers: {
                ...headers,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url }),
        });

        preencherDetalhes(info);
        elementos.secaoFormulario.hidden = true;
        elementos.secaoDetalhes.hidden = false;
    } catch (erro) {
        exibirMensagem(elementos.mensagemDetalhes, erro.message || "Não foi possível carregar os detalhes do vídeo.");
    } finally {
        if (!infoAtual) {
            bloquearOpcoesMp4("Qualidade indisponível.");
        }
        definirBotaoDesabilitado(
            elementos.btnBaixarMp3,
            !infoAtual?.mp3_disponivel,
            "Baixar Audio (MP3)",
        );
    }
}

function obterNomeArquivo(resposta, fallback) {
    const contentDisposition = String(resposta.headers.get("content-disposition") || "");
    const matchUtf = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (matchUtf?.[1]) {
        return decodeURIComponent(matchUtf[1]);
    }

    const matchSimples = contentDisposition.match(/filename="([^"]+)"/i);
    if (matchSimples?.[1]) {
        return matchSimples[1];
    }

    return fallback;
}

async function iniciarDownload(formato, qualidade = null) {
    if (!infoAtual?.url) {
        exibirMensagem(elementos.mensagemDetalhes, "Carregue os detalhes do vídeo antes de baixar.");
        return;
    }

    if (formato === "mp4" && !qualidade) {
        exibirMensagem(elementos.mensagemDetalhes, "Selecione uma qualidade MP4 antes de iniciar o download.");
        return;
    }

    const botao = formato === "mp3"
        ? elementos.btnBaixarMp3
        : elementos.btnBaixarMp4;
    const rotulo = formato === "mp3"
        ? "Salvar em MP3"
        : botao?.textContent || "Baixar MP4";
    alternarEstadoCarregando(botao, true, rotulo, "Preparando...");
    exibirMensagem(elementos.mensagemDetalhes, "");

    try {
        const resposta = await fetchResposta("/download/arquivo", {
            method: "POST",
            headers: {
                ...headers,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url: infoAtual.url, formato, qualidade }),
        });

        const blob = await resposta.blob();
        const nomeArquivo = obterNomeArquivo(resposta, `youtube.${formato}`);
        const urlBlob = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = urlBlob;
        link.download = nomeArquivo;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(urlBlob);
    } catch (erro) {
        exibirMensagem(elementos.mensagemDetalhes, erro.message || "Falha ao baixar o arquivo.");
    } finally {
        if (formato === "mp3") {
            definirBotaoDesabilitado(
                botao,
                !infoAtual?.mp3_disponivel,
                rotulo,
            );
            return;
        }

        atualizarResumoMp4();
    }
}

function irParaFormulario() {
    window.location.href = "/download";
}

function registrarEventos() {
    elementos.formYoutube.addEventListener("submit", (event) => {
        event.preventDefault();
        const url = String(elementos.campoUrl.value || "").trim();
        if (!url) {
            exibirMensagem(elementos.mensagemFormulario, "Cole um link do YouTube para continuar.");
            return;
        }

        exibirMensagem(elementos.mensagemFormulario, "");
        window.location.href = `/download/detalhes?url=${encodeURIComponent(url)}`;
    });

    elementos.radiosMp4.forEach((radio) => {
        radio.addEventListener("change", () => {
            atualizarResumoMp4();
        });
    });
    elementos.btnBaixarMp4.addEventListener("click", () => iniciarDownload("mp4", obterQualidadeMp4Selecionada()));
    elementos.btnBaixarMp3.addEventListener("click", () => iniciarDownload("mp3"));
    elementos.btnVoltarServicos.addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    elementos.btnSair.addEventListener("click", () => {
        encerrarSessao();
    });
}

function inicializarPagina() {
    registrarEventos();
    const url = obterUrlAtual();
    if (!url) {
        elementos.secaoFormulario.hidden = false;
        elementos.secaoDetalhes.hidden = true;
        return;
    }

    elementos.campoUrl.value = url;
    carregarDetalhes(url);
}

inicializarPagina();
