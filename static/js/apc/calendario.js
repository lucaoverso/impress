const { el } = window.AppDom;
const { garantirToken, criarHeadersAuth, encerrarSessao } = window.AppAuth;
const { fetchJson } = window.AppApi;
const { paraIso, paraDataBr } = window.AppFormat;

const headersCalendarioApc = criarHeadersAuth(garantirToken());
const mesesCalendarioApc = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];
const diasCalendarioApc = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

let contextoCalendarioApc = null;
let mesCalendarioApc = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
let periodosCalendarioApc = [];
let dataSelecionadaCalendarioApc = paraIso(new Date());

function mesIsoCalendarioApc(data) {
    return `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}`;
}

function periodosDoDiaCalendarioApc(dataIso) {
    return periodosCalendarioApc.filter((periodo) => periodo.data_referencia === dataIso);
}

function statusPeriodoCalendarioApc(periodo) {
    return Number(periodo.total_pendentes || 0) > 0
        ? { texto: "Pendente", classe: "" }
        : { texto: "Concluído", classe: "is-complete" };
}

function setMensagemCalendarioApc(texto, erro = false) {
    const mensagem = el("apcCalendarioMensagem");
    mensagem.textContent = texto || "";
    mensagem.classList.toggle("is-error", Boolean(erro));
}

function preencherAnosCalendarioApc() {
    const select = el("apcCalendarioAnoLetivo");
    select.replaceChildren();
    const anos = contextoCalendarioApc?.anos_letivos || [new Date().getFullYear()];
    anos.forEach((ano) => {
        const option = document.createElement("option");
        option.value = String(ano);
        option.textContent = String(ano);
        select.appendChild(option);
    });
    const anoAtual = Number(contextoCalendarioApc?.ano_letivo_atual || anos[0]);
    select.value = String(anoAtual);
    mesCalendarioApc = new Date(anoAtual, mesCalendarioApc.getMonth(), 1);
}

function renderAgendaCalendarioApc(dataIso) {
    const itens = periodosDoDiaCalendarioApc(dataIso);
    const lista = el("apcAgendaLista");
    el("apcAgendaTitulo").textContent = paraDataBr(dataIso);
    el("apcAgendaResumo").textContent = itens.length
        ? `${itens.length} ${itens.length === 1 ? "entrega prevista" : "entregas previstas"} para esta data.`
        : "Nenhuma entrega prevista para esta data.";
    lista.replaceChildren();

    if (!itens.length) {
        const vazio = document.createElement("p");
        vazio.className = "apc-calendar-empty-state";
        vazio.textContent = "O dia está livre de demandas na Central de Anexos.";
        lista.appendChild(vazio);
        return;
    }

    itens.forEach((periodo) => {
        const status = statusPeriodoCalendarioApc(periodo);
        const artigo = document.createElement("article");
        artigo.className = "apc-calendar-agenda-item";

        const titulo = document.createElement("h3");
        titulo.textContent = periodo.titulo || "Entrega pedagógica";
        const prazo = document.createElement("p");
        prazo.textContent = periodo.prazo_envio
            ? `Prazo: ${String(periodo.prazo_envio).replace("T", " ").slice(0, 16)}`
            : `Data: ${paraDataBr(periodo.data_referencia)}`;
        const etiqueta = document.createElement("span");
        etiqueta.className = `apc-calendar-agenda-status ${status.classe}`.trim();
        etiqueta.textContent = status.texto;

        artigo.append(titulo, prazo, etiqueta);
        lista.appendChild(artigo);
    });
}

function selecionarDataCalendarioApc(dataIso) {
    dataSelecionadaCalendarioApc = dataIso;
    document.querySelectorAll(".apc-calendar-day").forEach((dia) => {
        const selecionado = dia.dataset.date === dataIso;
        dia.classList.toggle("is-selected", selecionado);
        dia.setAttribute("aria-pressed", String(selecionado));
    });
    renderAgendaCalendarioApc(dataIso);
}

function renderCalendarioApc() {
    const ano = mesCalendarioApc.getFullYear();
    const mes = mesCalendarioApc.getMonth();
    const grid = el("apcCalendarioGrid");
    el("apcCalendarioMesAtual").textContent = `${mesesCalendarioApc[mes]} ${ano}`;
    grid.replaceChildren();

    diasCalendarioApc.forEach((dia) => {
        const cabecalho = document.createElement("div");
        cabecalho.className = "apc-calendar-weekday";
        cabecalho.textContent = dia;
        grid.appendChild(cabecalho);
    });

    const primeiroDia = new Date(ano, mes, 1).getDay();
    const totalDias = new Date(ano, mes + 1, 0).getDate();
    for (let indice = 0; indice < primeiroDia; indice += 1) {
        const vazio = document.createElement("div");
        vazio.className = "apc-calendar-empty";
        grid.appendChild(vazio);
    }

    for (let numeroDia = 1; numeroDia <= totalDias; numeroDia += 1) {
        const dataIso = paraIso(new Date(ano, mes, numeroDia));
        const itens = periodosDoDiaCalendarioApc(dataIso);
        const pendente = itens.some((item) => Number(item.total_pendentes || 0) > 0);
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "apc-calendar-day";
        botao.dataset.date = dataIso;
        botao.setAttribute("aria-label", `${paraDataBr(dataIso)}: ${itens.length} entrega(s)`);
        if (dataIso === paraIso(new Date())) botao.classList.add("is-today");
        if (itens.length) botao.classList.add("has-items", pendente ? "is-pending" : "is-complete");

        const numero = document.createElement("span");
        numero.className = "apc-calendar-number";
        numero.textContent = String(numeroDia);
        const resumo = document.createElement("span");
        resumo.className = "apc-calendar-count";
        resumo.textContent = itens.length
            ? `${itens.length} ${itens.length === 1 ? "entrega" : "entregas"}`
            : "Livre";
        botao.append(numero, resumo);
        botao.addEventListener("click", () => selecionarDataCalendarioApc(dataIso));
        grid.appendChild(botao);
    }

    const selecionadaNoMes = dataSelecionadaCalendarioApc.startsWith(mesIsoCalendarioApc(mesCalendarioApc));
    const primeiraEntrega = periodosCalendarioApc.find((item) =>
        String(item.data_referencia || "").startsWith(mesIsoCalendarioApc(mesCalendarioApc))
    );
    selecionarDataCalendarioApc(
        selecionadaNoMes ? dataSelecionadaCalendarioApc : (primeiraEntrega?.data_referencia || paraIso(new Date(ano, mes, 1)))
    );
}

async function carregarCalendarioApc() {
    setMensagemCalendarioApc("Carregando calendário...");
    const anoLetivo = el("apcCalendarioAnoLetivo").value;
    const visao = contextoCalendarioApc?.usuario?.pode_gerir ? "gestao" : "docente";
    try {
        const resposta = await fetchJson(
            `/apc/calendario?mes=${mesIsoCalendarioApc(mesCalendarioApc)}&ano_letivo=${anoLetivo}&visao=${visao}`,
            { headers: headersCalendarioApc }
        );
        periodosCalendarioApc = resposta.periodos || [];
        setMensagemCalendarioApc("");
        renderCalendarioApc();
    } catch (erro) {
        setMensagemCalendarioApc(erro.message || "Não foi possível carregar o calendário.", true);
    }
}

function registrarEventosCalendarioApc() {
    el("apcCalendarioAnoLetivo").addEventListener("change", () => {
        mesCalendarioApc = new Date(Number(el("apcCalendarioAnoLetivo").value), mesCalendarioApc.getMonth(), 1);
        void carregarCalendarioApc();
    });
    el("btnApcCalendarioAnterior").addEventListener("click", () => {
        mesCalendarioApc = new Date(mesCalendarioApc.getFullYear(), mesCalendarioApc.getMonth() - 1, 1);
        void carregarCalendarioApc();
    });
    el("btnApcCalendarioProximo").addEventListener("click", () => {
        mesCalendarioApc = new Date(mesCalendarioApc.getFullYear(), mesCalendarioApc.getMonth() + 1, 1);
        void carregarCalendarioApc();
    });
    el("btnApcCalendarioHoje").addEventListener("click", () => {
        const hoje = new Date();
        mesCalendarioApc = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        dataSelecionadaCalendarioApc = paraIso(hoje);
        void carregarCalendarioApc();
    });
}

async function initCalendarioApc() {
    try {
        contextoCalendarioApc = await fetchJson("/apc/contexto", { headers: headersCalendarioApc });
        preencherAnosCalendarioApc();
        registrarEventosCalendarioApc();
        await carregarCalendarioApc();
    } catch (_erro) {
        encerrarSessao();
    }
}

window.addEventListener("DOMContentLoaded", initCalendarioApc);
