function chaveProfessorVisaoDia(reserva) {
    const usuarioId = Number(reserva?.usuario_id || 0);
    if (usuarioId > 0) {
        return `id:${usuarioId}`;
    }
    return `nome:${String(reserva?.professor_nome || "").trim().toLowerCase()}`;
}

function agruparReservasVisaoDia(reservas = []) {
    const aulas = new Map();

    reservas.forEach((reserva) => {
        const faixa = Number(faixaGlobalReserva(reserva) || 0);
        if (faixa <= 0) {
            return;
        }

        if (!aulas.has(faixa)) {
            aulas.set(faixa, {
                faixa,
                aulaNumero: numeroAulaReserva(reserva),
                professores: new Map()
            });
        }

        const grupoAula = aulas.get(faixa);
        const chaveProfessor = chaveProfessorVisaoDia(reserva);
        if (!grupoAula.professores.has(chaveProfessor)) {
            grupoAula.professores.set(chaveProfessor, {
                nome: textoPadraoDetalheReserva(
                    reserva.professor_nome,
                    "Responsável não informado"
                ),
                recursos: new Set()
            });
        }

        grupoAula.professores.get(chaveProfessor).recursos.add(
            textoPadraoDetalheReserva(reserva.recurso_nome, "Recurso não informado")
        );
    });

    return Array.from(aulas.values())
        .sort((a, b) => a.faixa - b.faixa)
        .map((grupo) => ({
            ...grupo,
            professores: Array.from(grupo.professores.values()).sort(
                (a, b) => compararTextoPtBr(a.nome, b.nome)
            )
        }));
}

function criarLinhaProfessorVisaoDia(grupoProfessor) {
    const linha = document.createElement("div");
    linha.className = "scheduler-day-overview-row";

    const copy = document.createElement("div");
    copy.className = "scheduler-day-overview-copy";

    const professor = document.createElement("strong");
    professor.innerText = grupoProfessor.nome;

    const recursos = document.createElement("span");
    recursos.innerText = Array.from(grupoProfessor.recursos)
        .sort(compararTextoPtBr)
        .join(", ");

    copy.appendChild(professor);
    copy.appendChild(recursos);
    linha.appendChild(copy);
    return linha;
}

function renderVisaoGeralAgendamentosDia() {
    const container = el("schedulerDayOverviewList");
    const dataResumo = el("schedulerDayOverviewDate");
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (dataResumo) {
        dataResumo.innerText = paraDataBr(dataSelecionada);
    }

    const reservasDia = (Array.isArray(reservasMes) ? reservasMes : [])
        .filter((reserva) => reserva.data === dataSelecionada);

    if (reservasDia.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-day-overview-empty";
        vazio.innerText = "Nenhum recurso agendado neste dia.";
        container.appendChild(vazio);
        return;
    }

    agruparReservasVisaoDia(reservasDia).forEach((grupoAula) => {
        const grupo = document.createElement("section");
        grupo.className = "scheduler-day-overview-shift";

        const titulo = document.createElement("h4");
        titulo.innerText = aulaLabel(grupoAula.aulaNumero);
        grupo.appendChild(titulo);

        const lista = document.createElement("div");
        lista.className = "scheduler-day-overview-rows";
        grupoAula.professores.forEach((professor) => {
            lista.appendChild(criarLinhaProfessorVisaoDia(professor));
        });

        grupo.appendChild(lista);
        container.appendChild(grupo);
    });
}

async function carregarReservasProximosDias() {
    const dataBase = criarDataLocalPorIso(dataSelecionada) || new Date();
    const inicio = paraIso(somarDiasDataLocal(dataBase, 1));
    const fim = paraIso(somarDiasDataLocal(dataBase, 30));
    const url = `/agendamento/reservas?data_inicio=${inicio}&data_fim=${fim}`;
    const response = await fetchComAuth(url, { headers });

    if (!response.ok) {
        throw new Error("Não foi possível carregar os próximos agendamentos.");
    }
    reservasProximosDias = await response.json();
}

function agruparReservasPorDataProxima(reservas = []) {
    const datas = new Map();
    reservas.forEach((reserva) => {
        const data = String(reserva?.data || "").trim();
        if (!data) {
            return;
        }
        if (!datas.has(data)) {
            datas.set(data, []);
        }
        datas.get(data).push(reserva);
    });
    return Array.from(datas.entries())
        .sort(([dataA], [dataB]) => dataA.localeCompare(dataB))
        .slice(0, 5);
}

function formatarDataProximoAgendamento(dataIso) {
    const data = criarDataLocalPorIso(dataIso);
    if (!data) {
        return paraDataBr(dataIso);
    }
    const texto = data.toLocaleDateString("pt-BR", {
        weekday: "long",
        day: "2-digit",
        month: "long"
    });
    return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function criarGrupoProximaData(dataIso, reservasData) {
    const grupoData = document.createElement("article");
    grupoData.className = "scheduler-upcoming-date";

    const dataTitulo = document.createElement("h4");
    dataTitulo.className = "scheduler-upcoming-date-title";
    dataTitulo.innerText = formatarDataProximoAgendamento(dataIso);
    grupoData.appendChild(dataTitulo);

    const aulas = document.createElement("div");
    aulas.className = "scheduler-upcoming-lessons";
    agruparReservasVisaoDia(reservasData).forEach((grupoAula) => {
        const grupo = document.createElement("section");
        grupo.className = "scheduler-day-overview-shift";

        const titulo = document.createElement("h4");
        titulo.innerText = aulaLabel(grupoAula.aulaNumero);
        grupo.appendChild(titulo);

        const lista = document.createElement("div");
        lista.className = "scheduler-day-overview-rows";
        grupoAula.professores.forEach((professor) => {
            lista.appendChild(criarLinhaProfessorVisaoDia(professor));
        });
        grupo.appendChild(lista);
        aulas.appendChild(grupo);
    });

    grupoData.appendChild(aulas);
    return grupoData;
}

function renderVisaoProximosAgendamentos() {
    const container = el("schedulerUpcomingOverviewList");
    const contador = el("schedulerUpcomingOverviewCount");
    if (!container) {
        return;
    }

    const gruposData = agruparReservasPorDataProxima(reservasProximosDias);
    container.innerHTML = "";
    if (contador) {
        contador.innerText = gruposData.length > 0
            ? `${gruposData.length} dia(s) com reservas`
            : "";
    }

    if (gruposData.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-day-overview-empty";
        vazio.innerText = "Nenhum agendamento encontrado nos próximos 30 dias.";
        container.appendChild(vazio);
        return;
    }

    gruposData.forEach(([dataIso, reservasData]) => {
        container.appendChild(criarGrupoProximaData(dataIso, reservasData));
    });
}
