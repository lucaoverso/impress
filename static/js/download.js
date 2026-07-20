const { garantirToken, criarHeadersAuth, encerrarSessao } = window.AppAuth;
const { fetchJson } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);
const INTERVALO_POLLING_DOWNLOAD_MS = 2000;
const TIMEOUT_POLLING_DOWNLOAD_MS = 15 * 60 * 1000;

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
let temporizadorBarraProgresso = null;

function esperar(ms) {
    return new Promise((resolve) => {
        window.setTimeout(resolve, ms);
    });
}

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
    if (!elementos.secaoDetalhes) return;
    elementos.secaoDetalhes.hidden = false;
    elementos.secaoDetalhes.style.display = "grid";
}

function obterElementoRotuloBotao(botao) {
    return botao?.querySelector(".download-progress-label") || null;
}

function definirTextoBotao(botao, texto) {
    if (!botao) return;
    const rotuloElemento = obterElementoRotuloBotao(botao);
    if (rotuloElemento) {
        rotuloElemento.textContent = texto;
        return;
    }
    botao.textContent = texto;
}

function alternarEstadoCarregando(botao, carregando, textoNormal, textoCarregando) {
    if (!botao) return;
    botao.disabled = carregando;
    definirTextoBotao(botao, carregando ? textoCarregando : textoNormal);
}

function definirBotaoDesabilitado(botao, desabilitado, textoNormal) {
    if (!botao) return;
    botao.disabled = desabilitado;
    botao.classList.remove("is-busy", "is-complete");
    definirTextoBotao(botao, textoNormal);
}

function limparTemporizadorBarraProgresso() {
    if (!temporizadorBarraProgresso) return;
    window.clearTimeout(temporizadorBarraProgresso);
    temporizadorBarraProgresso = null;
}

function iniciarBarraProgresso(botao, texto = "Preparando download...") {
    if (!botao) return;
    limparTemporizadorBarraProgresso();
    botao.disabled = true;
    botao.classList.remove("is-complete");
    botao.classList.add("is-busy");
    definirTextoBotao(botao, texto);
}

function concluirBarraProgresso(botao, texto = "Download iniciado") {
    if (!botao) return;
    limparTemporizadorBarraProgresso();
    botao.classList.remove("is-busy");
    botao.classList.add("is-complete");
    definirTextoBotao(botao, texto);
    temporizadorBarraProgresso = window.setTimeout(() => {
        botao.classList.remove("is-complete");
    }, 700);
}

function obterRotuloPadraoBotao(formato, botao) {
    if (formato === "mp3") {
        return "Baixar Audio (MP3)";
    }
    return botao?.dataset.rotuloPadrao || "Baixar Vídeo";
}

function obterTextoBotaoDownloadPorStatus(formato, status) {
    const statusNormalizado = String(status || "").trim().toUpperCase();
    if (statusNormalizado === "PENDENTE") {
        return "Entrando na fila...";
    }
    if (statusNormalizado === "PROCESSANDO") {
        return formato === "mp3" ? "Convertendo audio..." : "Preparando arquivo...";
    }
    return "Preparando download...";
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
        elementos.btnBaixarMp4.dataset.rotuloPadrao = "Baixar Vídeo";
        definirBotaoDesabilitado(elementos.btnBaixarMp4, true, "Baixar Vídeo");
        return;
    }

    const rotulo = `Baixar Vídeo em ${opcaoSelecionada.rotulo}`;
    elementos.btnBaixarMp4.dataset.rotuloPadrao = rotulo;
    definirBotaoDesabilitado(elementos.btnBaixarMp4, false, rotulo);
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
    elementos.previewMiniatura.hidden = !info.miniatura_url;
    elementos.previewTitulo.textContent = info.titulo || "Vídeo sem título";
    elementos.previewDuracao.textContent = info.duracao_texto || "--:--";
    elementos.previewAutor.textContent = info.autor || "Canal não informado";
    elementos.previewResolucao.textContent = info.resolucao_maxima_video || "Qualidade não informada";
    configurarOpcoesMp4(info.qualidades_mp4 || []);
    elementos.btnBaixarMp3.disabled = !info.mp3_disponivel;
    const existeMp4Habilitado = (info.qualidades_mp4 || []).some((item) => item.habilitado);
    if (!existeMp4Habilitado && !info.mp3_disponivel) {
        const mensagem = info.ffmpeg_disponivel
            ? "Este vídeo não oferece formatos compatíveis com MP4 720p+ nesta tela. Tente outro vídeo ou use um link com maior qualidade."
            : "Este vídeo precisa de ffmpeg no servidor para liberar os downloads em MP4/MP3.";
        exibirMensagem(elementos.mensagemDetalhes, mensagem);
        return;
    }
    if (!existeMp4Habilitado) {
        exibirMensagem(
            elementos.mensagemDetalhes,
            "Nenhuma qualidade MP4 está disponível para este vídeo com a configuração atual do servidor.",
        );
        return;
    }
    if (!info.mp3_disponivel) {
        exibirMensagem(
            elementos.mensagemDetalhes,
            "MP3 indisponível no momento: instale o ffmpeg no servidor para habilitar a conversão.",
        );
        return;
    }
    exibirMensagem(elementos.mensagemDetalhes, "");
}

function mostrarPainelDetalhes() {
    elementos.secaoFormulario.hidden = true;
    ativarPainel();
}

function mostrarFormulario() {
    elementos.secaoFormulario.hidden = false;
    if (!elementos.secaoDetalhes) return;
    elementos.secaoDetalhes.hidden = true;
    elementos.secaoDetalhes.style.display = "";
}

async function carregarDetalhes(url) {
    bloquearOpcoesMp4("Carregando...");
    alternarEstadoCarregando(elementos.btnBaixarMp3, true, "Salvar em MP3", "Carregando...");
    exibirMensagem(elementos.mensagemDetalhes, "");
    mostrarPainelDetalhes();

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
    } catch (erro) {
        mostrarFormulario();
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
    const rotulo = obterRotuloPadraoBotao(formato, botao);
    iniciarBarraProgresso(botao, "Preparando download...");
    exibirMensagem(elementos.mensagemDetalhes, "");

    try {
        const job = await fetchJson("/download/jobs", {
            method: "POST",
            headers: {
                ...headers,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ url: infoAtual.url, formato, qualidade }),
        });

        let jobAtual = job;
        if (jobAtual?.mensagem_status) {
            exibirMensagem(elementos.mensagemDetalhes, jobAtual.mensagem_status);
        }
        if (String(jobAtual?.status || "").toUpperCase() === "ERRO") {
            throw new Error(jobAtual?.erro_mensagem || jobAtual?.mensagem_status || "Falha ao preparar o download.");
        }

        const inicioPolling = Date.now();
        while (!jobAtual?.pronto) {
            if ((Date.now() - inicioPolling) >= TIMEOUT_POLLING_DOWNLOAD_MS) {
                throw new Error("O download demorou mais do que o esperado. Tente novamente.");
            }

            definirTextoBotao(botao, obterTextoBotaoDownloadPorStatus(formato, jobAtual?.status));
            await esperar(INTERVALO_POLLING_DOWNLOAD_MS);
            jobAtual = await fetchJson(`/download/jobs/${encodeURIComponent(job.id)}`, {
                headers,
            });

            if (jobAtual?.mensagem_status) {
                exibirMensagem(elementos.mensagemDetalhes, jobAtual.mensagem_status);
            }

            if (String(jobAtual?.status || "").toUpperCase() === "ERRO") {
                throw new Error(jobAtual?.erro_mensagem || jobAtual?.mensagem_status || "Falha ao preparar o download.");
            }
        }

        definirTextoBotao(botao, "Liberando download...");
        const ticket = await fetchJson(`/download/jobs/${encodeURIComponent(job.id)}/ticket`, {
            method: "POST",
            headers,
        });

        definirTextoBotao(botao, "Iniciando download...");
        const link = document.createElement("a");
        link.href = ticket.download_url;
        if (ticket.arquivo_nome) {
            link.download = ticket.arquivo_nome;
        }
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        link.remove();
        concluirBarraProgresso(botao, "Download iniciado");
        exibirMensagem(elementos.mensagemDetalhes, "");
    } catch (erro) {
        botao.classList.remove("is-busy", "is-complete");
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
        carregarDetalhes(url);
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
        mostrarFormulario();
        return;
    }

    elementos.campoUrl.value = url;
    carregarDetalhes(url);
}

inicializarPagina();
