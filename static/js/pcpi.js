const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    encerrarSessao,
} = window.AppAuth;
const { fetchComAuth, obterMensagemErroResposta } = window.AppApi;
const { hojeIso, paraDataBr, escaparHtml } = window.AppFormat;

const token = garantirToken();
const headers = criarHeadersAuth(token);
const headersJson = criarHeadersJsonAuth(token);

const TURNOS_FALLBACK = [
    { id: "MATUTINO", nome: "Matutino" },
    { id: "VESPERTINO", nome: "Vespertino" }
];

const TURNOS_PCPI_PERMITIDOS = new Set(["MATUTINO", "VESPERTINO"]);

const TIPOS_ACAO_PCPI = [
    {
        id: "reuniao",
        nome: "Reuniao",
        descricaoExemplo: "Alinhamento de demandas institucionais e organizacao das acoes do turno.",
        observacoesExemplo: "Use para registrar reunioes com equipe gestora, coordenacao ou setores."
    },
    {
        id: "orientacao",
        nome: "Orientacao",
        descricaoExemplo: "Orientacao para uso pedagogico de recurso ou ferramenta digital.",
        observacoesExemplo: "Ex.: apoio ao uso de Canva, planilhas, projetor ou ambiente virtual."
    },
    {
        id: "planejamento",
        nome: "Planejamento",
        descricaoExemplo: "Planejamento das atividades e organizacao dos recursos do turno.",
        observacoesExemplo: "Use para registrar definicao de demandas, materiais e prioridades."
    },
    {
        id: "projeto",
        nome: "Projeto",
        descricaoExemplo: "Acompanhamento e organizacao de acoes relacionadas a projeto pedagogico.",
        observacoesExemplo: "Informe nome do projeto, etapa ou encaminhamento principal."
    },
    {
        id: "suporte_aula",
        nome: "Suporte em aula",
        descricaoExemplo: "Apoio prestado durante o desenvolvimento de aula ou atividade orientada.",
        observacoesExemplo: "Registre como o PCPI acompanhou o professor e a turma."
    },
    {
        id: "preparacao_recurso",
        nome: "Preparacao de recurso",
        descricaoExemplo: "Preparacao e organizacao de equipamento, laboratorio ou recurso didatico.",
        observacoesExemplo: "Ex.: separar notebook, testar audio, ligar computadores, configurar projetor."
    },
    {
        id: "suporte_tecnico",
        nome: "Suporte tecnico",
        descricaoExemplo: "Ajuste tecnico ou configuracao realizada para viabilizar a atividade.",
        observacoesExemplo: "Use para falhas de login, rede, equipamento ou configuracao."
    },
    {
        id: "atendimento_alunos",
        nome: "Atendimento a alunos",
        descricaoExemplo: "Apoio direto aos estudantes durante atividade pedagogica ou tecnologica.",
        observacoesExemplo: "Descreva como a turma foi orientada ou acompanhada."
    },
    {
        id: "producao_material",
        nome: "Producao de material",
        descricaoExemplo: "Montagem, adaptacao ou producao de material pedagogico e tecnologico.",
        observacoesExemplo: "Ex.: roteiro, formulario, apresentacao, atividade ou suporte visual."
    },
    {
        id: "articulacao",
        nome: "Articulacao",
        descricaoExemplo: "Articulacao com docentes, setores ou equipe gestora para encaminhamentos do turno.",
        observacoesExemplo: "Use para combinados, distribuicao de demandas e acompanhamento institucional."
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
    }
];

const ACOES_REALIZADAS_PCPI = [
    "Ligou os computadores",
    "Organizou os equipamentos",
    "Configurou projetor ou audio",
    "Preparou laboratorio ou STE",
    "Orientou o professor",
    "Acompanhou o desenvolvimento da aula",
    "Apoiou os alunos durante a atividade",
    "Montou atividade ou projeto",
    "Registrou evidencias ou encaminhamentos",
    "Resolveu demanda tecnica",
    "Outro"
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
    return tipo ? tipo.nome : "Acao complementar";
}

function obterConfigTipoAcao(tipoAcao) {
    return TIPOS_ACAO_PCPI.find((item) => item.id === String(tipoAcao || "").trim()) || null;
}

function categoriaUsoLabel(categoria) {
    const chave = String(categoria || "").trim();
    return CATEGORIAS_AUTOMATICAS[chave] || "Agendamento automatico";
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

    const turnosPcpi = turnos.filter((turno) => TURNOS_PCPI_PERMITIDOS.has(normalizarTurnoId(turno.id)));
    const opcoesTurno = turnosPcpi.length > 0 ? turnosPcpi : TURNOS_FALLBACK;

    opcoesTurno.forEach((turno) => {
        const option = document.createElement("option");
        option.value = turno.id;
        option.textContent = turno.nome;
        select.appendChild(option);
    });

    const turnoPadrao = opcoesTurno.find((turno) => normalizarTurnoId(turno.id) === "MATUTINO");
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

function obterItensRegistros() {
    return Array.isArray(registrosManuaisAtuais?.itens) ? registrosManuaisAtuais.itens : [];
}

function obterRegistrosManuaisLivres() {
    return obterItensRegistros().filter((item) => !Number(item.agendamento_id || 0));
}

function obterRegistrosVinculadosAgendamento(agendamentoId) {
    return obterItensRegistros().filter((item) => Number(item.agendamento_id || 0) === Number(agendamentoId || 0));
}

function resumoRegistro(item) {
    const partes = [];
    const acao = String(item.acao_realizada || "").trim();
    const resultado = String(item.resultado || "").trim();
    if (acao) {
        partes.push(acao);
    }
    if (resultado) {
        partes.push(resultado);
    }
    return partes.join(" | ");
}

function opcoesTipoAcaoHtml(selectedValue) {
    return TIPOS_ACAO_PCPI.map((tipo) => (
        `<option value="${escaparHtml(tipo.id)}"${tipo.id === selectedValue ? " selected" : ""}>${escaparHtml(tipo.nome)}</option>`
    )).join("");
}

function opcoesAcaoRealizadaHtml() {
    const options = [`<option value="">Selecione a acao realizada</option>`];
    ACOES_REALIZADAS_PCPI.forEach((acao) => {
        options.push(`<option value="${escaparHtml(acao)}">${escaparHtml(acao)}</option>`);
    });
    return options.join("");
}

function formularioExecucaoAgendamentoHtml(item) {
    return `
        <form class="pcpi-linked-form" data-agendamento-id="${Number(item.agendamento_id || 0)}">
            <div class="pcpi-linked-grid">
                <label class="pcpi-field field">
                    <span class="field-label">Tipo</span>
                    <select name="tipo_acao">${opcoesTipoAcaoHtml("suporte_aula")}</select>
                </label>
                <label class="pcpi-field field">
                    <span class="field-label">Acao realizada</span>
                    <select name="acao_realizada">${opcoesAcaoRealizadaHtml()}</select>
                </label>
                <label class="pcpi-field field pcpi-field-wide field--wide">
                    <span class="field-label">Descricao curta</span>
                    <input name="descricao_curta" type="text" maxlength="500" placeholder="Ex.: suporte ao uso de recursos digitais na aula" required>
                </label>
                <label class="pcpi-field field pcpi-field-wide field--wide">
                    <span class="field-label">Resultado</span>
                    <input name="resultado" type="text" maxlength="400" placeholder="Ex.: aula iniciou com os equipamentos prontos">
                </label>
                <label class="pcpi-field field pcpi-field-wide field--wide">
                    <span class="field-label">Observacoes</span>
                    <textarea name="observacoes" rows="2" maxlength="2000" placeholder="Detalhes complementares do atendimento"></textarea>
                </label>
            </div>
            <div class="pcpi-inline-actions">
                <button class="btn-destaque" type="submit">Salvar execucao</button>
            </div>
        </form>
    `;
}

function renderizarRegistrosVinculados(agendamentoId) {
    const itens = obterRegistrosVinculadosAgendamento(agendamentoId);
    if (itens.length === 0) {
        return `<p class="pcpi-item-note is-secondary">Nenhuma execucao registrada para este agendamento.</p>`;
    }

    return `
        <div class="pcpi-linked-history">
            ${itens.map((item) => {
                const resumo = resumoRegistro(item);
                const observacoes = String(item.observacoes || "").trim();
                return `
                    <div class="pcpi-linked-history-item">
                        <strong>${escaparHtml(tipoAcaoLabel(item.tipo_acao))}</strong>
                        <p class="pcpi-item-line">${escaparHtml(item.descricao_curta || "")}</p>
                        ${resumo ? `<p class="pcpi-item-note">${escaparHtml(resumo)}</p>` : ""}
                        ${observacoes ? `<p class="pcpi-item-note is-secondary">${escaparHtml(observacoes)}</p>` : ""}
                    </div>
                `;
            }).join("")}
        </div>
    `;
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
        const totalExecucoes = obterRegistrosVinculadosAgendamento(item.agendamento_id).length;

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
                                <span class="pcpi-chip">${totalExecucoes} execucao(oes)</span>
                            </div>
                        </div>
                        <p class="pcpi-item-line">${escaparHtml(professor)} | ${escaparHtml(componentes)}</p>
                        <p class="pcpi-item-line">${escaparHtml(turma)} | ${escaparHtml(aulaFormatada(item.aula))}</p>
                        ${tema ? `<p class="pcpi-item-note">${escaparHtml(tema)}</p>` : ""}
                        ${observacao ? `<p class="pcpi-item-note is-secondary">${escaparHtml(observacao)}</p>` : ""}
                    </div>
                </label>
                <div class="pcpi-linked-shell">
                    <div class="pcpi-subsection-header">
                        <h3>Execucao do PCPI neste atendimento</h3>
                    </div>
                    ${formularioExecucaoAgendamentoHtml(item)}
                    ${renderizarRegistrosVinculados(item.agendamento_id)}
                </div>
            </li>
        `;
    }).join("");

    lista.querySelectorAll(".pcpi-agendamento-checkbox").forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
            atualizarResumoAutomatico();
            atualizarResumoTexto();
        });
    });

    lista.querySelectorAll(".pcpi-linked-form").forEach((form) => {
        form.addEventListener("submit", salvarExecucaoAgendamentoPcpi);
    });

    atualizarResumoAutomatico();
    atualizarResumoTexto();
}

function renderizarRegistrosManuais() {
    const lista = el("listaRegistrosManuaisPcpi");
    const itens = obterRegistrosManuaisLivres();

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
        const resumo = resumoRegistro(item);
        const detalhes = [professor, componente, turma].filter(Boolean).join(" | ");

        return `
            <li class="pcpi-item pcpi-item-manual">
                <div class="pcpi-item-body pcpi-item-panel">
                    <div class="pcpi-item-top">
                        <strong>${escaparHtml(tipoAcaoLabel(item.tipo_acao))}</strong>
                        <div class="pcpi-tag-group">
                            <span class="pcpi-chip pcpi-chip-manual">Manual</span>
                        </div>
                    </div>
                    <p class="pcpi-item-line">${escaparHtml(item.descricao_curta || "")}</p>
                    ${detalhes ? `<p class="pcpi-item-note">${escaparHtml(detalhes)}</p>` : ""}
                    ${resumo ? `<p class="pcpi-item-note">${escaparHtml(resumo)}</p>` : ""}
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
    const totalManuais = Number(registrosManuaisAtuais?.total_registros_manuais || 0);
    const totalVinculados = Number(registrosManuaisAtuais?.total_registros_vinculados || 0);

    if (!filtros.data || !filtros.turno) {
        el("pcpiResumoTurno").textContent = "";
        return;
    }

    el("pcpiResumoTurno").textContent = `${nomeTurno(filtros.turno)} de ${paraDataBr(filtros.data)} com ${totalAutomaticos} agendamento(s), ${totalVinculados} execucao(oes) vinculada(s) e ${totalManuais} registro(s) manual(is).`;
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
    const totalRegistros = Number(registrosManuaisAtuais?.total_registros || 0);
    el("pcpiResumoTexto").textContent = `Texto baseado em ${selecionados} agendamento(s) selecionado(s) e ${totalRegistros} registro(s) complementar(es).`;
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
    el("pcpiAcaoRealizada").value = "";
    el("pcpiResultado").value = "";
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
            throw new Error(await obterMensagemErroResposta(resRegistros, "Nao foi possivel carregar os registros do PCPI."));
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
        el("listaRegistrosManuaisPcpi").innerHTML = criarEstadoVazio("Nao foi possivel carregar os registros.");
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

async function baixarPdfPcpi() {
    limparMensagem("msgPcpiGeral");
    let filtros;
    try {
        filtros = validarFiltrosSelecionados();
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Selecione data e turno.", true);
        return;
    }

    try {
        const resposta = await fetchComAuth("/pcpi/texto/pdf", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                data: filtros.data,
                turno: filtros.turno,
                agendamento_ids: obterAgendamentoIdsSelecionados()
            })
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel gerar o PDF do PCPI."));
        }

        const blob = await resposta.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `pcpi-${filtros.data}-${String(filtros.turno || "").toLowerCase()}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
        definirMensagem("msgPcpiGeral", "PDF gerado com sucesso.");
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Falha ao gerar o PDF do PCPI.", true);
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
        acao_realizada: String(el("pcpiAcaoRealizada").value || "").trim(),
        professor_nome: String(el("pcpiProfessorNome").value || "").trim(),
        componente: String(el("pcpiComponente").value || "").trim(),
        turma: String(el("pcpiTurma").value || "").trim(),
        descricao_curta: descricaoCurta,
        resultado: String(el("pcpiResultado").value || "").trim(),
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

function obterAgendamentoAtual(agendamentoId) {
    const itens = Array.isArray(sugestoesAtuais?.itens) ? sugestoesAtuais.itens : [];
    return itens.find((item) => Number(item.agendamento_id || 0) === Number(agendamentoId || 0)) || null;
}

async function salvarExecucaoAgendamentoPcpi(event) {
    event.preventDefault();
    limparMensagem("msgPcpiGeral");

    let filtros;
    try {
        filtros = validarFiltrosSelecionados();
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Selecione data e turno antes de salvar.", true);
        return;
    }

    const form = event.currentTarget;
    const agendamentoId = Number(form.dataset.agendamentoId || 0);
    const item = obterAgendamentoAtual(agendamentoId);
    if (!item) {
        definirMensagem("msgPcpiGeral", "Agendamento nao encontrado para registrar a execucao.", true);
        return;
    }

    const formData = new FormData(form);
    const descricaoCurta = String(formData.get("descricao_curta") || "").trim();
    const acaoRealizada = String(formData.get("acao_realizada") || "").trim();
    if (!descricaoCurta || !acaoRealizada) {
        definirMensagem("msgPcpiGeral", "Informe a acao realizada e a descricao curta da execucao.", true);
        return;
    }

    const payload = {
        data: filtros.data,
        turno: filtros.turno,
        agendamento_id: agendamentoId,
        tipo_acao: String(formData.get("tipo_acao") || "suporte_aula").trim(),
        acao_realizada: acaoRealizada,
        professor_nome: String(item.professor_nome || "").trim(),
        componente: String(item.recurso_nome || "").trim(),
        turma: String(item.turma || "").trim(),
        descricao_curta: descricaoCurta,
        resultado: String(formData.get("resultado") || "").trim(),
        observacoes: String(formData.get("observacoes") || "").trim()
    };

    try {
        const resposta = await fetchComAuth("/pcpi/registros-manuais", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify(payload)
        });

        if (!resposta.ok) {
            throw new Error(await obterMensagemErroResposta(resposta, "Nao foi possivel salvar a execucao do agendamento."));
        }

        definirMensagem("msgPcpiGeral", "Execucao do agendamento salva com sucesso.");
        await carregarContextoPcpi({ gerarTextoAutomaticamente: true });
    } catch (erro) {
        definirMensagem("msgPcpiGeral", erro.message || "Erro ao salvar a execucao do agendamento.", true);
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

    el("btnBaixarPdfPcpi").addEventListener("click", async () => {
        await baixarPdfPcpi();
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
