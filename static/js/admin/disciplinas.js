async function carregarDisciplinasAdmin() {
    const disciplinas = await fetchJson("/admin/disciplinas?incluir_inativas=true", { headers });
    const ul = el("listaDisciplinasAdmin");
    ul.innerHTML = "";

    if (!Array.isArray(disciplinas) || disciplinas.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma disciplina cadastrada.";
        ul.appendChild(vazio);
        return;
    }

    disciplinas.forEach((disciplina) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = disciplina.nome;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Carga horaria base: ${disciplina.aulas_semanais ?? 0}h | APC: ${disciplina.tem_apc ? "Sim" : "Nao"} | Prova bimestral: ${disciplina.tem_prova_bimestral ? "Sim" : "Nao"} | Status: ${disciplina.ativo ? "Ativa" : "Inativa"}`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const inputAulas = document.createElement("input");
        inputAulas.type = "number";
        inputAulas.min = "0";
        inputAulas.value = String(disciplina.aulas_semanais ?? 0);
        inputAulas.title = "Carga horaria base";

        const labelApc = document.createElement("label");
        labelApc.className = "admin-checkbox-item";
        const inputTemApc = document.createElement("input");
        inputTemApc.type = "checkbox";
        inputTemApc.checked = Boolean(disciplina.tem_apc);
        const textoApc = document.createElement("span");
        textoApc.innerText = "Tem APC";
        labelApc.appendChild(inputTemApc);
        labelApc.appendChild(textoApc);

        const labelProva = document.createElement("label");
        labelProva.className = "admin-checkbox-item";
        const inputTemProva = document.createElement("input");
        inputTemProva.type = "checkbox";
        inputTemProva.checked = Boolean(disciplina.tem_prova_bimestral);
        const textoProva = document.createElement("span");
        textoProva.innerText = "Tem prova bimestral";
        labelProva.appendChild(inputTemProva);
        labelProva.appendChild(textoProva);

        const btnSalvarDados = document.createElement("button");
        btnSalvarDados.type = "button";
        btnSalvarDados.innerText = "Salvar dados";
        btnSalvarDados.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        aulas_semanais: Number(inputAulas.value),
                        tem_apc: inputTemApc.checked,
                        tem_prova_bimestral: inputTemProva.checked
                    })
                });
                setMensagem("msgDisciplina", `Dados da disciplina ${disciplina.nome} atualizados.`);
                await Promise.all([carregarDisciplinasAdmin(), atualizarAtribuicoesDocentesSePermitido()]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        const btnStatus = document.createElement("button");
        btnStatus.type = "button";
        btnStatus.innerText = disciplina.ativo ? "Desativar" : "Ativar";
        btnStatus.addEventListener("click", async () => {
            try {
                await fetchJson(`/admin/disciplinas/${disciplina.id}/status`, {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({ ativo: !Boolean(disciplina.ativo) })
                });
                await Promise.all([
                    carregarDisciplinasAdmin(),
                    atualizarOpcoesProfessorSePermitido(),
                    atualizarAtribuicoesDocentesSePermitido()
                ]);
            } catch (err) {
                setMensagem("msgDisciplina", err.message, true);
            }
        });

        linha.appendChild(inputAulas);
        linha.appendChild(labelApc);
        linha.appendChild(labelProva);
        linha.appendChild(btnSalvarDados);

        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(linha);
        li.appendChild(btnStatus);
        ul.appendChild(li);
    });
}

async function cadastrarDisciplina(event) {
    event.preventDefault();
    try {
        await fetchJson("/admin/disciplinas", {
            method: "POST",
            headers: headersJson,
            body: JSON.stringify({
                nome: el("disciplinaNome").value.trim(),
                aulas_semanais: Number(el("disciplinaAulasSemanais").value),
                tem_apc: Boolean(el("disciplinaTemApc")?.checked),
                tem_prova_bimestral: Boolean(el("disciplinaTemProvaBimestral")?.checked)
            })
        });

        setMensagem("msgDisciplina", "Disciplina cadastrada com sucesso.");
        el("formDisciplina").reset();
        el("disciplinaAulasSemanais").value = "0";
        if (el("disciplinaTemApc")) {
            el("disciplinaTemApc").checked = false;
        }
        if (el("disciplinaTemProvaBimestral")) {
            el("disciplinaTemProvaBimestral").checked = false;
        }
        await Promise.all([
            carregarDisciplinasAdmin(),
            atualizarOpcoesProfessorSePermitido(),
            atualizarAtribuicoesDocentesSePermitido()
        ]);
    } catch (err) {
        setMensagem("msgDisciplina", err.message, true);
    }
}
