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
let calendarioApc = { periodos: [] };
let periodoSelecionadoApcId = null;
let abaGestaoApc = "professores";
let envioPreviewApcId = null;
let arquivoPreviewUrlApc = "";
let arquivoPreviewNomeApc = "";

function setMensagemApc(texto, erro = false) {
    const msg = el("msgApc");
    if (!msg) return;
    msg.innerText = texto || "";
    msg.style.color = erro ? "#ffe2e2" : "#d9f99d";
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
    if (usuarioApc?.pode_gerir) {
        const totalSolicitacoes = periodos.length;
        const totalPendencias = periodos.reduce(
            (soma, item) => soma + Number(item.total_pendentes || 0),
            0
        );
        el("apcResumoMes").innerText =
            `${pluralizarApc(totalSolicitacoes, "solicitacao", "solicitacoes")} neste mes | `
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
    const podeGerir = Boolean(usuarioApc?.pode_gerir);
    const ehProfessor = Boolean(usuarioApc?.eh_professor);
    const layoutProfessor = ehProfessor && !podeGerir;
    const pagina = obterPaginaApc();

    el("apcGestaoCard").hidden = !podeGerir;
    el("apcResumoPainel").hidden = !podeGerir;
    el("apcGestaoTabs").hidden = !podeGerir;
    if (!podeGerir) {
        document.querySelectorAll("[data-apc-gestao-tab-panel]").forEach((painel) => {
            painel.hidden = true;
        });
    } else {
        ativarAbaGestaoApc(abaGestaoApc);
    }
    el("apcUsuario").innerText = usuarioApc
        ? `${usuarioApc.nome} (${usuarioApc.cargo})`
        : "";

    if (!pagina) return;
    pagina.classList.toggle("is-manager", podeGerir);
    pagina.classList.toggle("is-professor", layoutProfessor);
}

function preencherFormularioPeriodo(periodo) {
    el("apcDataReferencia").value = periodo?.data_referencia || dataSelecionadaApc;
    el("apcPrazoEnvio").value = periodo?.prazo_envio_input || `${dataSelecionadaApc}T23:59`;
    el("apcTitulo").value = periodo?.titulo || "Documento";
    el("apcObservacao").value = periodo?.observacao || "";
    el("apcPublicoAlvo").value = periodo?.publico_alvo || "TODOS_PROFESSORES";
    el("btnExcluirApc").hidden = !Boolean(periodo?.id);
}

function renderResumoPainelCards(itens) {
    const wrap = document.createElement("div");
    wrap.className = "apc-resumo-grid";
    itens.forEach((item) => {
        const card = document.createElement("div");
        card.className = "apc-resumo-item";
        card.innerHTML = `<span>${item.label}</span><strong>${item.valor}</strong>`;
        wrap.appendChild(card);
    });
    return wrap;
}

function criarStatusApc(texto, tipo = "pending") {
    const span = document.createElement("span");
    span.className = `apc-status ${tipo === "ok" ? "is-ok" : tipo === "closed" ? "is-closed" : "is-pending"}`;
    span.innerText = texto;
    return span;
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

function ativarAbaGestaoApc(aba) {
    abaGestaoApc = aba || "professores";
    document.querySelectorAll("[data-apc-gestao-tab-trigger]").forEach((botao) => {
        const ativa = botao.dataset.apcGestaoTabTrigger === abaGestaoApc;
        botao.classList.toggle("is-active", ativa);
        botao.setAttribute("aria-selected", ativa ? "true" : "false");
    });
    document.querySelectorAll("[data-apc-gestao-tab-panel]").forEach((painel) => {
        const ativo = painel.dataset.apcGestaoTabPanel === abaGestaoApc;
        painel.hidden = !ativo;
        painel.classList.toggle("is-active", ativo);
    });
}

function revogarPreviewArquivoApc() {
    if (arquivoPreviewUrlApc) {
        window.URL.revokeObjectURL(arquivoPreviewUrlApc);
        arquivoPreviewUrlApc = "";
    }
    arquivoPreviewNomeApc = "";
}

function limparPreviewArquivoApc(mensagem = "Selecione um arquivo enviado para visualizar aqui.") {
    revogarPreviewArquivoApc();
    envioPreviewApcId = null;
    el("apcArquivoPreviewMeta").innerHTML = `<div class="booking-empty">${mensagem}</div>`;
    el("apcArquivoPreviewState").innerHTML =
        '<div class="booking-empty">A visualizacao do arquivo sera carregada neste painel.</div>';
    el("apcArquivoPreviewState").hidden = false;
    el("apcArquivoPreviewFrame").hidden = true;
    el("apcArquivoPreviewFrame").removeAttribute("src");
    el("apcArquivoPreviewImage").hidden = true;
    el("apcArquivoPreviewImage").removeAttribute("src");
    el("apcArquivoPreviewText").hidden = true;
    el("apcArquivoPreviewText").textContent = "";
    el("btnApcAbrirArquivoGuia").hidden = true;
    el("btnApcBaixarArquivo").hidden = true;
}

function tipoPreviewArquivoApc(envio) {
    const tipo = String(envio?.arquivo_tipo || "").toLowerCase();
    const nome = String(envio?.arquivo_nome_original || "").toLowerCase();
    if (tipo.startsWith("image/")) return "image";
    if (tipo.includes("pdf") || nome.endsWith(".pdf")) return "frame";
    if (tipo.includes("json") || nome.endsWith(".json") || tipo.startsWith("text/")) return "text";
    return "download";
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
                turmas: [],
                disciplinas: [],
                entregas: [],
            });
        }
        const grupo = grupos.get(professorId);
        grupo.total_entregas += 1;
        grupo.total_enviadas += item.enviado ? 1 : 0;
        grupo.total_pendentes += item.enviado ? 0 : 1;
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
        if (Number(item.total_elegiveis || 0) > 0 && Number(item.total_pendentes || 0) === 0) {
            return { texto: "Concluido", tipo: "ok" };
        }
        if (item.prazo_expirado) {
            return { texto: "Prazo encerrado", tipo: "closed" };
        }
        return { texto: "Aguardando envios", tipo: "pending" };
    }
    if (item.enviado) {
        return { texto: "Enviado", tipo: "ok" };
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

function criarCardEnvioExistenteApc(envio) {
    const envioCard = document.createElement("div");
    envioCard.className = "apc-professor-card";
    envioCard.appendChild(criarStatusApc("Arquivo enviado", "ok"));

    const enviadoEm = document.createElement("p");
    enviadoEm.className = "apc-envio-meta";
    enviadoEm.innerText = `Enviado em ${formatarDataHoraApc(envio.enviado_em)}`;
    envioCard.appendChild(enviadoEm);

    const link = document.createElement("a");
    link.className = "apc-envio-link";
    link.href = `/apc/envios/${envio.id}/arquivo`;
    link.target = "_blank";
    link.rel = "noopener";
    link.innerText = envio.arquivo_nome_original;
    envioCard.appendChild(link);

    return envioCard;
}

function criarCardEntregaProfessorApc(periodo, item) {
    const card = document.createElement("article");
    card.className = "apc-professor-card";

    const topo = document.createElement("div");
    topo.className = "apc-professor-topo";
    const titulo = item.disciplina_nome
        ? `${item.disciplina_nome}${item.turma_nome ? ` - ${item.turma_nome}` : ""}`
        : "Entrega geral";
    topo.innerHTML = `<div><h4>${titulo}</h4><p>${item.total_aulas || 0} aula(s) vinculada(s)</p></div>`;
    topo.appendChild(item.enviado ? criarStatusApc("Enviado", "ok") : criarStatusApc("Pendente"));
    card.appendChild(topo);

    if ((item.turmas || []).length) {
        const chips = document.createElement("div");
        chips.className = "apc-chip-row";
        (item.turmas || []).forEach((turma) => {
            chips.appendChild(criarChipApc(turma));
        });
        if (item.disciplina_nome) {
            chips.appendChild(criarChipApc(item.disciplina_nome));
        }
        card.appendChild(chips);
    }

    if ((item.horarios || []).length) {
        const horarios = document.createElement("ul");
        horarios.className = "apc-horarios-lista";
        (item.horarios || []).forEach((horario) => {
            const li = document.createElement("li");
            li.innerText = `${horario.aula_numero}a aula - ${horario.turma_nome} - ${horario.disciplina_nome}`;
            horarios.appendChild(li);
        });
        card.appendChild(horarios);
    } else {
        const livre = document.createElement("p");
        livre.className = "apc-inline-hint";
        livre.innerText = "Esta entrega foi liberada para todos os professores.";
        card.appendChild(livre);
    }

    if (item.envio?.id) {
        card.appendChild(criarCardEnvioExistenteApc(item.envio));
    }

    if (periodo.prazo_expirado) {
        card.appendChild(criarStatusApc("Prazo encerrado", "closed"));
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
        ? "Se necessario, envie um novo arquivo para substituir o anexo anterior desta disciplina."
        : "Anexe o arquivo correspondente a esta disciplina.";
    form.appendChild(dica);

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "btn-destaque";
    submit.innerText = item.envio?.id ? "Atualizar arquivo" : "Enviar arquivo";
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
        vazio.innerText = "Nenhuma disciplina vinculada a esta solicitacao para o seu horario.";
        body.appendChild(vazio);
        return body;
    }

    detalhe.itens.forEach((item) => {
        body.appendChild(criarCardEntregaProfessorApc(periodo, item));
    });

    return body;
}

function renderSolicitacoesData(periodos, detalheSelecionado = null) {
    const wrap = el("apcSolicitacoesData");
    wrap.innerHTML = "";

    if (!Array.isArray(periodos) || !periodos.length) {
        wrap.innerHTML = '<div class="booking-empty">Nenhuma solicitacao cadastrada para esta data.</div>';
        return;
    }

    const modoGestao = Boolean(usuarioApc?.pode_gerir);

    periodos.forEach((periodo) => {
        const selecionado = Number(periodo.id) === Number(periodoSelecionadoApcId);
        const detalheAtual = selecionado ? detalheSelecionado : null;
        const item = document.createElement("details");
        item.className = "apc-solicitacao-item";
        item.open = selecionado;
        if (selecionado) {
            item.classList.add("is-selected");
        }

        const summary = document.createElement("summary");
        summary.className = "apc-solicitacao-summary";

        const summaryMain = document.createElement("div");
        summaryMain.className = "apc-solicitacao-summary-main";
        const titulo = document.createElement("h4");
        titulo.innerText = periodo.titulo || "Documento";
        summaryMain.appendChild(titulo);

        const resumo = document.createElement("p");
        resumo.className = "apc-solicitacao-resumo";
        resumo.innerText = modoGestao
            ? `${periodo.total_enviados || 0}/${periodo.total_elegiveis || 0} enviados`
            : periodo.enviado
                ? "Todos os arquivos enviados"
                : `${periodo.total_pendentes || periodo.total_entregas || 0} pendencia(s) de envio`;
        summaryMain.appendChild(resumo);

        const meta = document.createElement("div");
        meta.className = "apc-solicitacao-summary-meta";
        meta.appendChild(criarMetaApc(periodo.publico_alvo_label || ""));
        meta.appendChild(criarMetaApc(`Prazo: ${formatarDataHoraApc(periodo.prazo_envio)}`));
        summaryMain.appendChild(meta);
        summary.appendChild(summaryMain);

        const summarySide = document.createElement("div");
        summarySide.className = "apc-solicitacao-summary-side";
        const status = statusResumoPeriodoApc(periodo, modoGestao);
        summarySide.appendChild(criarStatusApc(status.texto, status.tipo));

        const chevron = document.createElement("span");
        chevron.className = "apc-solicitacao-chevron";
        chevron.innerText = "v";
        summarySide.appendChild(chevron);
        summary.appendChild(summarySide);

        summary.addEventListener("click", async (event) => {
            event.preventDefault();
            periodoSelecionadoApcId = Number(periodo.id);
            await carregarDetalheSelecionadoApc();
        });

        item.appendChild(summary);
        item.appendChild(
            modoGestao
                ? criarCorpoResumoGestaoApc(periodo, detalheAtual)
                : criarCorpoProfessorPeriodoApc(detalheAtual)
        );
        wrap.appendChild(item);
    });
}

function renderListaGestaoApc(detalhe) {
    const lista = el("apcListaPainel");
    lista.innerHTML = "";

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
        details.open = true;

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
        side.appendChild(
            grupo.total_pendentes === 0
                ? criarStatusApc("Concluido", "ok")
                : criarStatusApc("Pendente")
        );
        const chevron = document.createElement("span");
        chevron.className = "apc-solicitacao-chevron";
        chevron.innerText = "v";
        side.appendChild(chevron);
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
            topo.innerHTML = `<div><h5>${titulo}</h5><p>${item.total_aulas || 0} aula(s) vinculada(s)</p></div>`;
            topo.appendChild(item.enviado ? criarStatusApc("Enviado", "ok") : criarStatusApc("Pendente"));
            card.appendChild(topo);

            const contexto = document.createElement("p");
            contexto.className = "apc-inline-hint";
            contexto.innerText = (item.horarios || []).length
                ? "Entrega vinculada a disciplina do horario escolar."
                : "Entrega liberada para este professor sem dependencia do horario escolar.";
            card.appendChild(contexto);

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

async function carregarPreviewArquivoApc(envio) {
    if (!envio?.id) {
        limparPreviewArquivoApc();
        return;
    }

    revogarPreviewArquivoApc();
    envioPreviewApcId = Number(envio.id);
    arquivoPreviewNomeApc = String(envio.arquivo_nome_original || "arquivo");
    preencherMetaPreviewArquivoApc(envio);
    el("apcArquivoPreviewState").hidden = false;
    el("apcArquivoPreviewState").innerHTML = '<div class="booking-empty">Carregando arquivo...</div>';
    el("apcArquivoPreviewFrame").hidden = true;
    el("apcArquivoPreviewImage").hidden = true;
    el("apcArquivoPreviewText").hidden = true;
    el("btnApcAbrirArquivoGuia").hidden = true;
    el("btnApcBaixarArquivo").hidden = true;

    try {
        const resposta = await fetchResposta(`/apc/envios/${envio.id}/arquivo`, {
            headers: headersApc,
        });
        const blob = await resposta.blob();
        arquivoPreviewUrlApc = window.URL.createObjectURL(blob);

        const tipoPreview = tipoPreviewArquivoApc(envio);
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
        } else if (tipoPreview === "frame") {
            const frame = el("apcArquivoPreviewFrame");
            frame.src = arquivoPreviewUrlApc;
            frame.hidden = false;
        } else {
            el("apcArquivoPreviewState").hidden = false;
            el("apcArquivoPreviewState").innerHTML =
                '<div class="booking-empty">Pre-visualizacao indisponivel para este formato. Use os botoes abaixo para abrir ou baixar o arquivo.</div>';
        }

        el("btnApcAbrirArquivoGuia").hidden = false;
        el("btnApcBaixarArquivo").hidden = false;
    } catch (err) {
        limparPreviewArquivoApc(err.message || "Nao foi possivel carregar o arquivo.");
    }
}

function renderArquivosGestaoApc(detalhe) {
    const lista = el("apcArquivosLista");
    lista.innerHTML = "";

    if (!detalhe || !Array.isArray(detalhe.itens) || detalhe.itens.length === 0) {
        lista.innerHTML = '<div class="booking-empty">Nenhum professor elegivel para esta solicitacao.</div>';
        limparPreviewArquivoApc();
        return;
    }

    const grupos = agruparItensGestaoPorProfessor(detalhe.itens);
    const enviosDisponiveis = detalhe.itens
        .filter((item) => item.envio?.id)
        .map((item) => item.envio);
    const envioPreviewAnterior = Number(envioPreviewApcId || 0);
    const envioSelecionado = enviosDisponiveis.find(
        (envio) => Number(envio.id) === Number(envioPreviewApcId)
    ) || enviosDisponiveis[0] || null;
    envioPreviewApcId = Number(envioSelecionado?.id || 0) || null;

    grupos.forEach((grupo) => {
        const bloco = document.createElement("article");
        bloco.className = "apc-arquivos-grupo";

        const header = document.createElement("div");
        header.className = "apc-arquivos-grupo-header";
        header.innerHTML = `
            <h4>${grupo.professor_nome}</h4>
            <p>${grupo.total_enviadas}/${grupo.total_entregas} arquivos enviados</p>
        `;
        bloco.appendChild(header);

        const itens = document.createElement("div");
        itens.className = "apc-arquivos-itens";

        grupo.entregas.filter((item) => item.envio?.id).forEach((item) => {
            const envio = item.envio;
            const botao = document.createElement("button");
            botao.type = "button";
            botao.className = "apc-arquivo-item-btn";
            botao.classList.toggle("is-active", Number(envio.id) === Number(envioPreviewApcId));
            botao.innerHTML = `
                <strong>${envio.disciplina_nome || item.disciplina_nome || "Entrega geral"}${envio.turma_nome ? ` - ${envio.turma_nome}` : ""}</strong>
                <span>${envio.arquivo_nome_original}</span>
                <small>Enviado em ${formatarDataHoraApc(envio.enviado_em)}</small>
            `;
            botao.addEventListener("click", async () => {
                await carregarPreviewArquivoApc(envio);
                renderArquivosGestaoApc(detalhe);
            });
            itens.appendChild(botao);
        });

        if (!itens.childNodes.length) {
            const vazio = document.createElement("div");
            vazio.className = "booking-empty";
            vazio.innerText = "Nenhum arquivo enviado por este professor ainda.";
            itens.appendChild(vazio);
        }

        bloco.appendChild(itens);
        lista.appendChild(bloco);
    });

    if (!enviosDisponiveis.length) {
        limparPreviewArquivoApc("Nenhum arquivo enviado ainda.");
        return;
    }

    if (Number(envioSelecionado?.id || 0) !== envioPreviewAnterior) {
        void carregarPreviewArquivoApc(envioSelecionado);
        return;
    }

    if (!arquivoPreviewUrlApc) {
        void carregarPreviewArquivoApc(envioSelecionado);
    }
}

function renderPainelSelecionadoVazio() {
    const modoGestao = Boolean(usuarioApc?.pode_gerir);
    el("apcTituloPainel").innerText = modoGestao
        ? `Solicitacoes de ${paraDataBr(dataSelecionadaApc)}`
        : `Pendencias de ${paraDataBr(dataSelecionadaApc)}`;
    el("apcSubtituloPainel").innerText = modoGestao
        ? "Cadastre uma nova solicitacao ao lado ou selecione outra data no calendario."
        : "Nao ha entregas disponiveis para voce nesta data.";
    renderSolicitacoesData([]);
    el("apcResumoPainel").innerHTML = "";
    if (modoGestao) {
        el("apcGestaoTabs").hidden = true;
        ativarAbaGestaoApc("professores");
        limparPreviewArquivoApc();
    }
    el("apcListaPainel").innerHTML = modoGestao
        ? '<div class="booking-empty">Cadastre uma solicitacao ao lado para comecar a receber anexos dos professores.</div>'
        : "";
    if (el("apcArquivosLista")) {
        el("apcArquivosLista").innerHTML = '<div class="booking-empty">Nenhum arquivo enviado ainda.</div>';
    }
    preencherFormularioPeriodo(null);
}

function renderPainelSemSelecaoGestao() {
    el("apcTituloPainel").innerText = `Solicitacoes de ${paraDataBr(dataSelecionadaApc)}`;
    el("apcSubtituloPainel").innerText = "Selecione uma solicitacao existente ou cadastre uma nova ao lado.";
    el("apcResumoPainel").innerHTML = "";
    el("apcGestaoTabs").hidden = true;
    el("apcListaPainel").innerHTML =
        '<div class="booking-empty">Nenhuma solicitacao selecionada.</div>';
    if (el("apcArquivosLista")) {
        el("apcArquivosLista").innerHTML = '<div class="booking-empty">Nenhum arquivo enviado ainda.</div>';
    }
    limparPreviewArquivoApc();
    renderSolicitacoesData(periodosResumoPorData(dataSelecionadaApc));
}

async function carregarDetalheSelecionadoApc() {
    const periodosDoDia = periodosResumoPorData(dataSelecionadaApc);

    if (!periodosDoDia.length) {
        periodoSelecionadoApcId = null;
        renderPainelSelecionadoVazio();
        return;
    }

    const resumoSelecionado = periodoResumoSelecionado(periodosDoDia);
    periodoSelecionadoApcId = Number(resumoSelecionado?.id || 0);
    if (!periodoSelecionadoApcId) {
        renderPainelSelecionadoVazio();
        return;
    }

    const detalhe = await fetchJson(`/apc/periodos/${periodoSelecionadoApcId}`, {
        headers: headersApc,
    });
    const periodo = detalhe.periodo || detalhe;
    renderSolicitacoesData(periodosDoDia, detalhe);

    if (usuarioApc?.pode_gerir) {
        const gruposProfessor = agruparItensGestaoPorProfessor(detalhe.itens || []);
        el("apcTituloPainel").innerText = `${periodo.titulo} - ${paraDataBr(periodo.data_referencia)}`;
        el("apcSubtituloPainel").innerText =
            `${periodo.dia_semana_nome} | Prazo ate ${formatarDataHoraApc(periodo.prazo_envio)}`;
        el("apcResumoPainel").innerHTML = "";
        el("apcResumoPainel").appendChild(
            renderResumoPainelCards([
                { label: "Professores", valor: String(gruposProfessor.length) },
                { label: "Entregas", valor: String(detalhe.total_elegiveis || 0) },
                { label: "Enviados", valor: String(detalhe.total_enviados || 0) },
                { label: "Pendentes", valor: String(detalhe.total_pendentes || 0) },
                { label: "Publico", valor: periodo.publico_alvo_label || "-" },
            ])
        );
        el("apcGestaoTabs").hidden = false;
        ativarAbaGestaoApc(abaGestaoApc);
        renderListaGestaoApc(detalhe);
        renderArquivosGestaoApc(detalhe);
        preencherFormularioPeriodo(periodo);
        return;
    }

    el("apcTituloPainel").innerText = `Pendencias de ${paraDataBr(periodo.data_referencia)}`;
    el("apcSubtituloPainel").innerText =
        "Abra a pendencia desejada abaixo para ver os detalhes e anexar o arquivo correto.";
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

        const btnDia = document.createElement("button");
        btnDia.type = "button";
        btnDia.className = "calendar-day apc-calendar-day";
        if (dataIso === dataSelecionadaApc) btnDia.classList.add("is-selected");
        if (dataIso === hojeIso) btnDia.classList.add("is-today");
        if (periodos.length) {
            btnDia.classList.add("has-apc");
            const todosConcluidos = usuarioApc?.pode_gerir
                ? periodos.every(
                    (item) => Number(item.total_elegiveis || 0) > 0 && Number(item.total_pendentes || 0) === 0
                )
                : periodos.every((item) => Boolean(item.enviado));
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
        } else if (usuarioApc?.pode_gerir) {
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

        btnDia.addEventListener("click", async () => {
            dataSelecionadaApc = dataIso;
            const periodosDaData = periodosResumoPorData(dataIso);
            const atualNaData = periodosDaData.find(
                (item) => Number(item.id) === Number(periodoSelecionadoApcId)
            );
            periodoSelecionadoApcId = atualNaData ? Number(atualNaData.id) : Number(periodosDaData[0]?.id || 0);
            renderCalendarioApc();
            await carregarDetalheSelecionadoApc();
        });

        grid.appendChild(btnDia);
    }
}

async function carregarCalendarioApc() {
    const mes = mesIsoApc(mesAtualApc);
    const anoLetivo = el("apcAnoLetivo").value;
    calendarioApc = await fetchJson(`/apc/calendario?mes=${mes}&ano_letivo=${anoLetivo}`, {
        headers: headersApc,
    });
    atualizarResumoMesApc();
    renderCalendarioApc();
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
    };

    try {
        let salvo;
        if (periodoSelecionadoApcId) {
            salvo = await fetchJson(`/apc/periodos/${periodoSelecionadoApcId}`, {
                method: "PUT",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
            });
            setMensagemApc("Solicitacao atualizada com sucesso.");
        } else {
            salvo = await fetchJson("/apc/periodos", {
                method: "POST",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
            });
            setMensagemApc("Solicitacao cadastrada com sucesso.");
        }
        dataSelecionadaApc = payload.data_referencia;
        periodoSelecionadoApcId = Number(salvo?.id || 0) || null;
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "Nao foi possivel salvar a solicitacao.", true);
    }
}

async function excluirPeriodoApc() {
    if (!periodoSelecionadoApcId) return;
    if (!window.confirm("Deseja realmente excluir esta solicitacao de entrega?")) return;

    try {
        await fetchJson(`/apc/periodos/${periodoSelecionadoApcId}`, {
            method: "DELETE",
            headers: headersApc,
        });
        setMensagemApc("Solicitacao removida com sucesso.");
        periodoSelecionadoApcId = null;
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "Nao foi possivel excluir a solicitacao.", true);
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
        setMensagemApc("Selecione um arquivo para enviar nesta pendencia.", true);
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
        setMensagemApc(err.message || "Nao foi possivel enviar o arquivo.", true);
    }
}

function registrarEventosApc() {
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });
    document.querySelectorAll("[data-apc-gestao-tab-trigger]").forEach((botao) => {
        botao.addEventListener("click", () => {
            ativarAbaGestaoApc(botao.dataset.apcGestaoTabTrigger || "professores");
        });
    });

    el("btnApcAbrirArquivoGuia")?.addEventListener("click", () => {
        if (arquivoPreviewUrlApc) {
            window.open(arquivoPreviewUrlApc, "_blank", "noopener");
        }
    });
    el("btnApcBaixarArquivo")?.addEventListener("click", () => {
        if (!arquivoPreviewUrlApc) return;
        const link = document.createElement("a");
        link.href = arquivoPreviewUrlApc;
        link.download = arquivoPreviewNomeApc || "arquivo";
        document.body.appendChild(link);
        link.click();
        link.remove();
    });

    el("apcAnoLetivo").addEventListener("change", async () => {
        periodoSelecionadoApcId = null;
        await carregarCalendarioApc();
    });

    el("btnApcMesAnterior").addEventListener("click", async () => {
        mesAtualApc = new Date(mesAtualApc.getFullYear(), mesAtualApc.getMonth() - 1, 1);
        periodoSelecionadoApcId = null;
        await carregarCalendarioApc();
    });
    el("btnApcMesProximo").addEventListener("click", async () => {
        mesAtualApc = new Date(mesAtualApc.getFullYear(), mesAtualApc.getMonth() + 1, 1);
        periodoSelecionadoApcId = null;
        await carregarCalendarioApc();
    });
    el("btnApcMesHoje").addEventListener("click", async () => {
        const hoje = new Date();
        mesAtualApc = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        dataSelecionadaApc = paraIso(hoje);
        periodoSelecionadoApcId = null;
        await carregarCalendarioApc();
    });

    el("formApcPeriodo")?.addEventListener("submit", salvarPeriodoApc);
    el("btnNovaApc")?.addEventListener("click", () => {
        periodoSelecionadoApcId = null;
        preencherFormularioPeriodo(null);
        setMensagemApc("");
        renderPainelSemSelecaoGestao();
    });
    el("btnExcluirApc")?.addEventListener("click", excluirPeriodoApc);
}

async function initApc() {
    try {
        const usuarioMe = await fetchJson("/me", { headers: headersApc });
        contextoApc = await fetchJson("/apc/contexto", { headers: headersApc });
        usuarioApc = Object.assign({}, usuarioMe || {}, contextoApc?.usuario || {});
        preencherSelectAnosApc();
        preencherSelectPublicoApc();
        aplicarVisibilidadeApc();
        registrarEventosApc();
        await carregarCalendarioApc();
    } catch (_err) {
        encerrarSessao();
    }
}

window.addEventListener("beforeunload", revogarPreviewArquivoApc);
window.addEventListener("DOMContentLoaded", initApc);
