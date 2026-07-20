async function carregarAtribuicoesDocentes() {
    const lista = await fetchJson(`/admin/atribuicoes-docentes${queryAtribuicoesDocentes()}`, { headers });
    const ul = el("listaAtribuicoesDocentesAdmin");
    if (!ul) {
        return;
    }
    ul.innerHTML = "";

    if (!Array.isArray(lista) || lista.length === 0) {
        const vazio = document.createElement("li");
        vazio.className = "booking-empty";
        vazio.innerText = "Nenhuma atribuicao docente encontrada para os filtros selecionados.";
        ul.appendChild(vazio);
        return;
    }

    const grupos = new Map();
    lista.forEach((item) => {
        const chave = `${item.professor_id}::${item.disciplina_id}`;
        if (!grupos.has(chave)) {
            grupos.set(chave, {
                professor_id: Number(item.professor_id),
                professor_nome: item.professor_nome,
                disciplina_id: Number(item.disciplina_id),
                disciplina_nome: item.disciplina_nome,
                professor_ativo: Boolean(item.professor_ativo),
                disciplina_ativa: Boolean(item.disciplina_ativa),
                turmas: []
            });
        }
        grupos.get(chave).turmas.push({
            id: Number(item.turma_id),
            nome: item.turma_nome,
            turno: item.turno,
            ativa: Boolean(item.turma_ativa)
        });
    });

    Array.from(grupos.values()).forEach((item) => {
        const li = document.createElement("li");
        li.className = "admin-list-item";

        const titulo = document.createElement("p");
        titulo.innerText = `${item.professor_nome} | ${item.disciplina_nome}`;

        const detalhe = document.createElement("p");
        detalhe.className = "booking-detail";
        detalhe.innerText = `Turmas: ${item.turmas.map((turma) => `${turma.nome} (${nomeTurno(turma.turno)})`).join(", ")}`;

        const status = document.createElement("p");
        status.className = "booking-detail";
        status.innerText = `Status: ${
            item.professor_ativo && item.disciplina_ativa && item.turmas.every((turma) => turma.ativa)
                ? "Ativo"
                : "Vinculo com item inativo"
        }`;

        const linha = document.createElement("div");
        linha.className = "admin-inline";

        const btnEditar = document.createElement("button");
        btnEditar.type = "button";
        btnEditar.innerText = "Editar turmas";
        btnEditar.addEventListener("click", async () => {
            el("atribuicaoProfessor").value = String(item.professor_id);
            el("atribuicaoDisciplina").value = String(item.disciplina_id);
            await carregarTurmasAtribuidasProfessorDisciplina();
            ativarAbaAdmin("atribuicoes");
            el("formAtribuicaoDocente").scrollIntoView({ behavior: "smooth", block: "start" });
        });

        const btnLimpar = document.createElement("button");
        btnLimpar.type = "button";
        btnLimpar.innerText = "Limpar turmas";
        btnLimpar.addEventListener("click", async () => {
            const confirmado = window.confirm(
                `Remover todas as turmas de ${item.professor_nome} em ${item.disciplina_nome}?`
            );
            if (!confirmado) {
                return;
            }
            try {
                await fetchJson("/admin/atribuicoes-docentes/lote", {
                    method: "PUT",
                    headers: headersJson,
                    body: JSON.stringify({
                        professor_id: item.professor_id,
                        disciplina_id: item.disciplina_id,
                        turma_ids: []
                    })
                });
                setMensagem("msgAtribuicoesDocentes", "Atribuicoes removidas com sucesso.");
                await Promise.all([
                    carregarContextoAtribuicoesDocentes(),
                    carregarAtribuicoesDocentes()
                ]);
            } catch (err) {
                setMensagem("msgAtribuicoesDocentes", err.message, true);
            }
        });

        linha.appendChild(btnEditar);
        linha.appendChild(btnLimpar);
        li.appendChild(titulo);
        li.appendChild(detalhe);
        li.appendChild(status);
        li.appendChild(linha);
        ul.appendChild(li);
    });
}

async function cadastrarAtribuicaoDocente(event) {
    event.preventDefault();
    const professorId = obterProfessorIdAtribuicaoFormulario();
    const disciplinaId = obterDisciplinaIdAtribuicaoFormulario();
    const turmaIds = obterTurmaIdsSelecionadasAtribuicao();

    if (professorId <= 0) {
        setMensagem("msgAtribuicoesDocentes", "Selecione o professor.", true);
        return;
    }
    if (disciplinaId <= 0) {
        setMensagem("msgAtribuicoesDocentes", "Selecione a disciplina.", true);
        return;
    }
    if (turmaIds.length === 0) {
        const confirmado = window.confirm(
            "Nenhuma turma foi marcada. Deseja remover todas as atribuicoes desta disciplina para o professor?"
        );
        if (!confirmado) {
            return;
        }
    }

    try {
        const resposta = await fetchJson("/admin/atribuicoes-docentes/lote", {
            method: "PUT",
            headers: headersJson,
            body: JSON.stringify({
                professor_id: professorId,
                disciplina_id: disciplinaId,
                turma_ids: turmaIds
            })
        });
        setMensagem("msgAtribuicoesDocentes", resposta.mensagem || "Atribuicoes atualizadas com sucesso.");
        await Promise.all([
            carregarAtribuicoesDocentes(),
            carregarTurmasAtribuidasProfessorDisciplina()
        ]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

async function importarAtribuicoesDocentesArquivo(event) {
    event.preventDefault();
    const arquivo = el("arquivoJsonAtribuicoesDocentes")?.files?.[0];
    if (!arquivo) {
        setMensagem("msgAtribuicoesDocentes", "Selecione um arquivo JSON para importar.", true);
        return;
    }

    const formData = new FormData();
    formData.append("arquivo", arquivo);

    try {
        const resposta = await fetchJson("/admin/atribuicoes-docentes/importar", {
            method: "POST",
            headers,
            body: formData
        });
        setMensagem("msgAtribuicoesDocentes", comporMensagemImportacao(resposta), houveFalhaImportacao(resposta));
        el("formImportarAtribuicoesDocentes").reset();
        await Promise.all([
            carregarContextoAtribuicoesDocentes(),
            carregarAtribuicoesDocentes()
        ]);
    } catch (err) {
        setMensagem("msgAtribuicoesDocentes", err.message, true);
    }
}

function baixarModeloAtribuicoesJson() {
    baixarArquivoTexto("modelo_atribuicoes_docentes.json", MODELO_JSON_ATRIBUICOES_DOCENTES);
}
