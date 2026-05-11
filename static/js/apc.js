const { el } = window.AppDom;
const {
    garantirToken,
    criarHeadersAuth,
    criarHeadersJsonAuth,
    encerrarSessao,
} = window.AppAuth;
const { fetchJson } = window.AppApi;
const { paraIso, paraDataBr } = window.AppFormat;

const tokenApc = garantirToken();
const headersApc = criarHeadersAuth(tokenApc);
const headersJsonApc = criarHeadersJsonAuth(tokenApc);

const nomesMesesApc = [
    "Janeiro", "Fevereiro", "MarÃ§o", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];
const nomesDiasSemanaApc = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "SÃ¡b"];

let usuarioApc = null;
let contextoApc = null;
let mesAtualApc = new Date();
let dataSelecionadaApc = paraIso(new Date());
let calendarioApc = { periodos: [] };
let periodoSelecionadoApc = null;

function setMensagemApc(texto, erro = false) {
    const msg = el("msgApc");
    if (!msg) return;
    msg.innerText = texto || "";
    msg.style.color = erro ? "#b42318" : "#0f766e";
}

function mesIsoApc(data) {
    return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}`;
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

function periodoResumoPorData(dataIso) {
    return (calendarioApc.periodos || []).find((item) => item.data_referencia === dataIso) || null;
}

function atualizarResumoMesApc() {
    const periodos = Array.isArray(calendarioApc.periodos) ? calendarioApc.periodos : [];
    if (usuarioApc?.pode_gerir) {
        const totalDatas = periodos.length;
        const totalPendencias = periodos.reduce(
            (soma, item) => soma + Number(item.total_pendentes || 0),
            0
        );
        el("apcResumoMes").innerText =
            `${totalDatas} data(s) de APC neste mÃªs | ${totalPendencias} pendÃªncia(s) no total.`;
        return;
    }

    const totalDatas = periodos.length;
    const enviados = periodos.filter((item) => Boolean(item.enviado)).length;
    el("apcResumoMes").innerText =
        `${totalDatas} APC(s) prevista(s) para vocÃª neste mÃªs | ${enviados} enviada(s).`;
}

function aplicarVisibilidadeApc() {
    el("apcGestaoCard").hidden = !Boolean(usuarioApc?.pode_gerir);
    el("apcProfessorCard").hidden = !Boolean(usuarioApc?.eh_professor) || Boolean(usuarioApc?.pode_gerir);
    el("apcUsuario").innerText = usuarioApc
        ? `${usuarioApc.nome} (${usuarioApc.cargo})`
        : "";
}

function preencherFormularioPeriodo(periodo) {
    el("apcDataReferencia").value = periodo?.data_referencia || dataSelecionadaApc;
    el("apcPrazoEnvio").value = periodo?.prazo_envio_input || `${dataSelecionadaApc}T23:59`;
    el("apcTitulo").value = periodo?.titulo || "APC";
    el("apcObservacao").value = periodo?.observacao || "";
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

function renderListaGestaoApc(detalhe) {
    const lista = el("apcListaPainel");
    lista.innerHTML = "";

    if (!detalhe || !Array.isArray(detalhe.itens) || detalhe.itens.length === 0) {
        lista.innerHTML = '<div class="booking-empty">Nenhum professor elegÃ­vel nesta data segundo o horÃ¡rio escolar.</div>';
        return;
    }

    detalhe.itens.forEach((item) => {
        const card = document.createElement("article");
        card.className = "apc-professor-card";

        const topo = document.createElement("div");
        topo.className = "apc-professor-topo";
        topo.innerHTML = `<div><h4>${item.professor_nome}</h4><p>${item.professor_email || "Sem e-mail"}</p></div>`;
        topo.appendChild(item.enviado ? criarStatusApc("Enviado", "ok") : criarStatusApc("Pendente"));
        card.appendChild(topo);

        const chips = document.createElement("div");
        chips.className = "apc-chip-row";
        (item.turmas || []).forEach((turma) => {
            const chip = document.createElement("span");
            chip.className = "apc-chip";
            chip.innerText = turma;
            chips.appendChild(chip);
        });
        card.appendChild(chips);

        const disciplinas = document.createElement("p");
        disciplinas.innerText = `Disciplinas: ${(item.disciplinas || []).join(", ") || "-"}`;
        card.appendChild(disciplinas);

        const horarios = document.createElement("ul");
        horarios.className = "apc-horarios-lista";
        (item.horarios || []).forEach((horario) => {
            const li = document.createElement("li");
            li.innerText = `${horario.aula_numero}Âª aula - ${horario.turma_nome} - ${horario.disciplina_nome}`;
            horarios.appendChild(li);
        });
        card.appendChild(horarios);

        if (item.envio?.id) {
            const link = document.createElement("a");
            link.className = "apc-envio-link";
            link.href = `/apc/envios/${item.envio.id}/arquivo`;
            link.target = "_blank";
            link.rel = "noopener";
            link.innerText = `Abrir arquivo: ${item.envio.arquivo_nome_original}`;
            card.appendChild(link);
        }

        lista.appendChild(card);
    });
}

function renderPainelProfessorApc(detalhe) {
    const resumo = el("apcProfessorResumo");
    const envioAtual = el("apcEnvioAtual");
    const form = el("formApcEnvio");

    resumo.innerHTML = "";
    envioAtual.innerHTML = "";

    if (!detalhe || !detalhe.periodo) {
        resumo.innerHTML = '<div class="booking-empty">Selecione uma data com APC prevista para vocÃª.</div>';
        form.hidden = true;
        return;
    }

    const periodo = detalhe.periodo;
    const bloco = document.createElement("div");
    bloco.className = "apc-professor-card";
    bloco.innerHTML = `
        <div class="apc-professor-topo">
            <div>
                <h4>${periodo.titulo}</h4>
                <p>${paraDataBr(periodo.data_referencia)} | Prazo atÃ© ${periodo.prazo_envio_input.replace("T", " ")}</p>
            </div>
        </div>
    `;

    const chips = document.createElement("div");
    chips.className = "apc-chip-row";
    (detalhe.turmas || []).forEach((turma) => {
        const chip = document.createElement("span");
        chip.className = "apc-chip";
        chip.innerText = turma;
        chips.appendChild(chip);
    });
    bloco.appendChild(chips);

    const disciplinas = document.createElement("p");
    disciplinas.innerText = `Disciplinas: ${(detalhe.disciplinas || []).join(", ") || "-"}`;
    bloco.appendChild(disciplinas);

    const horarios = document.createElement("ul");
    horarios.className = "apc-horarios-lista";
    (detalhe.horarios || []).forEach((horario) => {
        const li = document.createElement("li");
        li.innerText = `${horario.aula_numero}Âª aula - ${horario.turma_nome} - ${horario.disciplina_nome}`;
        horarios.appendChild(li);
    });
    bloco.appendChild(horarios);

    resumo.appendChild(bloco);

    if (detalhe.envio?.id) {
        const envioCard = document.createElement("div");
        envioCard.className = "apc-professor-card";
        envioCard.appendChild(criarStatusApc("Arquivo enviado", "ok"));
        const link = document.createElement("a");
        link.className = "apc-envio-link";
        link.href = `/apc/envios/${detalhe.envio.id}/arquivo`;
        link.target = "_blank";
        link.rel = "noopener";
        link.innerText = detalhe.envio.arquivo_nome_original;
        envioCard.appendChild(link);
        envioAtual.appendChild(envioCard);
    }

    form.hidden = Boolean(periodo.prazo_expirado);
    if (periodo.prazo_expirado) {
        envioAtual.appendChild(criarStatusApc("Prazo encerrado", "closed"));
    }
}

function renderPainelSelecionadoVazio() {
    el("apcTituloPainel").innerText = "Painel da data selecionada";
    el("apcSubtituloPainel").innerText = `Nenhuma APC cadastrada em ${paraDataBr(dataSelecionadaApc)}.`;
    el("apcResumoPainel").innerHTML = "";
    el("apcListaPainel").innerHTML =
        '<div class="booking-empty">Cadastre a data ao lado para comeÃ§ar a receber os anexos dos professores.</div>';
    preencherFormularioPeriodo(null);
    renderPainelProfessorApc(null);
}

async function carregarDetalheSelecionadoApc() {
    const resumo = periodoResumoPorData(dataSelecionadaApc);
    periodoSelecionadoApc = resumo;

    if (!resumo) {
        renderPainelSelecionadoVazio();
        return;
    }

    const detalhe = await fetchJson(`/apc/periodos/${resumo.id}`, { headers: headersApc });
    const periodo = detalhe.periodo || detalhe;
    periodoSelecionadoApc = periodo;

    el("apcTituloPainel").innerText = `${periodo.titulo} - ${paraDataBr(periodo.data_referencia)}`;
    el("apcSubtituloPainel").innerText = `${periodo.dia_semana_nome} | Prazo atÃ© ${periodo.prazo_envio_input.replace("T", " ")}`;

    if (usuarioApc?.pode_gerir) {
        el("apcResumoPainel").innerHTML = "";
        el("apcResumoPainel").appendChild(
            renderResumoPainelCards([
                { label: "ElegÃ­veis", valor: String(detalhe.total_elegiveis || 0) },
                { label: "Enviados", valor: String(detalhe.total_enviados || 0) },
                { label: "Pendentes", valor: String(detalhe.total_pendentes || 0) },
            ])
        );
        renderListaGestaoApc(detalhe);
        preencherFormularioPeriodo(periodo);
    } else {
        el("apcResumoPainel").innerHTML = "";
        el("apcListaPainel").innerHTML =
            '<div class="booking-empty">VocÃª estÃ¡ vendo apenas as APCs previstas para o seu horÃ¡rio.</div>';
    }

    if (usuarioApc?.eh_professor) {
        renderPainelProfessorApc(detalhe.periodo ? detalhe : null);
    }
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

    for (let i = 0; i < primeiroDiaSemana; i++) {
        const vazio = document.createElement("div");
        vazio.className = "calendar-empty";
        grid.appendChild(vazio);
    }

    for (let dia = 1; dia <= totalDias; dia++) {
        const dataIso = paraIso(new Date(ano, mes, dia));
        const periodo = periodoResumoPorData(dataIso);

        const btnDia = document.createElement("button");
        btnDia.type = "button";
        btnDia.className = "calendar-day apc-calendar-day";
        if (dataIso === dataSelecionadaApc) btnDia.classList.add("is-selected");
        if (dataIso === hojeIso) btnDia.classList.add("is-today");
        if (periodo) {
            btnDia.classList.add("has-apc");
            btnDia.classList.add(periodo.enviado ? "is-ok" : "is-pending");
        }

        const numero = document.createElement("span");
        numero.className = "calendar-number";
        numero.innerText = String(dia);
        btnDia.appendChild(numero);

        const resumo = document.createElement("small");
        resumo.className = "calendar-count";
        resumo.innerText = periodo
            ? usuarioApc?.pode_gerir
                ? `${periodo.total_enviados}/${periodo.total_elegiveis}`
                : periodo.enviado ? "OK" : "APC"
            : "Livre";
        btnDia.appendChild(resumo);

        if (periodo) {
            const flag = document.createElement("span");
            flag.className = "apc-calendar-flag";
            flag.innerText = periodo.titulo || "APC";
            btnDia.appendChild(flag);
        }

        btnDia.addEventListener("click", async () => {
            dataSelecionadaApc = dataIso;
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
    };

    try {
        if (periodoSelecionadoApc?.id) {
            await fetchJson(`/apc/periodos/${periodoSelecionadoApc.id}`, {
                method: "PUT",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
            });
            setMensagemApc("Data de APC atualizada com sucesso.");
        } else {
            await fetchJson("/apc/periodos", {
                method: "POST",
                headers: headersJsonApc,
                body: JSON.stringify(payload),
            });
            setMensagemApc("Data de APC cadastrada com sucesso.");
        }
        dataSelecionadaApc = payload.data_referencia;
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "NÃ£o foi possÃ­vel salvar a data da APC.", true);
    }
}

async function excluirPeriodoApc() {
    if (!periodoSelecionadoApc?.id) return;
    if (!window.confirm("Deseja realmente excluir esta data de APC?")) return;

    try {
        await fetchJson(`/apc/periodos/${periodoSelecionadoApc.id}`, {
            method: "DELETE",
            headers: headersApc,
        });
        setMensagemApc("Data de APC removida com sucesso.");
        periodoSelecionadoApc = null;
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "NÃ£o foi possÃ­vel excluir a data da APC.", true);
    }
}

async function enviarArquivoApc(event) {
    event.preventDefault();
    const resumo = periodoResumoPorData(dataSelecionadaApc);
    const arquivo = el("apcArquivo").files?.[0];

    if (!resumo?.id || !arquivo) {
        setMensagemApc("Selecione uma data de APC e um arquivo para enviar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        await fetchJson(`/apc/periodos/${resumo.id}/envio`, {
            method: "POST",
            headers: headersApc,
            body: formData,
        });
        el("apcArquivo").value = "";
        setMensagemApc("Arquivo da APC enviado com sucesso.");
        await carregarCalendarioApc();
    } catch (err) {
        setMensagemApc(err.message || "NÃ£o foi possÃ­vel enviar o arquivo da APC.", true);
    }
}

function registrarEventosApc() {
    el("btnVoltarServicos").addEventListener("click", () => {
        window.location.href = "/servicos";
    });
    el("btnSair").addEventListener("click", () => {
        encerrarSessao();
    });

    el("apcAnoLetivo").addEventListener("change", async () => {
        await carregarCalendarioApc();
    });

    el("btnApcMesAnterior").addEventListener("click", async () => {
        mesAtualApc = new Date(mesAtualApc.getFullYear(), mesAtualApc.getMonth() - 1, 1);
        await carregarCalendarioApc();
    });
    el("btnApcMesProximo").addEventListener("click", async () => {
        mesAtualApc = new Date(mesAtualApc.getFullYear(), mesAtualApc.getMonth() + 1, 1);
        await carregarCalendarioApc();
    });
    el("btnApcMesHoje").addEventListener("click", async () => {
        const hoje = new Date();
        mesAtualApc = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        dataSelecionadaApc = paraIso(hoje);
        await carregarCalendarioApc();
    });

    el("formApcPeriodo")?.addEventListener("submit", salvarPeriodoApc);
    el("btnNovaApc")?.addEventListener("click", () => {
        periodoSelecionadoApc = null;
        preencherFormularioPeriodo(null);
        setMensagemApc("");
    });
    el("btnExcluirApc")?.addEventListener("click", excluirPeriodoApc);
    el("formApcEnvio")?.addEventListener("submit", enviarArquivoApc);
}

async function initApc() {
    try {
        usuarioApc = await fetchJson("/me", { headers: headersApc });
        contextoApc = await fetchJson("/apc/contexto", { headers: headersApc });
        preencherSelectAnosApc();
        aplicarVisibilidadeApc();
        registrarEventosApc();
        await carregarCalendarioApc();
    } catch (_err) {
        encerrarSessao();
    }
}

window.addEventListener("DOMContentLoaded", initApc);
