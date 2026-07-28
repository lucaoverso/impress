const {
    garantirToken,
    criarHeadersAuth,
    encerrarSessao,
    normalizarCargoUsuario,
} = window.AppAuth;
const { fetchComAuth } = window.AppApi;

const token = garantirToken();
const headers = criarHeadersAuth(token);

function modulosPermitidos(usuario = {}) {
    usuario = usuario && typeof usuario === "object" ? usuario : {};
    if (Array.isArray(usuario.modulos) && usuario.modulos.length > 0) {
        return new Set(usuario.modulos.map((item) => String(item).trim().toLowerCase()));
    }

    const cargo = normalizarCargoUsuario(usuario);
    if (cargo === "ADMIN") return new Set(["impressao", "agendamento", "download", "gestao", "relatorios", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
    if (cargo === "COORDENADOR") return new Set(["impressao", "download", "relatorios", "coordenacao", "horario", "apc", "pcpi", "preconselho"]);
    return new Set(["impressao", "agendamento", "download", "coordenacao", "horario", "apc", "preconselho"]);
}

function aplicarVisibilidadeModulos(modulos) {
    document.querySelectorAll("[data-modulo]").forEach((elemento) => {
        const modulo = String(elemento.dataset.modulo || "").trim().toLowerCase();
        elemento.hidden = !modulos.has(modulo);
    });
}

function estadoProximasAulas(mensagem, icone = "bi-calendar2") {
    const lista = document.getElementById("teacherUpcomingLessons");
    lista.replaceChildren();
    const estado = document.createElement("div");
    estado.className = "teacher-upcoming-state";
    const simbolo = document.createElement("i");
    simbolo.className = `bi ${icone}`;
    simbolo.setAttribute("aria-hidden", "true");
    const texto = document.createElement("p");
    texto.textContent = mensagem;
    estado.append(simbolo, texto);
    lista.append(estado);
}

function renderizarProximasAulas(payload = {}) {
    const aulas = Array.isArray(payload.aulas) ? payload.aulas : [];
    document.getElementById("teacherUpcomingPeriod").textContent =
        payload.periodo_rotulo || "Próximos 7 dias";
    if (!aulas.length) {
        estadoProximasAulas("Nenhuma aula encontrada nos próximos dias.");
        return;
    }

    const lista = document.getElementById("teacherUpcomingLessons");
    lista.replaceChildren();
    aulas.forEach((aula) => {
        const item = document.createElement("article");
        item.className = `teacher-lesson-item${aula.em_andamento ? " is-current" : ""}`;

        const horario = document.createElement("div");
        horario.className = "teacher-lesson-time";
        const inicio = document.createElement("strong");
        inicio.textContent = aula.horario_inicio || `${aula.aula_numero}ª aula`;
        horario.append(inicio);
        if (aula.horario_fim) {
            const fim = document.createElement("span");
            fim.textContent = aula.horario_fim;
            horario.append(fim);
        }

        const descricao = document.createElement("div");
        descricao.className = "teacher-lesson-copy";
        const data = document.createElement("span");
        data.textContent = aula.data_rotulo || "";
        const titulo = document.createElement("h3");
        titulo.textContent = [aula.turma_nome, aula.disciplina_nome].filter(Boolean).join(" · ");
        const turno = document.createElement("p");
        turno.textContent = aula.turno_nome || "Horário escolar";
        descricao.append(data, titulo, turno);

        item.append(horario, descricao);
        if (aula.em_andamento) {
            const atual = document.createElement("span");
            atual.className = "teacher-lesson-current";
            atual.setAttribute("aria-label", "Aula em andamento");
            item.append(atual);
        }
        lista.append(item);
    });
}

async function carregarProximasAulas() {
    try {
        const resposta = await fetchComAuth("/horario-escolar/minhas-proximas-aulas", { headers });
        if (!resposta.ok) throw new Error("Falha ao carregar próximas aulas.");
        renderizarProximasAulas(await resposta.json());
    } catch (erro) {
        estadoProximasAulas("Não foi possível carregar suas próximas aulas.", "bi-exclamation-circle");
    }
}

async function carregarUsuario() {
    try {
        const res = await fetchComAuth("/me", { headers });
        if (!res.ok) {
            encerrarSessao();
            return;
        }

        const usuario = await res.json();
        const titulo = document.getElementById("tituloBoasVindas");
        const primeiroNome = String(usuario.nome || "usuário").trim().split(/\s+/)[0];
        titulo.innerText = `Olá, ${primeiroNome}. Escolha o serviço`;
        aplicarVisibilidadeModulos(modulosPermitidos(usuario));
        if (usuario.eh_professor) {
            document.body.classList.add("services-dashboard-body--teacher");
            document.getElementById("servicesPageLead").textContent =
                "Veja seus próximos compromissos e acesse as ferramentas do seu dia.";
            document.getElementById("teacherDashboardRail").hidden = false;
            carregarProximasAulas();
        }
    } catch (err) {
        encerrarSessao();
    }
}

carregarUsuario();
