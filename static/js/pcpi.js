const token = localStorage.getItem("token");

if (!token) {
    window.location.href = "/login-page";
}

const headers = {
    "Authorization": `Bearer ${token}`
};

const headersJson = {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
};

const TURNOS_FALLBACK = [
    { id: "INTEGRAL", nome: "Periodo integral" },
    { id: "MATUTINO", nome: "Matutino" },
    { id: "VESPERTINO", nome: "Vespertino" },
    { id: "VESPERTINO_EM", nome: "Vespertino E.M." }
];

const TIPOS_ACAO_PCPI = [
    {
        id: "reuniao",
        nome: "Reuniao",
        descricaoExemplo: "Alinhamento de demandas institucionais e organizacao das acoes do turno.",
        observacoesExemplo: "Participacao com equipe gestora, coordenacao ou setores da escola."
    },
    {
        id: "orientacao",
        nome: "Orientacao",
        descricaoExemplo: "Orientacao para uso pedagogico de recurso ou ferramenta digital.",
        observacoesExemplo: "Ex.: apoio ao uso de Canva, planilhas, projetor ou ambiente virtual."
    },
    {
        id: "rede_social",
        nome: "Rede social",
        descricaoExemplo: "Elaboracao de conteudos digitais para divulgacao institucional.",
        observacoesExemplo: "Registrar campanha, card, postagem ou cobertura de atividade escolar."
    },
    {
        id: "registro",
        nome: "Registro",
        descricaoExemplo: "Atualizacao e sistematizacao dos registros administrativos do turno.",
        observacoesExemplo: "Use para lancamentos, conferencias ou organizacao documental."
    },
    {
        id: "impressao",
        nome: "Impressao",
        descricaoExemplo: "Organizacao de impressoes de materiais pedagogicos solicitados no turno.",
        observacoesExemplo: "Informe, se necessario, volume, finalidade ou docentes atendidos."
    },
    {
        id: "adequacao_impressao",
        nome: "Adequacao de impressao",
        descricaoExemplo: "Adequacao de materiais impressos conforme necessidades pedagogicas especificas.",
        observacoesExemplo: "Detalhe a adaptacao realizada ou o publico atendido."
    },
    {
        id: "projeto",
        nome: "Projeto",
        descricaoExemplo: "Acompanhamento e organizacao de acoes relacionadas a projeto pedagogico.",
        observacoesExemplo: "Informe nome do projeto, etapa ou encaminhamento principal."
    },
    {
        id: "gremio",
        nome: "Gremio",
        descricaoExemplo: "Acompanhamento de demandas e registros do Gremio Estudantil.",
        observacoesExemplo: "Ex.: organizacao de reuniao, pauta ou atividade de representacao estudantil."
    },
    {
        id: "colaboracao",
        nome: "Colaboracao",
        descricaoExemplo: "Colaboracao em acao pedagogica ou tecnologica desenvolvida no turno.",
        observacoesExemplo: "Informe a equipe, setor ou atividade apoiada."
    },
    {
        id: "evento",
        nome: "Evento",
        descricaoExemplo: "Organizacao e apoio as acoes relacionadas a evento institucional.",
        observacoesExemplo: "Ex.: mostra, culminancia, palestra, recepcao ou atividade coletiva."
    },
    {
        id: "planejamento",
        nome: "Planejamento",
        descricaoExemplo: "Planejamento das atividades e organizacao dos recursos do turno.",
        observacoesExemplo: "Use para registrar definicao de demandas, materiais e prioridades."
    },
    {
        id: "formulario2",
        nome: "Formulario II",
        descricaoExemplo: "Elaboracao do Formulario II referente a projeto ou atividade pedagogica.",
        observacoesExemplo: "Informe objetivos, metodologia, avaliacao ou etapa do documento."
    }
];

const CATEGORIAS_AUTOMATICAS = {
    ste: "STE",
    tecnologia_educacional: "Tecnologia educacional",
    recurso_audiovisual: "Recurso audiovisual",
    apoio_pedagogico: "Apoio pedagogico"
};

let usuarioAtual = null;
let turnos = [];
let sugestoesAtuais = null;
let registrosManuaisAtuais = null;

function el(id) {
    return document.getElementById(id);
}

function encerrarSessao() {
    localStorage.removeItem("token");
    localStorage.removeItem("token_expira_em");
    window.location.href = "/login-page";
}

async function fetchComAuth(url, options = {}) {
    const resposta = await fetch(url, options);
    if (resposta.status === 401) {
        encerrarSessao();
        throw new Error("Sessao expirada.");
    }
    return resposta;
}

function hojeIso() {
    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, "0");
    const dia = String(agora.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
}

function paraDataBr(dataIso) {
    const partes = String(dataIso || "").split("-");
    if (partes.length !== 3) {
        return String(dataIso || "");
    }
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

function normalizarTurnoId(turnoId) {
    return String(turnoId || "").trim().toUpperCase();
}

function nomeTurno(turnoId) {
    const turnoNormalizado = normalizarTurnoId(turnoId);
    const turno = turnos.find((item) => normalizarTurnoId(item.id) === turnoNormalizado);
    return turno ? String(turno.nome || turno.id) : turnoNormalizado;
}

function tipoAcaoLabel(tipoAcao) {
    const tipo = TIPOS_ACAO_PCPI.find((item) => item.id === String(tipoAcao || "").trim());
    return tipo ? tipo.nome : "Acao manual";
}

function obterConfigTipoAcao(tipoAcao) {
    return TIPOS_ACAO_PCPI.find((item) => item.id === String(tipoAcao || "").trim()) || null;
}

function categoriaUsoLabel(categoria) {
    const chave = String(categoria || "").trim();
    return CATEGORIAS_AUTOMATICAS[chave] || "Agendamento automatico";
}

function escaparHtml(valor) {
    return String(valor || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
}

function definirMensagem(id, texto, erro = false) {
    const alvo = el(id);
    if (!alvo) {
        return;
    }
    alvo.textContent = texto || "";
    alvo.dataset.state = erro ? "erro" : "ok";
}

function limparMensagem(id) {
    definirMensagem(id, "", false);
}

async function obterMensagemErroResposta(resposta, fallback) {
    try {
        const dados = await resposta.json();
        if (typeof dados?.detail === "string" && dados.detail.trim()) {
            return dados.detail.trim();
        }
        if (typeof dados?.mensagem === "string" && dados.mensagem.trim()) {
            return dados.mensagem.trim();
        }
    } catch (_erro) {
        // Resposta sem JSON util.
    }
    return fallback;
}

function obterFiltrosAtuais() {
    return {
        data: String(el("pcpiData").value || "").trim(),
        turno: normalizarTurnoId(el("pcpiTurno").value),
    };
}

function validarFiltrosSelecionados() {
    const filtros = obterFiltrosAtuais();
    if (!filtros.data) {
        throw new Error("Selecione a data do registro.");
    }
    if (!filtros.turno) {
        throw new Error("Selecione o turno do registro.");
    }
    return filtros;
}

function preencherTurnosSelect() {
    const select = el("pcpiTurno");
    select.innerHTML = "";

    turnos.forEach((turno) => {
        const option = document.createElement("option");
        option.value = turno.id;
        option.textContent = turno.nome;
        select.appendChild(option);
    });

    const turnoPadrao = turnos.find((turno) => normalizarTurnoId(turno.id) === "MATUTINO");
    if (turnoPadrao) {
        select.value = turnoPadrao.id;
    }
}

function preencherTiposAcao() {
    const select = el("pcpiTipoAcao");
    select.innerHTML = "";

    TIPOS_ACAO_PCPI.forEach((tipo) => {
        const option = document.createElement("option");
        option.value = tipo.id;
        option.textContent = tipo.nome;
        select.appendChild(option);
    });

    aplicarAjudaTipoAcao();
}

function componentesFormatados(item) {
    const componentes = Array.isArray(item?.componentes) ? item.componentes.filter(Boolean) : [];
    return componentes.length > 0 ? componentes.join(", ") : "Componente nao informado";
}

function aulaFormatada(aula) {
    const valor = String(aula || "").trim();
    if (!valor) {
        return "Aula nao informada";
    }
    return `${valor}a aula`;
}

function criarEstadoVazio(mensagem) {
    return `<li class="pcpi-empty">${escaparHtml(mensagem)}</li>`;
}

function renderizarAgendamentosAutomaticos() {
    const lista = el("listaAgendamentosPcpi");
    const itens = Array.isArray(sugestoesAtuais?.itens) ? sugestoesAtuais.itens : [];

    if (itens.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum agendamento importado para a data e turno selecionados.");
        atualizarResumoAutomatico();
        atualizarResumoTexto();
        return;
    }

    lista.innerHTML = itens.map((item) => {
        const componentes = componentesFormatados(item);
        const tema = String(item.tema_aula || "").trim();
        const observacao = String(item.observacao || "").trim();
        const turma = String(item.turma || "").trim() || "Turma nao informada";
        const professor = String(item.professor_nome || "").trim() || "Professor nao informado";
        const recurso = String(item.recurso_nome || "").trim() || "Recurso nao informado";
        const categoria = categoriaUsoLabel(item.categoria_uso);

        return `
            <li class="pcpi-item pcpi-item-automatico">
                <label class="pcpi-checkbox-row">
                    <input
                        class="pcpi-agendamento-checkbox"
                        type="checkbox"
                        data-agendamento-id="${Number(item.agendamento_id || 0)}"
                        checked
                    >
                    <div class="pcpi-item-body">
                        <div class="pcpi-item-top">
                            <strong>${escaparHtml(recurso)}</strong>
                            <div class="pcpi-tag-group">
                                <span class="pcpi-chip pcpi-chip-automatico">Automatico</span>
                                <span class="pcpi-chip">${escaparHtml(categoria)}</span>
                            </div>
                        </div>
                        <p class="pcpi-item-line">${escaparHtml(professor)} | ${escaparHtml(componentes)}</p>
                        <p class="pcpi-item-line">${escaparHtml(turma)} | ${escaparHtml(aulaFormatada(item.aula))}</p>
                        ${tema ? `<p class="pcpi-item-note">${escaparHtml(tema)}</p>` : ""}
                        ${observacao ? `<p class="pcpi-item-note is-secondary">${escaparHtml(observacao)}</p>` : ""}
                    </div>
                </label>
            </li>
        `;
    }).join("");

    lista.querySelectorAll(".pcpi-agendamento-checkbox").forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
            atualizarResumoAutomatico();
            atualizarResumoTexto();
        });
    });

    atualizarResumoAutomatico();
    atualizarResumoTexto();
}

function renderizarRegistrosManuais() {
    const lista = el("listaRegistrosManuaisPcpi");
    const itens = Array.isArray(registrosManuaisAtuais?.itens) ? registrosManuaisAtuais.itens : [];

    if (itens.length === 0) {
        lista.innerHTML = criarEstadoVazio("Nenhum registro manual salvo para este turno.");
        el("pcpiResumoManual").textContent = "0 registros";
        atualizarResumoTexto();
        return;
    }

    lista.innerHTML = itens.map((item) => {
        const professor = String(item.professor_nome || "").trim();
        const componente = String(item.componente || "").trim();
        const turma = String(item.turma || "").trim();
        const observacoes = String(item.observacoes || "").trim();
        const detalhes = [professor, componente, turma].filter(Boolean).join(" | ");

        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-item-body">
                    <div class="pcpi-item-top">
                        <strong>${escaparHtml(tipoAcaoLabel(item.tipo_acao))}</strong>
                        <div class="pcpi-tag-group">
                            <span class="pcpi-chip pcpi-chip-manual">Manual</span>
                        </div>
                    </div>
                    <p class="pcpi-item-line">${escaparHtml(item.descricao_curta || "")}</p>
                    ${detalhes ? `<p class="pcpi-item-note">${escaparHtml(detalhes)}</p>` : ""}
                    ${observacoes ? `<p class="pcpi-item-note is-secondary">${escaparHtml(observacoes)}</p>` : ""}
                </div>
            </li>
        `;
    }).join("");

    const total = itens.length;
    el("pcpiResumoManual").textContent = `${total} ${total === 1 ? "registro" : "registros"}`;
    atualizarResumoTexto();
}

function obterAgendamentoIdsSelecionados() {
    return Array.from(document.querySelectorAll(".pcpi-agendamento-checkbox:checked"))
        .map((checkbox) => Number(checkbox.dataset.agendamentoId || 0))
        .filter((valor) => Number.isInteger(valor) && valor > 0);
}

function atualizarResumoTurno() {
    const filtros = obterFiltrosAtuais();
    const totalAutomaticos = Number(sugestoesAtuais?.resumo?.total_agendamentos || 0);
    const totalManuais = Number(registrosManuaisAtuais?.total_registros || 0);

    if (!filtros.data || !filtros.turno) {
        el("pcpiResumoTurno").textContent = "";
        return;
    }

    el("pcpiResumoTurno").textContent = `${nomeTurno(filtros.turno)} de ${paraDataBr(filtros.data)} com ${totalAutomaticos} agendamento(s) importado(s) e ${totalManuais} registro(s) manual(is).`;
}

function atualizarResumoAutomatico() {
    const total = Number(sugestoesAtuais?.resumo?.total_agendamentos || 0);
    const selecionados = obterAgendamentoIdsSelecionados().length;
    const totalProfessores = Number(sugestoesAtuais?.resumo?.total_professores || 0);
    const totalTurmas = Number(sugestoesAtuais?.resumo?.total_turmas || 0);

    el("pcpiResumoAutomatico").textContent = `${selecionados} de ${total} agendamento(s) marcados | ${totalProfessores} professor(es) | ${totalTurmas} turma(s).`;
}

function atualizarResumoTexto() {
    const selecionados = obterAgendamentoIdsSelecionados().length;
    const totalManuais = Number(registrosManuaisAtuais?.total_registros || 0);
    el("pcpiResumoTexto").textContent = `Texto baseado em ${selecionados} agendamento(s) selecionado(s) e ${totalManuais} registro(s) manual(is) salvo(s).`;
}

function aplicarAjudaTipoAcao() {
    const config = obterConfigTipoAcao(el("pcpiTipoAcao").value);
    const descricao = config?.descricaoExemplo || "Descreva objetivamente a acao realizada pelo PCPI no turno.";
    const observacoes = config?.observacoesExemplo || "Use observacoes para complementar contexto, publico atendido ou encaminhamentos.";

    el("pcpiAjudaManual").textContent = `Exemplo: ${descricao} ${observacoes}`;
    el("pcpiDescricaoCurta").placeholder = descricao;
    el("pcpiObservacoes").placeholder = observacoes;
}

function limparFormularioManual() {
    el("pcpiProfessorNome").value = "";
    el("pcpiComponente").value = "";
    el("pcpiTurma").value = "";
    el("pcpiDescricaoCurta").value = "";
    el("pcpiObservacoes").value = "";
    limparMensagem("msgPcpiManual");
}

async function carregarUsuario() {
    const resposta = await fetchComAuth("/me", { headers });
    if (!resposta.ok) {
        encerrarSessao();
        return false;
    }

    usuarioAtual = await resposta.json();
    const modulos = new Set((usuarioAtual.modulos || []).map((item) => String(item).trim().toLowerCase()));
    if (!modulos.has("pcpi")) {
        window.location.href = "/servicos";
        return false;
    }

    const primeiroNome = String(usuarioAtual.nome || "").trim().split(" ")[0] || "Usuario";
    el("pcpiUsuario").textContent = `${primeiroNome} | modulo PCPI`;
    return true;
}

async function carregarTurnos() {
    try {
        const resposta = await fetchComAuth("/agendamento/opcoes", { headers });
        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel carregar os turnos."));
        }

        const dados = await resposta.json();
        turnos = Array.isArray(dados.turnos) && dados.turnos.length > 0 ? dados.turnos : TURNOS_FALLBACK;
    } catch (_erro) {
        turnos = TURNOS_FALLBACK;
    }

    preencherTurnosSelect();
}

async function carregarContextoPcpi({ gerarTextoAutomaticamente = true } = {}) {
    limparMensagem("msgPcpiGeral");

    let filtros;
    try {
        filtros = validarFiltrosSelecionados();
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Selecione data e turno.", true);
        return;
    }

    definirMensagem("msgPcpiGeral", "Carregando dados do turno...");

    try {
        const query = `data=${encodeURIComponent(filtros.data)}&turno=${encodeURIComponent(filtros.turno)}`;
        const [resSugestoes, resRegistros] = await Promise.all([
            fetchComAuth(`/pcpi/sugestoes?${query}`, { headers }),
            fetchComAuth(`/pcpi/registros-manuais?${query}`, { headers })
        ]);

        if (!resSugestoes.ok) {
            throw new Error(await obterMensagemErroResposta(resSugestoes, "Nao foi possivel carregar os agendamentos do PCPI."));
        }
        if (!resRegistros.ok) {
            throw new Error(await obterMensagemErroResposta(resRegistros, "Nao foi possivel carregar os registros manuais do PCPI."));
        }

        sugestoesAtuais = await resSugestoes.json();
        registrosManuaisAtuais = await resRegistros.json();

        renderizarAgendamentosAutomaticos();
        renderizarRegistrosManuais();
        atualizarResumoTurno();

        if (gerarTextoAutomaticamente) {
            await gerarTextoPcpi();
        } else {
            definirMensagem("msgPcpiGeral", "Dados do turno atualizados.");
        }
    } catch (erro) {
        sugestoesAtuais = null;
        registrosManuaisAtuais = null;
        el("listaAgendamentosPcpi").innerHTML = criarEstadoVazio("Nao foi possivel carregar os agendamentos.");
        el("listaRegistrosManuaisPcpi").innerHTML = criarEstadoVazio("Nao foi possivel carregar os registros manuais.");
        el("pcpiTextoFinal").value = "";
        el("pcpiResumoTurno").textContent = "";
        el("pcpiResumoAutomatico").textContent = "0 de 0 agendamento(s) marcados | 0 professor(es) | 0 turma(s).";
        el("pcpiResumoManual").textContent = "0 registros";
        atualizarResumoTexto();
        definirMensagem("msgPcpiGeral", erro.message || "Erro ao carregar o modulo PCPI.", true);
    }
}

async function gerarTextoPcpi() {
    limparMensagem("msgPcpiGeral");

    let filtros;
    try {
        filtros = validarFiltrosSelecionados();
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Selecione data e turno.", true);
        return;
    }

    try {
        const resposta = await fetchComAuth("/pcpi/texto/preview", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                data: filtros.data,
                turno: filtros.turno,
                agendamento_ids: obterAgendamentoIdsSelecionados()
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel gerar o texto do PCPI."));
        }

        const dados = await resposta.json();
        el("pcpiTextoFinal").value = String(dados.texto || "");
        definirMensagem("msgPcpiGeral", "Texto gerado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Falha ao gerar o texto do PCPI.", true);
    }
}

async function salvarRegistroManualPcpi(event) {
    event.preventDefault();
    limparMensagem("msgPcpiManual");

    let filtros;
    try {
        filtros = validarFiltrosSelecionados();
    } catch (erro) {
        definirMensagem("msgPcpiManual", erro.message || "Selecione data e turno antes de salvar.", true);
        return;
    }

    const descricaoCurta = String(el("pcpiDescricaoCurta").value || "").trim();
    if (!descricaoCurta) {
        definirMensagem("msgPcpiManual", "Informe a descricao curta da acao manual.", true);
        el("pcpiDescricaoCurta").focus();
        return;
    }

    const payload = {
        data: filtros.data,
        turno: filtros.turno,
        tipo_acao: el("pcpiTipoAcao").value,
        professor_nome: String(el("pcpiProfessorNome").value || "").trim(),
        componente: String(el("pcpiComponente").value || "").trim(),
        turma: String(el("pcpiTurma").value || "").trim(),
        descricao_curta: descricaoCurta,
        observacoes: String(el("pcpiObservacoes").value || "").trim()
    };

    try {
        const resposta = await fetchComAuth("/pcpi/registros-manuais", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify(payload)
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel salvar a acao manual."));
        }

        limparFormularioManual();
        definirMensagem("msgPcpiManual", "Acao manual salva com sucesso.");
        await carregarContextoPcpi({ gerarTextoAutomaticamente: true });
    } catch (erro) {
        definirMensagem("msgPcpiManual", erro.message || "Erro ao salvar a acao manual.", true);
    }
}

async function copiarTextoPcpi() {
    limparMensagem("msgPcpiGeral");
    const texto = String(el("pcpiTextoFinal").value || "").trim();
    if (!texto) {
        definirMensagem("msgPcpiGeral", "Nao ha texto para copiar.", true);
        return;
    }

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(texto);
        } else {
            el("pcpiTextoFinal").select();
            document.execCommand("copy");
        }
        definirMensagem("msgPcpiGeral", "Texto copiado para a area de transferencia.");
    } catch (_erro) {
        definirMensagem("msgPcpiGeral", "Nao foi possivel copiar o texto.", true);
    }
}

function definirSelecaoAgendamentos(marcado) {
    document.querySelectorAll(".pcpi-agendamento-checkbox").forEach((checkbox) => {
        checkbox.checked = Boolean(marcado);
    });
    atualizarResumoAutomatico();
    atualizarResumoTexto();
}

function registrarEventos() {
    el("formFiltrosPcpi").addEventListener("submit", async (event) => {
        event.preventDefault();
        await carregarContextoPcpi({ gerarTextoAutomaticamente: true });
    });

    el("btnGerarTexto").addEventListener("click", async () => {
        await gerarTextoPcpi();
    });

    el("btnMarcarTodosAgendamentos").addEventListener("click", async () => {
        definirSelecaoAgendamentos(true);
        await gerarTextoPcpi();
    });

    el("btnLimparAgendamentos").addEventListener("click", async () => {
        definirSelecaoAgendamentos(false);
        await gerarTextoPcpi();
    });

    el("formRegistroManualPcpi").addEventListener("submit", salvarRegistroManualPcpi);

    el("pcpiTipoAcao").addEventListener("change", () => {
        aplicarAjudaTipoAcao();
    });

    el("btnLimparRegistroManualPcpi").addEventListener("click", () => {
        limparFormularioManual();
    });

    el("btnCopiarTextoPcpi").addEventListener("click", async () => {
        await copiarTextoPcpi();
    });

    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });

    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });
}

async function iniciarPcpi() {
    preencherTiposAcao();
    el("pcpiData").value = hojeIso();

    registrarEventos();
    const podeProsseguir = await carregarUsuario();
    if (!podeProsseguir) {
        return;
    }
    await carregarTurnos();
    await carregarContextoPcpi({ gerarTextoAutomaticamente: true });
}

iniciarPcpi();
