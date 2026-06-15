const estadoRepeticaoAgendamento = {
    aulaBaseChave: ""
};

function obterAulaBaseRepeticaoAgendamento() {
    const aulas = Array.isArray(aulasProfessorDia) ? aulasProfessorDia : [];
    return aulas.find(
        (aula) => chaveAulaAgendamento(aula) === estadoRepeticaoAgendamento.aulaBaseChave
    ) || null;
}

function prepararEtapaRepeticaoAgendamento() {
    if (!estadoRepeticaoAgendamento.aulaBaseChave) {
        estadoRepeticaoAgendamento.aulaBaseChave = selecaoAulaAgendamento.chave;
    }
    renderEtapaRepeticaoAgendamento();
}

function limparEstadoRepeticaoAgendamento() {
    estadoRepeticaoAgendamento.aulaBaseChave = "";
}

function obterAulasCandidatasRepeticaoAgendamento() {
    const recursosSelecionados = obterRecursosSelecionadosAgendamento();
    const chaveBase = estadoRepeticaoAgendamento.aulaBaseChave;
    if (!chaveBase || recursosSelecionados.length === 0) {
        return [];
    }

    return ordenarAulasAgendamento(
        (Array.isArray(aulasProfessorDia) ? aulasProfessorDia : []).filter((aula) => {
            const chave = chaveAulaAgendamento(aula);
            return chave !== chaveBase
                && aulaSuportaRecursosSelecionados(aula, recursosSelecionados);
        })
    );
}

function obterAulasSelecionadasRepeticaoAgendamento() {
    const chaveBase = estadoRepeticaoAgendamento.aulaBaseChave;
    return obterAulasSelecionadasAgendamento().filter(
        (aula) => chaveAulaAgendamento(aula) !== chaveBase
    );
}

function alternarAulaRepeticaoAgendamento(aula) {
    const chave = chaveAulaAgendamento(aula);
    if (!chave || chave === estadoRepeticaoAgendamento.aulaBaseChave) {
        return;
    }

    if (aulasAdicionaisAgendamento.has(chave)) {
        aulasAdicionaisAgendamento.delete(chave);
        delete detalhesAulasAgendamento[chave];
    } else {
        aulasAdicionaisAgendamento.add(chave);
        obterDetalhesAulaAgendamento(chave);
    }

    renderEtapaRepeticaoAgendamento();
    atualizarResumoWizardAgendamento(obterEstadoWizardAgendamento());
    atualizarAcoesWizardAgendamento(obterEstadoWizardAgendamento());
}

function criarOpcaoAulaRepeticaoAgendamento(aula) {
    const chave = chaveAulaAgendamento(aula);
    const selecionada = aulasAdicionaisAgendamento.has(chave);
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "scheduler-repeat-option";
    botao.classList.toggle("is-selected", selecionada);
    botao.setAttribute("aria-pressed", selecionada ? "true" : "false");

    const check = document.createElement("span");
    check.className = "scheduler-repeat-check";
    check.setAttribute("aria-hidden", "true");
    check.innerText = "✓";

    const copy = document.createElement("span");
    copy.className = "scheduler-repeat-option-copy";
    const titulo = document.createElement("strong");
    titulo.innerText = obterTituloAulaAgendamento(aula);
    const meta = document.createElement("span");
    meta.innerText = obterResumoCurtoAulaAgendamento(aula);
    copy.appendChild(titulo);
    copy.appendChild(meta);

    botao.appendChild(check);
    botao.appendChild(copy);
    botao.addEventListener("click", () => alternarAulaRepeticaoAgendamento(aula));
    return botao;
}

function criarCampoRepeticaoAgendamento(aula) {
    const chave = chaveAulaAgendamento(aula);
    const detalhes = obterDetalhesAulaAgendamento(chave);
    const card = document.createElement("article");
    card.className = "scheduler-lesson-detail-card";

    const cabecalho = document.createElement("div");
    cabecalho.className = "scheduler-lesson-detail-header";
    const titulo = document.createElement("h3");
    titulo.innerText = obterTituloAulaAgendamento(aula);
    const meta = document.createElement("p");
    meta.innerText = obterResumoCurtoAulaAgendamento(aula);
    cabecalho.appendChild(titulo);
    cabecalho.appendChild(meta);

    const tema = criarCampoTextoRepeticao({
        id: `temaRepeticao-${chave}`,
        label: "Tema da aula",
        value: detalhes.tema,
        placeholder: "Ex.: Continuação da atividade prática",
        required: true,
        onInput: (value) => {
            detalhes.tema = value;
            atualizarAcoesWizardAgendamento(obterEstadoWizardAgendamento());
        }
    });
    const observacao = criarCampoTextoRepeticao({
        id: `observacaoRepeticao-${chave}`,
        label: "Observação",
        value: detalhes.observacao,
        placeholder: "Orientações específicas para esta aula",
        textarea: true,
        onInput: (value) => {
            detalhes.observacao = value;
        }
    });

    card.appendChild(cabecalho);
    card.appendChild(tema);
    card.appendChild(observacao);
    return card;
}

function criarCampoTextoRepeticao({
    id,
    label,
    value,
    placeholder,
    required = false,
    textarea = false,
    onInput
}) {
    const grupo = document.createElement("article");
    grupo.className = "print-field-group";
    const rotulo = document.createElement("label");
    rotulo.setAttribute("for", id);
    rotulo.innerText = label;
    const campo = document.createElement(textarea ? "textarea" : "input");
    campo.id = id;
    if (!textarea) {
        campo.type = "text";
        campo.maxLength = 160;
    } else {
        campo.rows = 3;
    }
    campo.required = required;
    campo.placeholder = placeholder;
    campo.value = value || "";
    campo.addEventListener("input", () => onInput(campo.value));
    grupo.appendChild(rotulo);
    grupo.appendChild(campo);
    return grupo;
}

function renderEtapaRepeticaoAgendamento() {
    const lista = el("listaAulasRepeticaoAgendamento");
    const resumo = el("resumoRepeticaoAgendamento");
    const quantidade = el("quantidadeRepeticaoAgendamento");
    const detalhesSection = el("detalhesRepeticaoAgendamento");
    const detalhesLista = el("listaDetalhesRepeticaoAgendamento");
    if (!lista || !detalhesLista) {
        return;
    }

    const candidatas = obterAulasCandidatasRepeticaoAgendamento();
    const chavesCandidatas = new Set(candidatas.map((aula) => chaveAulaAgendamento(aula)));
    obterAulasSelecionadasRepeticaoAgendamento().forEach((aula) => {
        const chave = chaveAulaAgendamento(aula);
        if (!chavesCandidatas.has(chave)) {
            aulasAdicionaisAgendamento.delete(chave);
            delete detalhesAulasAgendamento[chave];
        }
    });
    const selecionadas = obterAulasSelecionadasRepeticaoAgendamento();
    lista.innerHTML = "";
    detalhesLista.innerHTML = "";

    candidatas.forEach((aula) => lista.appendChild(criarOpcaoAulaRepeticaoAgendamento(aula)));
    selecionadas.forEach((aula) => detalhesLista.appendChild(criarCampoRepeticaoAgendamento(aula)));

    if (candidatas.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "scheduler-repeat-empty";
        vazio.innerText = "Não há outra aula com todos os recursos escolhidos disponíveis nesta data.";
        lista.appendChild(vazio);
    }

    if (resumo) {
        resumo.innerText = candidatas.length > 0
            ? `${candidatas.length} outra(s) aula(s) podem receber os mesmos recursos.`
            : "Você pode confirmar apenas a aula já configurada.";
    }
    if (quantidade) {
        quantidade.innerText = `${selecionadas.length} selecionada(s)`;
    }
    if (detalhesSection) {
        detalhesSection.hidden = selecionadas.length === 0;
    }
}
