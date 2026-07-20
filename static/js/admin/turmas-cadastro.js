function atualizarJanelaAulasFormularioTurma({ forcarPadrao = false } = {}) {
    sincronizarSelectsJanelaAulasTurma({
        turno: el("turmaTurno")?.value || "MATUTINO",
        selectInicial: el("turmaAulaInicial"),
        selectFinal: el("turmaAulaFinal"),
        aulaInicialAtual: Number(el("turmaAulaInicial")?.value || 0),
        aulaFinalAtual: Number(el("turmaAulaFinal")?.value || 0),
        forcarPadrao
    });
}

async function carregarTurmasAdmin() {
    const turmas = await fetchJson("/admin/turmas/dados?incluir_inativas=true", { headers });
    const ul = el("listaTurmasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(turmas) || turmas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma turma cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    turmas.forEach((turma) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = turma.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = [
            `Turno: ${nomeTurno(turma.turno)}`,
            `Aulas: ${Number(turma.aula_inicial || 0)} a ${Number(turma.aula_final || 0)}`,
            `Estudantes: ${turma.quantidade_estudantes ?? 0}`,
            `Status: ${turma.ativo ? "Ativa" : "Inativa"}`
        ].join(" | ");

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputTurno = document.createElement("select");
        ["MATUTINO", "VESPERTINO", "VESPERTINO_EM", "INTEGRAL"].forEach((turno) => {
            const option = document.createElement("option");
            option.value = turno;
            option.innerText = nomeTurno(turno);
            inputTurno.appendChild(option);
        });
        inputTurno.value = turma.turno && TURNO_LABEL[turma.turno] ? turma.turno : "MATUTINO";

        const inputQuantidade = document.createElement("input");
        inputQuantidade.type = "number";
        inputQuantidade.min = "0";
        inputQuantidade.value = String(turma.quantidade_estudantes ?? 0);
        inputQuantidade.title = "Quantidade de estudantes";

        const inputAulaInicial = document.createElement("select");
        inputAulaInicial.title = "Aula inicial da turma";

        const inputAulaFinal = document.createElement("select");
        inputAulaFinal.title = "Aula final da turma";

        const atualizarJanelaTurma = ({ forcarPadrao = false } = {}) => {
            sincronizarSelectsJanelaAulasTurma({
                turno: inputTurno.value,
                selectInicial: inputAulaInicial,
                selectFinal: inputAulaFinal,
                aulaInicialAtual: Number(inputAulaInicial.value || turma.aula_inicial || 0),
                aulaFinalAtual: Number(inputAulaFinal.value || turma.aula_final || 0),
                forcarPadrao
            });
        };

        atualizarJanelaTurma();
        inputTurno.addEventListener("change", () => atualizarJanelaTurma({ forcarPadrao: true }));
        inputAulaInicial.addEventListener("change", () => atualizarJanelaTurma());

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar dados";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                const aulaInicial = Number(inputAulaInicial.value || 0);
                const aulaFinal = Number(inputAulaFinal.value || 0);
                if (aulaInicial <= 0 || aulaFinal <= 0) {
                    throw new Error("Configure a grade global antes de salvar a turma.");
                }
                await fetchJson(`/admin/turmas/${turma.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        turno: inputTurno.value,
                        aula_inicial: aulaInicial,
                        aula_final: aulaFinal,
                        quantidade_estudantes: Number(inputQuantidade.value)
                    })
                });
                setMensagem("msgTurma", `Dados da turma ${turma.nome} atualizados.`);
                await Promise.all([carregarTurmasAdmin(), atualizarAtribuicoesDocentesSePermitido()]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = turma.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/turmas/${turma.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(turma.ativo) })
                });
                await Promise.all([
                    carregarTurmasAdmin(),
                    atualizarOpcoesProfessorSePermitido(),
                    atualizarAtribuicoesDocentesSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgTurma", err.message, true);
            }
        });

        linha.appendChild(inputTurno);
        linha.appendChild(inputAulaInicial);
        linha.appendChild(inputAulaFinal);
        linha.appendChild(inputQuantidade);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarTurma(event) {
    event.preventDefault();
    try {
        const aulaInicial = Number(el("turmaAulaInicial")?.value || 0);
        const aulaFinal = Number(el("turmaAulaFinal")?.value || 0);
        if (aulaInicial <= 0 || aulaFinal <= 0) {
            throw new Error("Cadastre primeiro a grade global de aulas da escola.");
        }
        await fetchJson("/admin/turmas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("turmaNome").value.trim(),
                turno: el("turmaTurno").value,
                aula_inicial: aulaInicial,
                aula_final: aulaFinal,
                quantidade_estudantes: Number(el("turmaQuantidadeEstudantes").value)
            })
        });

        setMensagem("msgTurma", "Turma cadastrada com sucesso.");
        el("formTurma").reset();
        el("turmaTurno").value = "MATUTINO";
        el("turmaQuantidadeEstudantes").value = "0";
        atualizarJanelaAulasFormularioTurma({ forcarPadrao: true });
        await Promise.all([
            carregarTurmasAdmin(),
            atualizarOpcoesProfessorSePermitido(),
            atualizarAtribuicoesDocentesSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgTurma", err.message, true);
    }
}
